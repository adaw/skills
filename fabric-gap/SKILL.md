---
name: fabric-gap
description: "Detect gaps between vision, backlog, and reality (code, tests, docs). Produces a gap report and generates actionable intake items (source=gap) for the most important missing pieces (features, tests, docs, security, reliability)."
depends_on:
  - fabric-process
---

# GAP — Mezera mezi vizí, backlogem a realitou

## Účel

Porovnat:
1) **Vizi** (`{WORK_ROOT}/vision.md`) — co má existovat a proč  
2) **Backlog** (`{WORK_ROOT}/backlog.md` + items) — co je naplánované  
3) **Realitu** (`{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`) — co fakt existuje

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-gap" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-gap" --event end --status OK --report "{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


A z toho vytvořit:
- `reports/gap-*.md`
- 0..N intake itemů (top gaps), které posunou projekt správným směrem

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md`
- `{WORK_ROOT}/backlog.md` + `{WORK_ROOT}/backlog/*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`
- `{WORK_ROOT}/fabric/processes/process-map.md` (optional)

---

## Výstupy

- `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- intake items v `{WORK_ROOT}/intake/` dle `{WORK_ROOT}/templates/intake.md`:
  - `source: gap`
  - `initial_type` typicky Task/Chore/Bug
  - `raw_priority` podle dopadu

---

## Postup

### 1) Extrahuj „capabilities“ z vize

Z `vision.md` + `{VISIONS_ROOT}/*.md` vytáhni seznam:
- pillars / goals / must-haves (z core vision)
- rozšířené cíle a detaily z sub-vizí

Výsledek: 5–30 capabilities (krátké názvy).

### 2) Mapuj backlog coverage

- Z backlog indexu vezmi top itemy a zjisti, jestli odkazují na capability.
- Pokud backlog itemy nejsou explicitně tagované, mapuj heuristicky podle title/keywords.

Výsledek: capability → {backlog IDs}

### 3) Reality check (code, tests, docs)

Pro každou capability:
- **Code existence signal:** existuje relevantní modul/entrypoint?
- **Tests signal:** existují testy pro klíčové chování?
- **Docs signal:** je to popsáno v docs?

Neřeš přesné coverage číslo; stačí kvalitativní „Yes/No/Unknown” + evidence.

**Test execution pro reality check (POVINNÉ):**

Nečti jen soubory — SPUSŤ testy, abys zjistil REÁLNÝ stav:

```bash
# Quick test run pro reality check (ne plný test suite — jen smoke)
if [ -n “{COMMANDS.test}” ] && [ “{COMMANDS.test}” != “TBD” ]; then
  echo “Running quick test for gap reality check...”
  timeout 120 {COMMANDS.test} -x --tb=line -q 2>/dev/null | tail -5
  GAP_TEST_EXIT=$?
  if [ $GAP_TEST_EXIT -eq 0 ]; then
    GAP_TEST_STATUS=”PASS”
  elif [ $GAP_TEST_EXIT -eq 124 ]; then
    GAP_TEST_STATUS=”TIMEOUT”
  else
    GAP_TEST_STATUS=”FAIL”
    # Extrahuj failing test names pro gap mapping
    FAILING_TESTS=$(timeout 120 {COMMANDS.test} --tb=no -q 2>/dev/null | grep FAILED | head -10)
  fi
  echo “Gap reality check: $GAP_TEST_STATUS”
fi

# Stub detection v kódu
STUBS=$(grep -rn 'pass$\|raise NotImplementedError\|# TODO\|# FIXME' {CODE_ROOT}/ --include='*.py' 2>/dev/null | grep -v test | grep -v __pycache__)
STUB_COUNT=$(echo “$STUBS” | grep -c '\S' || echo 0)
if [ “$STUB_COUNT” -gt 0 ]; then
  echo “Found $STUB_COUNT stubs/TODOs in code”
fi
```

Zapiš test výsledek + stub count do gap reportu. Pokud testy FAILují → gap je REÁLNÝ (ne jen “soubor chybí”).

### 4) Identifikuj gap typy

Vyrob seznam gaps:

A) Vision → Backlog gap  
- capability nemá žádné backlog items

B) Backlog → Code gap  
- backlog item status READY/IN_PROGRESS, ale kód/relevantní soubory neexistují (nebo jsou stub)

C) Code → Tests gap  
- změny bez testů, kritické moduly bez test coverage signálu

D) Code → Docs gap  
- public API / usage není dokumentované

E) Security/Operational gap  
- chybí input validation, secrets hygiene, logging, error handling, etc.

### 5) Vyber top 3–10 gaps a vytvoř intake items

Pro každý top gap vytvoř intake item ({WORK_ROOT}/templates/intake.md):
- `title`: akční („Dopsat testy pro X”, „Zavést rate limiting”, „Dokumentovat CLI usage”)
- `source: gap`
- `initial_type`: Task/Bug/Chore/Spike
- `raw_priority`: 8–10 pro critical, 5–7 pro medium

Do těla:
- Popis mezery
- Evidence (soubor, modul, nebo „missing”)
- Doporučená akce + AC návrh

**Testovatelnost gap detection (P2 work quality):**
Každý identifikovaný gap musí mít:
- Konkrétní evidence (soubor:řádek nebo chybějící artefakt)
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Doporučená akce (ne jen “opravit” — konkrétně co a kde)
- Ověřitelné kritérium (jak poznat že gap je uzavřen)

### 5.5) Process Coverage Check

Ověř, že všechny zdokumentované externí procesy mají implementaci v kódu.

```bash
PROCESS_MAP=”{WORK_ROOT}/fabric/processes/process-map.md”

if [ ! -f “$PROCESS_MAP” ]; then
  echo “WARN: $PROCESS_MAP does not exist (optional input), skipping process coverage check”
else
  echo “Checking process coverage...”

  # Extrahuj dokumentované externí procesy ze process-map.md
  # Format: Předpokládá seznam externích procesů s jejich identifikátory
  DOCUMENTED_PROCESSES=$(grep -E '^- \[' “$PROCESS_MAP” | sed 's/^- \[//;s/\].*//' | sort | uniq)

  PROCESS_GAPS=0
  while IFS= read -r proc_id; do
    [ -z “$proc_id” ] && continue

    # Ověř, že proces má implementaci v {CODE_ROOT}
    # Hledej v config, handler registry, nebo process-specific modulech
    PROC_FOUND=$(grep -r “process.*$proc_id\|$proc_id.*handler” {CODE_ROOT}/ --include='*.py' 2>/dev/null | grep -v test | grep -v __pycache__ | head -1)

    if [ -z “$PROC_FOUND” ]; then
      echo “GAP: External process '$proc_id' documented but no implementation found in code”

      # Vytvoř intake item pro chybějící implementaci
      INTAKE_FILE=”{WORK_ROOT}/intake/process-impl-$proc_id-$(date +%s).md”
      cat > “$INTAKE_FILE” << 'EOF'
---
title: “Implement external process: $proc_id”
source: gap
initial_type: Task
raw_priority: 7
---

## Problem

External process `$proc_id` is documented in `fabric/processes/process-map.md` but has no implementation in the codebase.

## Evidence

- Documented in: `fabric/processes/process-map.md`
- Missing handler/implementation in `{CODE_ROOT}/`

## Acceptance Criteria

- [ ] Process handler created with clear input/output contracts
- [ ] Handler registered in configuration or process registry
- [ ] Basic tests verify handler can be invoked
- [ ] Documentation updated with implementation details

EOF
      PROCESS_GAPS=$((PROCESS_GAPS + 1))
    fi
  done <<< “$DOCUMENTED_PROCESSES”

  if [ $PROCESS_GAPS -gt 0 ]; then
    echo “Found $PROCESS_GAPS process coverage gaps”
  else
    echo “All documented processes have implementation coverage”
  fi
fi
```

### 6) Gap report

`reports/gap-{date}.md`:
- shrnutí: kolik capabilities má coverage
- tabulka gaps (severity + evidence)
- seznam vytvořených intake items

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- report obsahuje: Vision↔Backlog gaps, Backlog↔Code gaps, Code↔Tests gaps, Docs drift, Security/Operational gaps
- každé CRITICAL/HIGH gap má buď intake item, nebo explicitní vysvětlení proč ne
- počet intake items: 3–10

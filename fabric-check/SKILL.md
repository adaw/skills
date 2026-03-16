---
name: fabric-check
description: "Consistency and quality audit of the Fabric workspace. Validates directory structure, templates, backlog schemas, sprint plans, and code health signals. Applies safe auto-fixes (regenerate indices, fill missing fields) and creates intake items for issues requiring follow-up."
---

<!-- built from: builder-template -->

---

## §1 — Účel

Najít rozbité invariants dřív, než se pipeline rozjede dál. Ověř existenci a konzistenci workspace artefaktů (config, state, backlog, templates), validuj YAML schema backlog itemů, synkuj backlog index s realitou, kontroluj sprint plán, ověř runtime commands v konfigu a detekuj stálé položky či governance drift. Aplikuj bezpečné auto-fixes (regenerace indexů, doplnění povinných polí) a všechno ostatní převeď na intake items.

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "check" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "check" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "check" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions

Před spuštěním ověř:

```bash
# --- Path traversal guard (K7) ---
for VAR in "{WORK_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# --- Precondition 1: Config existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: State existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# K1: Phase validation — check runs in implementation or closing or planning
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$CURRENT_PHASE" | grep -qE '^(implementation|closing|planning)$'; then
  echo "STOP: fabric-check requires phase=implementation|closing|planning, current=$CURRENT_PHASE"
  exit 1
fi

# --- Precondition 3: Backlog struktura existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "WARN: {WORK_ROOT}/backlog.md not found — check will auto-regenerate it"
fi

# --- Precondition 4: Reports directory exists ---
mkdir -p "{WORK_ROOT}/reports"
```

**Dependency chain:** `(workspace state)` → [fabric-check] → `fabric-loop` (uses check status to decide pipeline continuation)

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` — Configuration, SCHEMA, ENUMS, COMMANDS
- `{WORK_ROOT}/state.md` — Current phase, sprint, WIP status
- `{WORK_ROOT}/backlog.md` — Index (may auto-regenerate if missing)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/backlog/*.md` — Individual backlog items
- `{WORK_ROOT}/sprints/sprint-{N}.md` — Sprint task queue
- `{WORK_ROOT}/templates/*.md` — Required templates
- `{WORK_ROOT}/vision.md`, `{VISIONS_ROOT}/*.md` — Vision links
- `{WORK_ROOT}/decisions/INDEX.md`, `{WORK_ROOT}/specs/INDEX.md` — Governance
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` — Optional runtime checks

---

## §5 — Výstupy

### Primární (vždy)
- Audit report: `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/check-*.md` (schema: `fabric.intake_item.v1`) — created for all CRITICAL and WARNING findings
- Auto-fixed files: backlog.md, governance indices (marked in report)

---

## §6 — Deterministic FAST PATH

Před analýzou proveď deterministické kroky:

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index
```

---

## §7 — Postup (JÁDRO SKILLU)

### FAST PATH Initialization:
```bash
# K5: Read MAX_FINDINGS from config.md
MAX_FINDINGS=$(grep 'QUALITY.max_findings:' "{WORK_ROOT}/config.md" 2>/dev/null | awk '{print $2}' || echo "") || { echo "ERROR: failed to read QUALITY.max_findings from config.md"; exit 1; }
MAX_FINDINGS=${MAX_FINDINGS:-500}
FINDINGS_COUNTER=0

# K2: Numeric validation
if ! echo "$MAX_FINDINGS" | grep -qE '^[0-9]+$'; then
  MAX_FINDINGS=500
  echo "WARN: MAX_FINDINGS not numeric, reset to default (500)"
fi
```

Detailní procedury jsou v `references/workflow.md`. Zde je přehled kroků:

### 7.1) Strukturální integrita workspace

Ověř existenci všech povinných adresářů a souborů (config.md, state.md, vision.md, backlog/, sprints/, templates/, decisions/, specs/, reviews/, reports/, intake/, analyses/).

**Řešení:** Viz `references/workflow.md` — sektion "1) Strukturální integrita workspace"

### 7.2) Templates integrity

Ověř, že v `{WORK_ROOT}/templates/` existují všechny povinné šablony odkazované v config.md.

**Řešení:** Viz `references/workflow.md` — sektion "2) Templates integrity"

### 7.3) Backlog item schema audit

Proveď YAML validaci každého backlog itemu (povinná pole, enum values, filename match). Aplikuj safe auto-fixes (doplnění schema, updated, prio).

**Řešení:** Viz `references/workflow.md` — sektion "3) Backlog item schema audit"

### 7.4) Vision-fit lint

Pro každý backlog item s tier T0/T1 ověř linked_vision_goal. Detekuj orphaned references.

**Řešení:** Viz `references/workflow.md` — sektion "3.1) Vision-fit lint"

### 7.5) Backlog index sync

Regeneruj backlog.md z aktuálních itemů, seřazených podle priority.

**Řešení:** Viz `references/workflow.md` — sektion "4) Backlog index sync"

### 7.6) Governance integrity

Ověř decisions/INDEX.md a specs/INDEX.md, detekuj stálé proposed ADRs, draft SPECs.

**Řešení:** Viz `references/workflow.md` — sektion "4.1) Governance integrity"

### 7.7) Sprint plan audit

Ověř aktuální sprint file (existence sekcí, Task Queue validace — všechny item IDs existují).

**Řešení:** Viz `references/workflow.md` — sektion "5) Sprint plan audit"

### 7.8) Config COMMANDS sanity

Ověř COMMANDS.test, COMMANDS.lint, COMMANDS.format_check nejsou TBD či prázdné (dle QUALITY.mode).

**Řešení:** Viz `references/workflow.md` — sektion "6) Config COMMANDS sanity"

### 7.9) Runtime checks (pokud existují commands)

Spusť lint, format_check, test dle konfigurace. Aplikuj auto-fix logiku (max 1× per gate).

**Řešení:** Viz `references/workflow.md` — sektion "7) Volitelné runtime checks"

### 7.10) Stale detection

Detekuj backlog items bez změny >30 dní (WARNING), >60 dní (CRITICAL — WQ10).

**Řešení:** Viz `references/workflow.md` — sektion "7.1) Stale detection"

### 7.11) Report freshness monitoring

Ověř, že audit reports (gap, prio, check, vision) nejsou starší než náležité thresholds.

**Řešení:** Viz `references/workflow.md` — sektion "7.2) Report freshness monitoring"

### 7.12) Spec completeness check

Pro READY backlog items ověř minimální kvalitu (description, effort, acceptance criteria).

**Řešení:** Viz `references/workflow.md` — sektion "7.3) Spec completeness check"

### 7.13) Process map freshness

Ověř existence a freshness `{WORK_ROOT}/fabric/processes/process-map.md` (>7 dní = WARNING, missing + Sprint>1 = CRITICAL).

**Řešení:** Viz `references/workflow.md` — sektion "7.6) Process Map Freshness validation"

### 7.14) Skill frontmatter audit

Pro každý skill v `skills/fabric-*/SKILL.md` ověř frontmatter dle Claude Code Agent Skills spec:

- `name`: doporučený, ≤64 znaků, lowercase+hyphens, musí odpovídat názvu adresáře
- `description`: doporučený, ≤1024 znaků, non-empty, 3. osoba ("Performs…", "Validates…")
- Podporované: `name`, `description`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `argument-hint`, `model`, `context`, `agent`, `hooks`, `compatibility`, `license`, `metadata`
- Zakázaná pole: `title`, `type`, `schema`, `version`, `tags`, `depends_on`, `feeds_into`
- `<!-- built from: builder-template -->` tag: musí být ZA `---`, ne uvnitř YAML (pro T2 skills)

**Severity:** WARNING pokud chybí description; CRITICAL pokud frontmatter obsahuje nepodporované atributy.

### 7.X) Documentation Consistency Audit

Ověř že dokumentace odpovídá aktuálnímu kódu:

```bash
# README.md defaults vs config.py
echo "=== Checking README defaults vs config.py ==="
grep 'default:' README.md 2>/dev/null | sort > /tmp/readme-defaults.txt
grep 'default=' src/llmem/config.py | sort > /tmp/config-defaults.txt
if ! diff -q /tmp/readme-defaults.txt /tmp/config-defaults.txt >/dev/null 2>&1; then
  echo "CRITICAL: README.md defaults don't match config.py"
  echo "P1 finding: docs-config-mismatch"
fi

# {DOCS_ROOT}/api/ pokrývá všechny routes v {CODE_ROOT}/api/routes/
echo "=== Checking API documentation coverage ==="
ENDPOINT_COUNT=$(grep -c '@.*\.\(get\|post\|put\|delete\)' {CODE_ROOT}/api/routes/*.py 2>/dev/null || echo 0)
DOC_COUNT=$(ls {DOCS_ROOT}/api/*.md 2>/dev/null | wc -l)
if [ "$DOC_COUNT" -lt "$((ENDPOINT_COUNT / 2))" ]; then
  echo "CRITICAL: {DOCS_ROOT}/api/ doesn't cover all endpoints (found: $DOC_COUNT, expected: >$((ENDPOINT_COUNT / 2)))"
  echo "P1 finding: docs-api-coverage"
fi

# {DOCS_ROOT}/cli.md defaults vs cli.py
echo "=== Checking CLI documentation consistency ==="
grep 'default:' {DOCS_ROOT}/cli.md 2>/dev/null | sort > /tmp/docs-cli.txt
grep 'default=' {CODE_ROOT}/cli.py 2>/dev/null | sort > /tmp/cli-defaults.txt
if ! diff -q /tmp/docs-cli.txt /tmp/cli-defaults.txt >/dev/null 2>&1; then
  echo "CRITICAL: {DOCS_ROOT}/cli.md defaults don't match cli.py"
  echo "P1 finding: docs-cli-mismatch"
fi
```

Nesrovnalosti = P1 finding.

### 7.15) Vygeneruj audit report

Vytvoř `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` s vyhodnocením všech check rezultátů, scoring, intake items.

**Řešení:** Viz `references/workflow.md` — sektion "8) Vygeneruj audit report"

### K10: Inline Example — LLMem Quality Audit

**Input:** Sprint 3 workspace: test coverage 45%, 2 stale backlog items (>60 days), missing ADR for new /capture/batch endpoint, 3 broken doc links.
**Output:** Audit report with score 65 (WARN), 4 findings (1 CRITICAL: test coverage <60%, 1 HIGH: ADR missing, 2 MEDIUM: broken links), 3 intake items created, auto-fixed backlog.md regeneration logged.

### K10: Anti-patterns (s detekcí)
```bash
# A1: Running check without current test results — Detection: ! ls {WORK_ROOT}/reports/test-*.md | xargs ls -tr | tail -1
# A2: Accepting stale findings without refresh — Detection: grep -o 'updated: [^}]*' {report} shows last_run >3 days
# A3: Missing CRITICAL findings in intake — Detection: grep CRITICAL {report} but no grep -l 'check-' {WORK_ROOT}/intake/*.md
# A4: Score calculation ignoring weights — Detection: (CRITICAL×30 + HIGH×10) != (100 - score) from report
```

---

## §8 — Quality Gates

Tato sekce není relevantní — fabric-check je audit skill, bez vlastních quality gates.

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: check
step: "check"
run_id: "{YYYY-MM-DD-{random}}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: PASS | WARN | FAIL
score: {int 0-100}
---

# check — Audit Report {YYYY-MM-DD}

## Souhrn
{1–3 věty: co se auditovalo a s jakým výsledkem}

## Metriky
| Check | Result | Detail |
|-------|--------|--------|
{...per check: Structural integrity, Backlog schema, Vision-fit, Governance, Sprint plan, COMMANDS, Process map, Coverage, Lint/Format...}

## Findings (High → Low)
| Finding | Severity | Confidence | Intake Item |
|---------|----------|------------|-------------|
{...}

## Auto-fixes applied
- ✓ {description}
{...}

## Intake items created
1. {slug}
{...}

## Warnings
{...}

## Configuration notes
{...}
```

Příklad vypracovaného reportu je v `references/examples.md`.

---

## §10 — Self-check (povinný)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1` a `kind: check`
- [ ] Všechny CRITICAL findings mají odkazované intake items v `{WORK_ROOT}/intake/`
- [ ] Protocol log má START a END záznam s `skill: check`

### Quality checks
- [ ] Audit report má všechny povinné sekce: Souhrn, Metriky, Findings, Auto-fixes, Intake items
- [ ] Findings tabulka má sloupce: Finding, Severity, Confidence, Intake Item
- [ ] Score je vypočítán dle formule: `100 - (CRITICAL×30) - (HIGH×10) - (MEDIUM×3) - (LOW×1)`
- [ ] Pokud audit PASS: score ≥80 a 0 CRITICAL findings
- [ ] Pokud audit WARN: score 50–79
- [ ] Pokud audit FAIL: score <50 nebo 1+ CRITICAL findings

### Invarianty
- [ ] Žádný soubor mimo `{WORK_ROOT}/reports/` a `{WORK_ROOT}/intake/` nebyl modifikován (fabric-check je read-only audit, s výjimkou auto-fixes)
- [ ] Pokud backlog.md byl regenerován, report to explicitně uvádí v "Auto-fixes applied"
- [ ] State.md NENÍ modifikován
- [ ] Protocol log obsahuje START i END záznam

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí {WORK_ROOT}/config.md nebo state.md | STOP + jasná zpráva "run fabric-init first" |
| FAST PATH | fabric.py backlog-index selže | WARN + pokračuj manuálně |
| Strukturální check | Chybí povinný adresář/soubor | CRITICAL + intake item |
| Backlog audit | Invalida YAML či schema mismatch | WARNING (pokud fixable) nebo CRITICAL (pokud ne) |
| Runtime commands | Test/lint command neexistuje nebo failne | CRITICAL (test missing) nebo WARNING (lint/format) |
| Auto-fix operace | Nelze regenerovat index / aplikovat fix | WARN + intake item s popisem |
| Self-check | Check selže (e.g., missing intake item) | Report WARN + popis co chybí |

**Obecné pravidlo:** Skill je fail-open vůči VOLITELNÝM vstupům (chybí → pokračuj s WARNING) a fail-fast vůči POVINNÝM vstupům (chybí → STOP).

---

## §12 — Metadata

```yaml
# Zařazení v lifecycle
phase: closing
step: check

# Oprávnění
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true

# Pořadí v pipeline
depends_on: [fabric-init, fabric-docs, fabric-hotfix]
feeds_into: [fabric-loop, fabric-intake]
```

---

## Downstream Contract

**fabric-loop** reads:
- `reports/check-*.md` field: `status` (PASS/WARN/FAIL) → decides if pipeline can continue
- `score` (0-100) → logged for trend tracking across sprints

**fabric-intake** reads:
- Generated intake items (`intake/check-*.md`) → triages into backlog
- Each intake item has: `source: check`, `slug`, `severity`, `description`, `evidence`

**fabric-sprint** reads:
- Audit score trend → if score declining across sprints, prioritize debt reduction

# Quality Gates & Validation — fabric-process

This file contains detailed validation procedures from §8–§12 of the main SKILL.md.

## Quality Gate 1: Process Map Schema Validation (§8)

```bash
# Ověř YAML frontmatter
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if head -20 "$PROCESS_MAP" | grep -q "^schema: fabric.process-map.v1"; then
  echo "PASS: process-map schema valid"
else
  echo "FAIL: process-map missing or invalid schema"
fi
```

- **PASS:** Schema přítomné a parsovatelné
- **FAIL:** Vytvoř intake item + report FAIL

## Quality Gate 2: Route Coverage Threshold (WQ10 — BLOCKING if <80%)

```bash
# Počet routes v kódu vs. počet external processes v mapě
CODE_ROUTES=$(grep -rE '@router\.(get|post|put|delete|patch)' "${CODE_ROOT}/api/routes/" --include="*.py" 2>/dev/null | wc -l)
MAP_EXTERNALS=$(grep -c "^| ext-" "$PROCESS_MAP" 2>/dev/null || echo 0)
COVERAGE=$((MAP_EXTERNALS * 100 / CODE_ROUTES))

if [ "$COVERAGE" -ge 80 ]; then
  echo "PASS: $COVERAGE% routes documented ($MAP_EXTERNALS / $CODE_ROUTES)"
else
  echo "FAIL: $COVERAGE% routes covered (<80% threshold) — create intake item + return FAIL"
fi
```

- **PASS:** ≥80% routes documented
- **FAIL:** <80% coverage → must create intake items for missing routes + block report status

## Quality Gate 3: No Duplicate Process IDs

```bash
DUPES=$(grep "^id:" {WORK_ROOT}/fabric/processes/*.md 2>/dev/null | awk '{print $2}' | sort | uniq -d)
if [ -z "$DUPES" ]; then
  echo "PASS: No duplicate process IDs"
else
  echo "FAIL: Duplicate IDs: $DUPES"
fi
```

- **PASS:** Žádné duplikáty
- **FAIL:** Deduplikuj ručně + report FAIL

## Self-Check Checklist (§10 — povinný)

### Existence Checks
- [ ] Process map existuje: `{WORK_ROOT}/fabric/processes/process-map.md`
- [ ] Report existuje: `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md`
- [ ] Process map má validní YAML frontmatter (schema: fabric.process-map.v1)

### Quality Checks
- [ ] Počet external processes ≥ počet API routes v kódu
- [ ] KAŽDÝ ACTIVE external process má ≥1 internal chain traced
- [ ] KAŽDÝ internal chain má vyplněné contract_modules (není prázdný seznam)
- [ ] Cross-mapping tabulka je kompletní (žádný external bez řádku)
- [ ] Orphan detection sekce existuje a rozlišuje DEAD_CODE / INTERNAL_ONLY / UNDOCUMENTED
- [ ] Report obsahuje povinné sekce: Souhrn, Metriky, Detaily, Warnings

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován
- [ ] Protocol log obsahuje START i END záznam
- [ ] Žádný zdrojový kód nebyl modifikován (process je read-only analytický skill)

## Report Schema (§9)

```markdown
---
schema: fabric.report.v1
kind: process
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
version: "1.0"                                    # WQ9 fix: track report version
status: {PASS|WARN|FAIL}                         # WQ10 fix: route coverage <80% OR orphans detected → FAIL
---

# process — Report {YYYY-MM-DD}

## Souhrn
{1–3 věty: kolik procesů nalezeno, kolik traced, kolik orphanů, verdikt}

## Metriky

| Metrika | Hodnota |
|---------|---------|
| External processes (ACTIVE) | {N} |
| Internal chains (traced) | {N} |
| Cross-mappings | {N} |
| Orphans (external unimplemented) | {N} |
| Orphans (dead code) | {N} |
| Orphans (undocumented) | {N} |
| Process files created/updated | {N} |
| Test validation | {PASS/FAIL/SKIP} |
| Contract modules total | {N} |
| Contract modules with tests | {N} |
| Contract modules with stubs | {N} |

## Detaily

### External Processes
{Kompaktní tabulka: ID | Entry Point | Status}

### Internal Chains
{Kompaktní tabulka: ID | Trigger | Contract Modules Count | Governance}

### Orphan Analysis
{Klasifikovaný seznam: CRITICAL (unimplemented) / WARN (dead code) / INFO (internal only)}

### Causal Dependencies (klíčové)
{Top 5 nejkritičtějších kauzálních řetězců — změny v těchto modulech mají největší dopad}

## Delta (vs. předchozí mapa)
{Pokud existovala předchozí process-map.md: co se změnilo (nové/odstraněné/modified procesy)}

## Intake items vytvořené
{Seznam nebo "žádné"}

## Warnings
{Seznam nebo "žádné"}
```

## Failure Handling Matrix (§11)

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí config.md/state.md | STOP + jasná zpráva |
| Preconditions | CODE_ROOT neexistuje | STOP + zpráva |
| Preconditions | Žádné Python soubory | STOP + zpráva |
| FAST PATH | fabric.py selže | WARN + pokračuj manuálně |
| P1 (Extract) | Žádné routes nalezeny | WARN + pokračuj (systém může mít jen CLI) |
| P2 (Trace) | Call chain nelze sledovat (obfuskovaný kód) | Zapiš co jde, zbytek = WARN + intake item |
| P3 (Cross-map) | Příliš mnoho orphanů (>50% procesů) | Report WARN + intake item (systém potřebuje refactoring) |
| P4 (Validate) | Testy FAIL | Report WARN (ne FAIL — process mapping pokračuje) |
| P4 (Validate) | Test command TBD | SKIP validace, zaloguj WARN |
| P5 (Update) | YAML write error | STOP + protocol error log + intake item |
| Quality Gate | Duplicate process IDs | Deduplikuj + report WARN |
| Self-check | Missing sections in process-map | Report WARN + intake item |

**Obecné pravidlo:** Skill je **fail-open** vůči VOLITELNÝM vstupům (vision, specs, previous map)
a **fail-fast** vůči POVINNÝM vstupům (config, state, CODE_ROOT).

## Metadata (§12 — pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: orientation
step: process

# Oprávnění
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true

# Pořadí v pipeline (pro fabric-loop)
depends_on: [fabric-architect]
feeds_into: [fabric-gap]

# Konzumenti process mapy (cross-reference)
consumed_by: [fabric-gap, fabric-analyze, fabric-review, fabric-check, fabric-implement, fabric-architect]
```

## Downstream Consumers of Process Map (from §1)

### fabric-gap
- **Reads:** `process-map.md` → External Processes table (columns: ID, Actor, Entry Point, Status)
- **Uses:** Checks each external process has matching code implementation
- **Action:** Missing implementation → gap finding

### fabric-analyze
- **Reads:** Individual process files (`fabric/processes/{id}.md`) → field `contract_modules[]`
- **Uses:** Cross-references task's touched modules against contract_modules → "Affected Processes" section

### fabric-review
- **Reads:** Individual process files → field `contract_modules[]`
- **Uses:** If task modifies contract_module → requires test evidence for that process chain

### fabric-check
- **Reads:** `process-map.md` → field `updated` (date)
- **Uses:** If older than 7 days → intake item for freshness update

### fabric-implement
- **Reads:** Individual process files → context on which processes the current task affects

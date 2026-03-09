---
name: fabric-gap
description: "Detect gaps between vision, backlog, and reality (code, tests, docs). Produces gap report and generates actionable intake items for most important missing pieces: features, tests, documentation, security, reliability."
---

<!-- built from: builder-template -->

# GAP — Detect gaps between vision, backlog, and reality

---

## §1 — Účel

Porovnat tři vrstvy a identifikovat nedostatky:

1. **Vizi** (`{WORK_ROOT}/vision.md`) — co má existovat a proč
2. **Backlog** (`{WORK_ROOT}/backlog.md` + položky) — co je naplánované
3. **Realitu** (`{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`) — co fakt existuje

Bez identifikace mezer projekt driftem ztrácí zaměření. GAP detekuje: chybějící capability v backlogu, hotové backlog item bez kódu, kód bez testů, public API bez dokumentace, a bezpečnostní/operační problémy. Výstupem je gap report a top 3–10 actionable intake items.

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci zapiš do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "gap" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "gap" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "gap" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Ověř, že tyto soubory existují PŘED spuštěním:

```bash
# K1: Phase validation — gap analysis runs in orientation
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "orientation" ]; then
  echo "STOP: fabric-gap requires phase=orientation, current=$CURRENT_PHASE"
  exit 1
fi

# --- Path traversal guard (K7) ---
for VAR in "{WORK_ROOT}" "{CODE_ROOT}" "{TEST_ROOT}" "{DOCS_ROOT}" "{VISIONS_ROOT}"; do
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

# --- Precondition 2: Vision existuje ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "STOP: {WORK_ROOT}/vision.md not found — run fabric-vision first"
  exit 1
fi

# --- Precondition 3: Backlog index existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "STOP: {WORK_ROOT}/backlog.md not found — run fabric-intake first"
  exit 1
fi
```

**Dependency chain:** `fabric-vision` → [fabric-gap] → `fabric-process`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md`
- `{WORK_ROOT}/backlog.md`

### Volitelné
- `{VISIONS_ROOT}/*.md` — dílčí vize
- `{WORK_ROOT}/backlog/*.md` — detailní backlog položky
- `{CODE_ROOT}/` — zdrojové kódy
- `{TEST_ROOT}/` — testy
- `{DOCS_ROOT}/` — dokumentace
- `{WORK_ROOT}/fabric/processes/process-map.md` — seznam procesů

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/gap-{gap_id}-{slug}.md` (schema: `fabric.intake_item.v1`)
  - Typicky 3–10 items
  - `source: gap`
  - `initial_type`: Task/Chore/Bug/Spike
  - `raw_priority` dle dopadu a úsilí

---

## §6 — Deterministic FAST PATH

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index

# 3. Backlog scan
python skills/fabric-init/tools/fabric.py backlog-scan \
  --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

---

## §7 — Postup (JÁDRO SKILLU)

### FAST PATH Initialization:
```bash
# K5: Read max gaps from config.md
MAX_GAPS=$(grep 'GAP.max_gaps:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MAX_GAPS=${MAX_GAPS:-50}
# K2: Numeric guard for MAX_GAPS
if ! echo "$MAX_GAPS" | grep -qE '^[0-9]+$'; then
  MAX_GAPS=50
  echo "WARN: MAX_GAPS not numeric, reset to default (50)"
fi
GAP_COUNTER=0

# K5: Gap thresholds from config.md
MIN_COVERAGE_PCT=$(grep 'GAP.min_coverage_pct:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MIN_COVERAGE_PCT=${MIN_COVERAGE_PCT:-80}
if ! echo "$MIN_COVERAGE_PCT" | grep -qE '^[0-9]+$'; then
  MIN_COVERAGE_PCT=80
  echo "WARN: MIN_COVERAGE_PCT not numeric, reset to default (80)"
fi
GAP_SEVERITY_THRESHOLD=$(grep 'GAP.severity_threshold:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
GAP_SEVERITY_THRESHOLD=${GAP_SEVERITY_THRESHOLD:-medium}
```

### 7.1) Extrahuj capabilities z vize

Z vision.md a {VISIONS_ROOT}/*.md vytáhni seznam pillar/goal/must-have capabilities (5–30 kusů). Normalizuj názvy, odeber duplikáty. Pokud MAX_GAPS dosaženo → WARN a break.

**Minimum:** 5+ capabilities.

### 7.2) Mapuj backlog coverage

Pro každou capability: existují backlog items? Tabeluj capability → {backlog IDs}.

**Minimum:** Coverage tabulka capability ↔ backlog (yes/no/unknown).

### 7.3) Reality check (code, tests, docs)

Pro každou capability ověř: code exists? tests exist? documented?

**POVINNÉ: SPUSŤ testy.** Nečti jen soubory:

```bash
TIMEOUT_TEST=$(awk '/timeout_bounds:/,/^[^ ]/{if(/  test:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_TEST=${TIMEOUT_TEST:-120}
timeout "$TIMEOUT_TEST" {COMMANDS.test} -x --tb=line -q 2>/dev/null
# Zaznamenej GAP_TEST_STATUS: PASS/FAIL/TIMEOUT
# Detekuj stubs: grep -rn 'pass$\|NotImplementedError' {CODE_ROOT}/src
```

**Minimum:** Test results + stub count zalogováno.

### 7.4) Detekuj všechny gap typy

Spusť bash pipelines (references/workflow.md) pro:
- **A) Vision→Backlog:** capability bez backlog items
- **B) Backlog→Code:** READY item bez kódu/je stub
- **C) Code→Tests:** změny bez testů
- **D) Code→Docs:** API není dokumentované
- **E) Security:** input validation, auth guards, secrets, rate limiting
- **F) Operational:** logging, timeout, monitoring

**ROOT CAUSE (POVINNÉ):** Každý gap: DEFERRED|BLOCKED|OVERSIGHT|CAPACITY

**Minimum:** 3–5 findings, gap_id, type, severity, root_cause, evidence (file:line).

### 7.5) Impact Analysis & Priority

Aplikuj formuli: `PRIORITY = IMPACT_SCORE × (1 / EFFORT_DAYS) × FREQUENCY_MULTIPLIER`
- IMPACT_SCORE: HIGH=10, MEDIUM=5, LOW=1
- EFFORT_DAYS: 1–10
- FREQUENCY: 1|2|3x

Prahová hodnota intake item: **PRIORITY ≥ 15** (nebo CRITICAL severity).

**Minimum:** Top 3–10 gaps seřazeno dle priority.

### 7.6) Vytvoř intake items

Pro top gaps: vytvoř `{WORK_ROOT}/intake/gap-{gap_id}-{slug}.md` s frontmatter (source=gap, initial_type, raw_priority), Kontext, Root Cause, Impact, Evidence, Akce, AC.

**Minimum:** 3–10 intake items.

### 7.7) Process Coverage Check (optional)

Pokud `{WORK_ROOT}/fabric/processes/process-map.md` existuje: ověř, že dokumentované procesy mají implementaci v {CODE_ROOT}.

### K10: Inline Example — LLMem Gap Detection

**Input:**
```
Vision: Recall module must support cosine + Jaccard scoring
Backlog: task-b042 "recall scoring" (READY)
Code: src/llmem/recall/scoring.py exists, only cosine implemented
Tests: test_scoring.py → tests cosine only (no Jaccard tests)
```

**Output:**
Gap report entry:
```
| Gap ID | Type | Root Cause | Evidence | Impact | Priority |
| G-005 | Code→Tests | OVERSIGHT | test_scoring.py:1-50 | MEDIUM | 18 |
Intake item created: gap-g005-jaccard-test.md
Title: "Add Jaccard scoring unit tests (recall module)"
Type: Task | Priority: 8 | Effort: S
```

### K10: Anti-patterns (s detekcí)
```bash
# A1: Reporting Non-Existent Code
# Detection: grep "gap.*exists" report.md && find CODE_ROOT -path "*recall/scoring.py" | wc -l
# Fix: Only report gaps for implemented code; planned items → "N/A, design phase"

# A2: Missing Root Cause
# Detection: grep "^| G-" report.md | grep -v "DEFERRED\|BLOCKED\|OVERSIGHT\|CAPACITY"
# Fix: Tag each gap with root cause; else skip from intake

# A3: Duplicate Gap Reports
# Detection: cut -d'|' -f3 gap-report.md | sort | uniq -d
# Fix: Dedup by evidence (file:line); merge identical gaps into single item
```

---

## §8 — Quality Gates

### Gate 1: Gap Report Validation

```bash
REPORT="{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md"
grep -q "^## Summary" "$REPORT" && \
grep -q "^## Gap Analysis" "$REPORT" && \
grep -q "^## Intake Items" "$REPORT"
```

**PASS:** Report obsahuje všechny povinné sekce.

**FAIL:** EXIT 1.

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: gap
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
critical_findings_count: {int}
total_gaps: {int}
intake_items_created: {int}
---

# Gap Report — {YYYY-MM-DD}

## Summary

- **Coverage:** N of M capabilities. Missing: X, Y, Z.
- **Test Status:** N passed, M failed. Stubs: K.
- **Security Gaps:** N CRITICAL (missing X, Y, Z).

## Gap Analysis

| Gap ID | Type | Root Cause | Evidence | Impact | Priority |
|--------|------|-----------|----------|--------|----------|
| G-001 | Vision→Code | OVERSIGHT | file:line | CRITICAL — issue | 30 |

## Intake Items Created

- `intake/gap-g001-{slug}.md` — Title

## Test Results

```
Command: pytest -q --tb=line
Exit: {exit_code}
Passed: N / Failed: M / Stubs: K
```
```

---

## §10 — Self-check (povinný)

### Existence checks
- [ ] Report: `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- [ ] YAML frontmatter se schematem `fabric.report.v1`
- [ ] CRITICAL/HIGH gaps mají intake items
- [ ] Protocol log: START + END záznam

### Quality checks
- [ ] Report: Summary, Gap Analysis, Intake Items sekce
- [ ] Gap tabulka: Gap Type, Severity, Root cause, Evidence
- [ ] Počet intake items: 3–10
- [ ] BLOCKING validace: `grep -q "^## Summary\|^## Gap Analysis\|^## Intake Items"`

### Invariants
- [ ] Žádný soubor mimo reports/ a intake/ modifikován
- [ ] Backlog.md NENÍ modifikován
- [ ] Code files NEJSOU modifikován
- [ ] Protocol log: START + END

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí prereq (vision.md) | STOP + jasná zpráva |
| FAST PATH | fabric.py selže | WARN + pokračuj |
| Postup (§7) | Nelze spustit testy | WARN + pokračuj |
| Quality Gate | Report chybí sekce | EXIT 1 |
| Self-check | Check FAIL | Report WARN + intake |

---

## §12 — Metadata

```yaml
phase: orientation
step: "detect_gaps"
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true
depends_on: [fabric-vision]
feeds_into: [fabric-process]
```

---

## §0 — Reference

Viz references/workflow.md pro:
- Complete end-to-end detection pipeline bash
- Path traversal guard (K7)
- State validation (K1)
- Anti-patterns A–E (detection & fix)
- Intake templates
- Security gap checklist

Viz references/examples.md pro:
- Gap report examples (real LLMem data)
- Intake item templates (5 konkrétních typů)
- How to validate a gap report

---

## DOWNSTREAM CONTRACT (pro fabric-process)

fabric-process čte z reportu:
- `findings[]` — (gap_id, type, severity, root_cause, evidence, impact, priority)
- `critical_findings_count` (int)
- `intake_items_created[]` (list cest)
- `test_status` (enum) — PASS | FAIL | TIMEOUT
- `stub_count` (int)

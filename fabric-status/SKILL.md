---
name: fabric-status
description: "Produce holistic project health snapshot: codebase signals, test health, backlog flow, docs drift, and CI/tooling status. Language-agnostic detection with configured commands. Dashboard-style report enabling informed strategic decisions."
---

<!-- built from: builder-template -->

---

## §1 — Účel

Vytvořit rychlý, ale použitelný „dashboard" projektu: codebase signály (velikost, churn proxy), test zdraví (PASS/FAIL + evidence), backlog stav (flow, WIP), docs drift, a rizika pro další sprint. Bez STATUSu tým pracuje bez orientace v tom, kde se projekt nachází. STATUS je foundation pro všechna další rozhodnutí (je-li zdravý → pokračujeme; je-li v riziku → triage).

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "status" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "status" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "status" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

```bash
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

# --- Precondition 3: Backlog existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "WARN: {WORK_ROOT}/backlog.md not found — backlog metrics will be unavailable"
fi

# --- Precondition 4: Reports directory exists ---
mkdir -p "{WORK_ROOT}/reports"
```

**Dependency chain tohoto skillu:**
```
(anytime) → [fabric-status] → (monitoring/dashboard)
```

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` — COMMANDS, cesty
- `{WORK_ROOT}/state.md` — aktuální fáze

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/backlog.md` + backlog items — pro backlog metrics
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` — pro codebase snapshot
- `{WORK_ROOT}/reports/status-*.md` — poslední 3 reporty pro trend analýzu

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`, kind: `status`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/status-{slug}.md` — pokud chybí COMMANDS.test/lint/format_check nebo jsou kritická rizika

---

## §6 — Deterministic FAST PATH

Než začneš psát report, vyrob strojový snapshot (git + code stats + backlog stats + COMMANDS test/lint/format_check s log capture):

```bash
python skills/fabric-init/tools/fabric.py snapshot-status \
  --out "{WORK_ROOT}/reports/status-snapshot-{YYYY-MM-DD}.json" \
  --tail 120
```

Pak report stav podle dat ze snapshotu (ne odhadem). Snapshots mohou být dočasné, report je trvalý artefakt.

---

## §7 — Postup (JÁDRO SKILLU)

### K2: Counter initialization and validation
```bash
# K5: Read from config.md
CONFIG_MAX_FILES=$(grep 'STATUS.max_files_scan:' "{WORK_ROOT}/config.md" 2>/dev/null | awk '{print $2}' || echo "") || { echo "ERROR: failed to read STATUS.max_files_scan from config.md"; exit 1; }
MAX_FILES_SCAN=${CONFIG_MAX_FILES:-${MAX_FILES_SCAN:-10000}}

# K2: Counter initialization
FILE_COUNTER=0

# K2: Numeric validation
if ! echo "$MAX_FILES_SCAN" | grep -qE '^[0-9]+$'; then
  MAX_FILES_SCAN=10000
  echo "WARN: MAX_FILES_SCAN not numeric, reset to default (10000)"
fi
```

### 7.1) State Validation (K1: State Machine)

**Co:** Ověřit, že aktuální fáze projektu je kompatibilní se spuštěním fabric-status.

**Jak:**
```bash
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-status. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

**Minimum:** Potvrzení, že fáze je validní.

**Anti-patterns:**
- Nepoužívej `continue` pokud fáze je invalid — STOP je korektní.

---

### 7.2) Path Traversal Guard (K7: Input Validation)

**Co:** Zabránit path traversal útoků na souborový systém.

**Jak:**
```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Aplikuj na všechny dynamické cesty
validate_path "$CODE_PATH"
validate_path "$STATUS_REPORT"
```

**Minimum:** Validace funkce je definovaná a volána.

---

### 7.3) Zjistí dominantní typy souborů (language-agnostic)

**Co:** Určit programovací jazyk projektu na základě rozšíření souborů.

**Jak:**
Použij `git ls-files` (pokud je repo git) nebo `find` fallback. Vytvoř histogram přípon v `{CODE_ROOT}/` (ignoruj `{TEST_ROOT}/`, `{DOCS_ROOT}/`, vendory). Top 3 extensions použij jako proxy pro jazyk (např. `.py`, `.ts`, `.go`).

**Minimum:**
```markdown
| Extension | Count (files) | Approx LOC |
|-----------|---------------|-----------|
| .py       | 47            | ~4200     |
| .md       | 12            | ~2100     |
```

**Anti-patterns:**
- Netvrdíš, že je LOC "přesné" — jde o trend, ne matematiku.
- Nevynechávej top 3 extensions jen proto, že máš málo souborů.

---

### 7.4) Test health (objektivní)

**Co:** Spustit test suite a reportovat PASS/FAIL.

**Jak:**
Z configu načti `COMMANDS.test` a volitelně `COMMANDS.test_e2e`. Pokud `COMMANDS.test` je `TBD` nebo prázdné (`""`), označ status jako `UNKNOWN` a vytvoř WARNING + intake item.

Jinak spusť:
```bash
TIMEOUT_TEST=$(awk '/timeout_bounds:/,/^[^ ]/{if(/  test:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_TEST=${TIMEOUT_TEST:-120}
timeout "$TIMEOUT_TEST" {COMMANDS.test}
```

**Minimum:**
```
Status: PASS | FAIL | UNKNOWN | SKIPPED
Evidence: {count passed}/{count failed} (exit code: {N})
```

**Anti-patterns:**
- Netvrdíš „build health" bez ověření COMMANDS.test.
- Netvrdíš „dobrý stav" pokud tests FAIL.

---

### 7.5) Lint/format health

**Co:** Spustit linter a format-checker, reportovat stav.

**Jak:**
Z configu načti `COMMANDS.lint` a `COMMANDS.format_check`. Pokud je `TBD` → report `UNKNOWN` + vytvoř intake item. Pokud je prázdné (`""`) → report `SKIPPED` (doporuč doplnit linter/formatter).

```bash
TIMEOUT_LINT=$(awk '/timeout_bounds:/,/^[^ ]/{if(/lint:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_LINT=${TIMEOUT_LINT:-120}
TIMEOUT_FMT=$(awk '/timeout_bounds:/,/^[^ ]/{if(/format_check:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_FMT=${TIMEOUT_FMT:-120}
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout "$TIMEOUT_LINT" {COMMANDS.lint}
else
  echo "lint: SKIPPED or UNKNOWN"
fi

if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout "$TIMEOUT_FMT" {COMMANDS.format_check}
else
  echo "format_check: SKIPPED or UNKNOWN"
fi
```

**Minimum:**
```
Lint: PASS | FAIL | UNKNOWN | SKIPPED
Format: PASS | FAIL | UNKNOWN | SKIPPED
```

---

### 7.6) Git health

**Co:** Ověřit čistotu working tree, věk feature branches, ahead/behind main.

**Jak:**
```bash
git status --porcelain
git for-each-ref --sort=committerdate --format='%(refname:short) %(committerdate:relative)' refs/heads/
git rev-list --left-right --count {main_branch}...HEAD
```

**Minimum:**
```
Working tree: CLEAN | DIRTY
Stale branches (> GIT.max_branch_age_days): {count}
Unmerged branches: {count}
```

---

### 7.7) Backlog health

**Co:** Spočítat backlog items po statusu, READY ratio, WIP compliance.

**Jak:**
Z `{WORK_ROOT}/backlog/*.md` spočítej status counts (IDEA/DESIGN/READY/IN_PROGRESS/IN_REVIEW/BLOCKED/DONE). WIP compliance: pokud existuje víc než 1 IN_PROGRESS/IN_REVIEW → riziko (WIP breach).

**Minimum:**
```markdown
| Status | Count |
|--------|-------|
| IDEA   | 5     |
| READY  | 15    |
| BLOCKED| 3     |
| IN_PROGRESS | 2 |
| DONE   | 28    |

WIP compliance: READY=15, BLOCKED=3, WIP=2 — OK
```

---

### 7.8) Docs health

**Co:** Zjistit, zda existuje dokumentace a jak je aktuální.

**Jak:**
- Existuje `{DOCS_ROOT}/`?
- Počet markdown souborů
- Nejnovější modifikovaný doc file (pokud git)

**Minimum:**
```
Docs: OK | STALE | MISSING
Modified: {N} days ago (or "never")
File count: {N}
```

---

### 7.9) Trend (poslední 3 status reporty)

**Co:** Analýza zdraví projektu v čase — zlepšuje se? zhoršuje se?

**Jak:**
Pokud existují poslední 3 status reporty, extrahuj health score a key signals. Trend: zlepšuje se test/lint? Roste backlog READY? Klesá BLOCKED?

**Minimum:**
```markdown
| Date | Health Score | Key Delta |
|------|--------------|-----------|
| 2026-03-06 | 72 | +5 (tests fixed) |
| 2026-03-05 | 67 | -10 (BLOCKED grew) |
| 2026-03-04 | 77 | stable |
```

---

### 7.10 & 7.11) Health Score & Risk Identification

**Detail:** Viz `references/health-scoring.md` pro health scoring formula, risk identification patterns a assessment levels.

### K10: Inline Example — LLMem Status Dashboard

**Input:**
```
Current sprint 3 (day 5 of 10):
Tests: pytest -q → 47 passed, 2 failed (FAIL)
Lint: ruff check src/ → 0 violations (PASS)
Backlog: READY=12, IN_PROGRESS=1, BLOCKED=2, DONE=28
Docs: modified 3 days ago, 8 .md files
```

**Output:**
```
Health Score: 67/100 (at-risk)
| Signal | Status | Value | Assessment |
| Tests | FAIL | 47/49 | blockers: test_qdrant, test_injection |
| Lint | PASS | 0 | excellent |
| Backlog | RISK | BLOCKED=2 | mitigate: unblock or drop from sprint |
Risks: (1) test failures prevent merge; (2) 2 blocked items reduce sprint capacity
```

### K10: Anti-patterns (s detekcí)
```bash
# A1: Stale Test Results
# Detection: stat -c %Y reports/status-*.md | sort -n | tail -1; [if >24h ago]
# Fix: Run fabric-status again; update test command in config.md if broken

# A2: Missing COMMANDS.test
# Detection: grep "COMMANDS.test:" config.md | grep -E "TBD|^$"
# Fix: Fill in test command (e.g., "pytest -q") and re-run

# A3: Docs Drift (>30 days)
# Detection: find DOCS_ROOT -name "*.md" -mtime +30 | wc -l
# Fix: Schedule doc update task or create intake item for stale docs review
```

---

## §8 — Quality Gates (pokud skill má gates)

Skill fabric-status NEMÁ quality gates — reportuje stav, neopravuje. Pokud snapshot nebo COMMANDS selže, report WARN/ERROR a pokračuj manuálně.

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md`:

```markdown
---
schema: fabric.report.v1
kind: status
step: "status"
run_id: "status-{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: OK
health_score: {0-100}
---

# status — Report {YYYY-MM-DD}

## Health snapshot
Health score: **{N}/100** ({healthy|at-risk|critical})

## Key signals
| Signal | Status | Value | Assessment |
|--------|--------|-------|------------|
| Tests | {PASS/FAIL/UNKNOWN} | {count or —} | {brief} |
| Lint | {PASS/FAIL/UNKNOWN} | {count or —} | {brief} |
| Format | {PASS/FAIL/UNKNOWN} | {count or —} | {brief} |
| Backlog flow | {OK/RISK} | READY={N}, BLOCKED={N} | {brief} |
| Docs | {OK/STALE/UNKNOWN} | {modified: N days ago or —} | {brief} |
| Git | {CLEAN/DIRTY} | dirty={N}, stale-branches={N} | {brief} |

## Codebase snapshot
| Metric | Value |
|--------|-------|
| Top language | {ext: count files, LOC} |
| Total code files | {N} |
| Total LOC | ~{N} |

## Risks (top 3)
1. {Risk}: {Specifika + impact} → {next action}
2. {Risk}: {Specifika + impact} → {next action}
3. {Risk}: {Specifika + impact} → {next action}

## Suggested next actions (priority)
1. {Konkrétní akce + reason}
2. {Konkrétní akce + reason}
3. {Konkrétní akce + reason}

## Trend (last 3 reports)
| Date | Health score | Key delta |
|------|--------------|-----------|
| {date} | {N} | {delta} |
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md`
- [ ] Protocol log obsahuje START i END záznam

### Quality checks
- [ ] Report obsahuje všechny povinné sekce: Health snapshot, Key signals, Codebase snapshot, Risks, Suggested next actions
- [ ] Health score je číselný (0–100)
- [ ] Všechny key signals mají explicitní hodnotu: PASS / FAIL / UNKNOWN / SKIPPED (nikdy „—" když je data dostupná)
- [ ] Risks jsou specifické (ne generické): jméno rizika + impact + next action
- [ ] Suggested actions jsou konkrétní (ne vágní): není „improve tests", je „run test coverage; target ≥80%"
- [ ] Tabulky mají hodnoty (ne „—" když je data dostupná)

### Invarianty
- [ ] Pokud `COMMANDS.test` je `TBD` → intake item „status-missing-test-command" existuje
- [ ] Pokud `COMMANDS.lint` je `TBD` → intake item „status-missing-lint-command" existuje
- [ ] Health score logika odpovídá §7.10 scoring (start 100, -40 pokud tests FAIL, atd.)
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí config.md nebo state.md | STOP + jasná zpráva co chybí |
| FAST PATH | snapshot-status selže | WARN + pokračuj manuálně (LLM udělá strojovou práci) |
| Postup §7 | COMMANDS.test/lint/format nelze spustit | Report UNKNOWN/SKIPPED + intake item s popisem |
| Postup §7 | Nelze spočítat backlog (soubor chybí) | WARN + report s dostupnými daty |
| Postup §7 | Git operace selže | WARN + skip git health (ne STOP) |
| Self-check | Check FAIL | Report WARN + intake item |

**Obecné pravidlo:** Skill je fail-open vůči VOLITELNÝM vstupům (chybí → pokračuj s WARNING) a fail-fast vůči POVINNÝM vstupům (chybí → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: orientation
step: status

# Oprávnění
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true

# Pořadí v pipeline
depends_on: [fabric-init]
feeds_into: [fabric-loop]
```

---

## Git Safety (K4)

Skill fabric-status používá READ-ONLY git příkazy (git status, git for-each-ref, git rev-list) pro health snapshot. Nemodifikuje repo. Všechny proměnné v git příkazech jsou quotované.

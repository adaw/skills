---
name: fabric-check
description: "Consistency and quality audit of the Fabric workspace. Validates directory structure, templates, backlog item schemas, backlog index, sprint plan integrity, and basic code health signals (via configured COMMANDS). Applies safe auto-fixes (e.g., regenerate backlog.md) and creates intake items for anything requiring human/agent follow-up. Writes an audit report."
---

# CHECK — Konzistenční audit + safe auto-fix

## Účel

Najít rozbité invariants dřív, než se pipeline rozjede dál:
- špatné cesty / chybějící adresáře
- rozbitá metadata (YAML schema)
- backlog index mimo sync
- sprint plán nevalidní
- config COMMANDS chybí

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-check" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-check" --event end --status OK --report "{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Aplikovat jen **bezpečné** automatické opravy (idempotentní) a vše ostatní převést na intake items.

## Downstream Contract

**Kdo konzumuje výstupy fabric-check a jaká pole čte:**

- **fabric-loop** reads:
  - `reports/check-*.md` field: `status` (PASS/WARN/FAIL) → decides if pipeline can continue
  - `score` (0-100) → logged for trend tracking across sprints

- **fabric-intake** reads:
  - Generated intake items (`intake/check-*.md`) → triages into backlog
  - Each intake item has: `source: check`, `slug`, `severity`, `description`, `evidence`

- **fabric-sprint** reads:
  - Audit score trend → if score declining across sprints, prioritize debt reduction

**Contract fields in report:**
```yaml
version: "1.0"
status: PASS | WARN | FAIL    # FAIL blocks pipeline
score: int                     # 0-100 (formula: 100 - CRIT*30 - HIGH*10 - MED*3 - LOW*1)
findings: [{id, severity, confidence, description, evidence, auto_fixed}]
intake_items_created: [slug]
auto_fixes_applied: [description]
```

## Anti-patterns with Detection & Fix (§9)

**Anti-pattern A: Stale backlog item ignored**
- Detection: `find {WORK_ROOT}/backlog/ -name "*.md" -mtime +30 | wc -l`
- Fix: Create intake item per stale item. If >60 days, escalate to CRITICAL and FAIL the audit.

**Anti-pattern B: Broken backlog index (items exist but not in backlog.md)**
- Detection: `diff <(ls "{WORK_ROOT}/backlog"/*.md | sed 's|.*/||;s|\.md||' | sort) <(grep -oP '(?<=\[)[^\]]+' "{WORK_ROOT}/backlog.md" | sort)`
- Fix: Run `python skills/fabric-init/tools/backlog_index.py --work-root "{WORK_ROOT}"` to regenerate.

**Anti-pattern C: Missing required frontmatter fields**
- Detection: `for f in "{WORK_ROOT}/backlog"/*.md; do grep -L "^status:" "$f"; done`
- Fix: Auto-fill missing fields with defaults (status: BACKLOG, effort: M, tier: T2, updated: today).

**Anti-pattern D: Config COMMANDS referencing non-existent scripts**
- Detection: `grep -oP 'test:\s*"?\K[^"]+' "{WORK_ROOT}/config.md" | xargs -I{} sh -c 'command -v {} || echo "MISSING: {}"'`
- Fix: Report as CRITICAL. Create intake item to fix config.md or install missing tool.

**Anti-pattern E: Duplicate backlog item slugs**
- Detection: `ls "{WORK_ROOT}/backlog"/*.md | sed 's|.*/||;s|\.md||' | sort | uniq -d`
- Fix: Rename duplicates with suffix `-v2`, `-v3`. Update backlog.md index.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/*.md`
- `{WORK_ROOT}/sprints/*.md`
- `{WORK_ROOT}/templates/*.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (pro vision-fit lint)
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` (existence + volitelné commands)

---

## Výstupy

- audit report: `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` (dle `{WORK_ROOT}/templates/audit-report.md`)
- safe auto-fix changes (např. regenerace backlog.md)
- intake items pro CRITICAL/WARNING:
  - `{WORK_ROOT}/intake/check-*.md`

---

## Preconditions

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

# --- Precondition 3: Backlog struktura existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "WARN: {WORK_ROOT}/backlog.md not found — check will auto-regenerate it"
fi

# --- Precondition 4: Templates existují ---
if [ ! -d "{WORK_ROOT}/templates" ]; then
  echo "WARN: {WORK_ROOT}/templates directory not found"
fi

# --- Precondition 5: Reports directory exists ---
mkdir -p "{WORK_ROOT}/reports"
```

**Dependency chain:** `(workspace state)` → [fabric-check] → `fabric-loop` (uses check status to decide pipeline continuation)

---

## Status taxonomie (z config.md)

Backlog statusy musí být:
`IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE`

---

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="closing"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-check. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### Path Traversal Guard (K7: Input Validation)

```bash
# Path traversal guard — reject any input containing ".."
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic path inputs:
# validate_path "$BACKLOG_FILE"
# validate_path "$REPORT_PATH"
```

### 1) Strukturální integrita workspace

Ověř existenci:
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/vision.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/` + `backlog/done/`
- `{WORK_ROOT}/intake/` + `intake/done/` + `intake/rejected/`
- `{WORK_ROOT}/reports/`
- `{WORK_ROOT}/sprints/`
- `{WORK_ROOT}/analyses/`
- `{WORK_ROOT}/templates/`
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`
- `{WORK_ROOT}/reviews/` + `reviews/INDEX.md`

CRITICAL pokud chybí → vytvoř intake item `check-missing-structure.md`.

### 2) Templates integrity

Ověř, že v `{WORK_ROOT}/templates/` existují povinné šablony (viz config).
Pokud chybí → WARNING + intake.

### 3) Backlog item schema audit

**K2 Fix: Backlog Audit with Counter**

```bash
MAX_FINDINGS=${MAX_FINDINGS:-500}
FINDING_COUNTER=0
```

Z `{WORK_ROOT}/config.md` načti kontrakty:
- `SCHEMA.backlog_item`
- `ENUMS.statuses`, `ENUMS.tiers`, `ENUMS.efforts`, `ENUMS.types`

Pro každý `{WORK_ROOT}/backlog/*.md` (mimo `backlog/done/`):
```bash
for item_file in {WORK_ROOT}/backlog/*.md; do
  FINDING_COUNTER=$((FINDING_COUNTER + 1))
  if [ "$FINDING_COUNTER" -ge "$MAX_FINDINGS" ]; then
    echo "WARN: max audit findings reached ($FINDING_COUNTER/$MAX_FINDINGS)"
    break
  fi
  # ... validate item schema
done
```
- parse YAML frontmatter
- ověř povinné klíče:
  - `schema`, `id`, `title`, `type`, `tier`, `status`, `effort`, `created`, `updated`, `source`, `prio`
- validuj hodnoty:
  - `schema` == `SCHEMA.backlog_item`
  - `status` ∈ `ENUMS.statuses`
  - `type` ∈ `ENUMS.types`
  - `tier` ∈ `ENUMS.tiers`
  - `effort` ∈ `ENUMS.efforts`
  - `prio` je integer
  - filename odpovídá `id` (např. `{id}.md`)

Safe auto-fix (idempotentní):
- pokud chybí `schema`, doplň `schema: <SCHEMA.backlog_item>`
- pokud chybí `updated`, doplň `updated: {YYYY-MM-DD}`
- pokud chybí `prio`, doplň `prio: 0` (a reportuj WARNING; prio to později přepočítá)

Ne-safe (→ intake + WARNING/CRITICAL):
- chybějící `id` nebo `title`
- `schema` existuje, ale je **jiný** než očekávaný (drift)
- nevalidní status/type/tier/effort

### 3.1) Vision-fit lint (backlog ↔ vize)

Cíl: zabránit tomu, aby se backlog stal „košem na všechno“.

Pro každý backlog item (mimo `done/`):
- načti `tier` a `linked_vision_goal` (pokud existuje)

Pravidla:
- pokud `tier` je `T0` nebo `T1` a `linked_vision_goal` chybí nebo je prázdné:
  - vytvoř intake item `{WORK_ROOT}/intake/check-missing-vision-link-{id}.md`
  - do něj napiš: co chybí (goal/pillar), a návrh: doplnit `linked_vision_goal` nebo snížit tier
  - reportuj jako WARNING (neblokuje to okamžitě běh, ale musí se to řešit)

- pokud `linked_vision_goal` je vyplněné, ale **neobjevuje se** ani v `{WORK_ROOT}/vision.md` ani v `{VISIONS_ROOT}/*.md`:
  - vytvoř intake item `{WORK_ROOT}/intake/check-unknown-vision-link-{id}.md`
  - reportuj WARNING („vision drift / překlep / chybí sub-vize“)

### 4) Backlog index sync

Regeneruj „expected“ tabulku z backlog itemů a porovnej s `{WORK_ROOT}/backlog.md`.

Pokud nesedí:
- safe auto-fix: přepiš backlog.md na kanonickou tabulku (seřazení PRIO desc)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```
- zapiš do reportu jako FIXED


### 4.1) Governance integrity (decisions/specs/reviews)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py governance-index
python skills/fabric-init/tools/fabric.py governance-scan
```

Vyhodnoť:
- chybějící `INDEX.md` → WARNING + intake (nebo auto-fix přes `governance-index`)
- proposed ADR starší než `GOVERNANCE.decisions.stale_proposed_days` → WARNING + intake
- draft SPEC starší než `GOVERNANCE.specs.stale_draft_days` → WARNING + intake
- missing `date`/`status` ve governance souborech → WARNING + intake (oprava: doplnit metadata)

Pozn.: `governance-index` je safe auto-fix (jen přegeneruje indexy).


### 5) Sprint plan audit (pokud existuje)

Najdi aktuální sprint:
- ze `state.md` (`sprint: N`)
- sprint file: `{WORK_ROOT}/sprints/sprint-{N}.md` (pokud existuje)

Validace:
- má sekce `## Sprint Targets`
- má sekce `## Task Queue` s tabulkou
- každý Task Queue `ID` existuje jako backlog item
- `Order` je unikátní a začíná od 1 (nebo je aspoň monotónní)

Pokud Task Queue odkazuje na neexistující backlog item → CRITICAL + intake.

### 6) Config COMMANDS sanity

Z configu ověř:

- `COMMANDS.test` není `TBD` ani prázdné
- `COMMANDS.lint` není `TBD` *(prázdné = vypnuto)*
- `COMMANDS.format_check` není `TBD` *(prázdné = vypnuto)*

Pokud `COMMANDS.test` je `TBD` nebo prázdné:
- vytvoř intake item `intake/check-missing-test-command.md`
- reportuj **CRITICAL** (bez testů nelze bezpečně pokračovat)

Pokud `COMMANDS.lint` nebo `COMMANDS.format_check` je `TBD`:
- vytvoř intake item `intake/check-config-commands-tbd.md`
- reportuj **WARNING** (bez nich nelze enforce některé quality gates)

Pokud je `COMMANDS.lint` nebo `COMMANDS.format_check` prázdné:
- reportuj `SKIPPED`
- vytvoř intake item `intake/check-recommend-enable-lint-or-format.md` (doporučení)

Pokud `QUALITY.mode` je `strict` a lint/format jsou prázdné (`""`):
- reportuj **CRITICAL**
- vytvoř intake item `intake/check-strict-mode-missing-lint-or-format.md`
- FAIL

### 7) Volitelné: rychlé runtime checks (pokud commands existují)

Pokud repo má čistý working tree:

Spusť v tomto tvaru (aby nikdy neběžel prázdný příkaz):

```bash
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi
{COMMANDS.test}
```

Výsledek zapiš do reportu (PASS/FAIL).

#### Auto-fix (safe, idempotentní)

Pokud lint nebo format check failne a config má příslušný fix příkaz, **spusť auto-fix a opakuj gate**:

1. **Lint fail** + `COMMANDS.lint_fix` není prázdné → spusť `{COMMANDS.lint_fix}`, pak znovu `{COMMANDS.lint}`.
2. **Format fail** + `COMMANDS.format` není prázdné → spusť `{COMMANDS.format}`, pak znovu `{COMMANDS.format_check}`.

Auto-fix smí proběhnout **max 1×** per gate. Pokud po auto-fixu gate stále failne → zapiš do reportu jako FAIL a vytvoř intake item.

Pokud auto-fix něco opravil, commitni změny:
```bash
git add -A && git commit -m "chore: auto-fix lint/format (fabric-check)"
```

Pokud by to bylo příliš drahé, zaznamenej to jako `skipped` s důvodem.

**Volitelně (framework self-test):**
- spusť statický validator:
  ```bash
  python skills/fabric-init/tools/validate_fabric.py --workspace --runnable
  ```
  Pokud failne → CRITICAL + intake item `intake/check-validator-failed.md`.

### 7.1) Stale detection (backlog items + epics) — WQ10 BLOCKING (WQ10 fix)

```bash
# Stale detection: items beze změny >30 dní (WARN), >60 dní (FAIL — WQ10)
TODAY_EPOCH=$(date +%s)
CRITICAL_STALE_COUNT=0

for ITEM in {WORK_ROOT}/backlog/*.md; do
  [ -f "$ITEM" ] || continue
  UPDATED=$(grep '^updated:' "$ITEM" | awk '{print $2}')
  if [ -n "$UPDATED" ]; then
    ITEM_EPOCH=$(date -d "$UPDATED" +%s 2>/dev/null || echo 0)
    DAYS_OLD=$(( (TODAY_EPOCH - ITEM_EPOCH) / 86400 ))
    ITEM_TYPE=$(grep '^type:' "$ITEM" | awk '{print $2}')
    ITEM_ID=$(basename "$ITEM" .md)

    # WQ10 enforcement: >60d = CRITICAL (FAIL status)
    if [ "$DAYS_OLD" -gt 60 ]; then
      echo "CRITICAL: stale item $ITEM_ID (${DAYS_OLD}d unchanged — exceeds 60d threshold)"
      CRITICAL_STALE_COUNT=$((CRITICAL_STALE_COUNT + 1))
    # Regular stale threshold (WARN)
    elif [ "$ITEM_TYPE" = "Epic" ] && [ "$DAYS_OLD" -gt 60 ]; then
      echo "WARN: stale Epic $ITEM_ID (${DAYS_OLD}d unchanged)"
    elif [ "$ITEM_TYPE" != "Epic" ] && [ "$DAYS_OLD" -gt 30 ]; then
      echo "WARN: stale item $ITEM_ID (${DAYS_OLD}d unchanged)"
    fi
  fi
done

# WQ10: If >0 items >60d stale → report status = FAIL
if [ "$CRITICAL_STALE_COUNT" -gt 0 ]; then
  echo "FAIL: $CRITICAL_STALE_COUNT items are stale >60 days (WQ10 blocking)"
fi
```

Stale items zapiš do audit reportu + vytvoř intake items pro top 5 nejstarších. WQ10: Pokud je >0 CRITICAL stale items → report status = FAIL.

### 7.2) Report freshness monitoring

```bash
# Report freshness: GAP ≤30d, PRIO ≤45d, CHECK ≤15d
check_report_freshness() {
  local PATTERN="$1"
  local MAX_DAYS="$2"
  local LABEL="$3"
  LATEST=$(ls -t {WORK_ROOT}/reports/${PATTERN}*.md 2>/dev/null | head -1)
  if [ -z "$LATEST" ]; then
    echo "WARN: no $LABEL report found"
  else
    REPORT_DATE=$(grep '^created_at:\|^date:' "$LATEST" | head -1 | awk '{print $2}' | cut -c1-10)
    if [ -n "$REPORT_DATE" ]; then
      REPORT_EPOCH=$(date -d "$REPORT_DATE" +%s 2>/dev/null || echo 0)
      DAYS_OLD=$(( (TODAY_EPOCH - REPORT_EPOCH) / 86400 ))
      if [ "$DAYS_OLD" -gt "$MAX_DAYS" ]; then
        echo "WARN: $LABEL report is ${DAYS_OLD}d old (max ${MAX_DAYS}d)"
      fi
    fi
  fi
}

check_report_freshness "gap-" 30 "GAP"
check_report_freshness "prio-" 45 "PRIO"
check_report_freshness "check-" 15 "CHECK"
check_report_freshness "vision-" 60 "VISION"
```

### 7.3) Spec completeness check (READY items)

Pro READY items v backlogu ověř minimální kvalitu:
```bash
for ITEM in {WORK_ROOT}/backlog/*.md; do
  STATUS=$(grep '^status:' "$ITEM" | awk '{print $2}')
  [ "$STATUS" = "READY" ] || continue
  ITEM_ID=$(basename "$ITEM" .md)
  MISSING=""
  # Musí mít ≥2 věty popisu (ne jen title)
  BODY_LINES=$(sed -n '/^---$/,/^---$/!p' "$ITEM" | grep -c '\S')
  [ "$BODY_LINES" -lt 3 ] && MISSING="${MISSING} popis(<3 řádky)"
  # Musí mít effort (ne TBD)
  EFFORT=$(grep '^effort:' "$ITEM" | awk '{print $2}')
  [ "$EFFORT" = "TBD" ] || [ -z "$EFFORT" ] && MISSING="${MISSING} effort"
  # Musí mít ≥1 AC
  grep -q '\- \[.\]' "$ITEM" 2>/dev/null || MISSING="${MISSING} AC"
  if [ -n "$MISSING" ]; then
    echo "WARN: READY item $ITEM_ID missing:${MISSING}"
  fi
done
```

### 7.4) E2E endpoint coverage ratio

```bash
# Počet definovaných routes vs E2E testů
if [ -d "{CODE_ROOT}/api/" ]; then
  ROUTE_COUNT=$(grep -rn '@app\.\(get\|post\|put\|delete\)' {CODE_ROOT}/api/ 2>/dev/null | wc -l)
  E2E_TEST_COUNT=$(grep -rn 'def test.*e2e\|def test.*integration\|def test.*api' {TEST_ROOT}/ 2>/dev/null | wc -l)
  RATIO=0
  if [ "$ROUTE_COUNT" -gt 0 ]; then
    RATIO=$(( E2E_TEST_COUNT * 100 / ROUTE_COUNT ))
  fi
  echo "E2E coverage: $E2E_TEST_COUNT tests / $ROUTE_COUNT routes = ${RATIO}%"
  if [ "$RATIO" -lt 50 ]; then
    echo "WARN: E2E coverage ${RATIO}% < 50% target"
  fi
fi
```

### 7.5) Confidence scoring per check

Pro každý finding v audit reportu přidej confidence level:
- **HIGH (95%+):** Deterministický check (file existence, schema validation, enum match)
- **MEDIUM (70-95%):** Heuristický check (stale detection — threshold může být neadekvátní, grep-based code search)
- **LOW (<70%):** Best-effort check (doc coverage estimation, complexity heuristics)

Formát v reportu: `| Finding | Severity | Confidence | Detail |`

### 7.6) Process Map Freshness validation

Ověř existenci a kvalitu process map dokumentace:

```bash
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
TODAY_EPOCH=$(date +%s)
PROCESS_MAP_FINDINGS=""

# Kontrola existence process-map.md
if [ ! -f "$PROCESS_MAP" ]; then
  # Process map chybí — kritické jen pokud je projekt za Sprint 1
  CURRENT_SPRINT=$(grep '^sprint:' {WORK_ROOT}/state.md 2>/dev/null | awk '{print $2}')
  CURRENT_SPRINT=${CURRENT_SPRINT:-1}
  if [ "$CURRENT_SPRINT" -gt 1 ]; then
    echo "CRITICAL: process-map.md is missing (Sprint ${CURRENT_SPRINT} > 1)"
    PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **CRITICAL:** Process map chybí (Sprint ${CURRENT_SPRINT} > 1) → intake: process-map-missing"
  else
    echo "INFO: process-map.md doesn't exist yet (Sprint 1)"
  fi
else
  # Kontrola freshness (updated field)
  UPDATED=$(grep '^updated:' "$PROCESS_MAP" | awk '{print $2}')
  if [ -n "$UPDATED" ]; then
    UPDATED_EPOCH=$(date -d "$UPDATED" +%s 2>/dev/null || echo 0)
    DAYS_OLD=$(( (TODAY_EPOCH - UPDATED_EPOCH) / 86400 ))
    if [ "$DAYS_OLD" -gt 7 ]; then
      echo "WARN: process-map.md is ${DAYS_OLD}d old (>7d stale)"
      PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **HIGH:** Process map stale (${DAYS_OLD}d old) → intake: process-map-stale"
    else
      echo "PASS: process-map.md is fresh (${DAYS_OLD}d old)"
    fi
  else
    echo "WARN: process-map.md missing 'updated:' field"
    PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **MEDIUM:** Process map missing updated field"
  fi

  # Kontrola orphan count (UNIMPLEMENTED/ORPHAN markers)
  ORPHAN_COUNT=$(grep -c 'UNIMPLEMENTED\|ORPHAN' "$PROCESS_MAP" 2>/dev/null || echo 0)
  if [ "$ORPHAN_COUNT" -gt 0 ]; then
    echo "INFO: process-map.md has $ORPHAN_COUNT orphan/unimplemented entries"
    PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **INFO:** Process map contains ${ORPHAN_COUNT} UNIMPLEMENTED/ORPHAN entries"
  fi
fi
```

Výstupy:
- Pokud `process-map.md` neexistuje a `state.sprint > 1` → vytvoř intake item `intake/check-process-map-missing.md`, reportuj **CRITICAL**
- Pokud `process-map.md` existuje ale `updated` je >7 dní starý → vytvoř intake item `intake/check-process-map-stale.md`, reportuj **HIGH**
- Pokud `process-map.md` má >0 UNIMPLEMENTED/ORPHAN → zaznamenej do reportu jako INFO (orientační)
- Přílož `$PROCESS_MAP_FINDINGS` do audit reportu

### 8) Vygeneruj audit report

Vytvoř `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` dle `{WORK_ROOT}/templates/audit-report.md`:
- summary + score
- CRITICAL/WARNING findings
- auto-fixes
- intake items created

---

## Scoring — Aggregation Formula (WQ5 fix — enforceable)

**Formula:**
```
SCORE = 100 - (CRITICAL_COUNT × 30) - (HIGH_COUNT × 10) - (MEDIUM_COUNT × 3) - (LOW_COUNT × 1)
VERDICT = SCORE ≥ 80 ? PASS : SCORE ≥ 50 ? WARN : FAIL
```

**Coverage floor check (WQ9 fix):**
```bash
# POVINNĚ: Spusť pytest s --cov
COVERAGE_REPORT=$(mktemp)
{COMMANDS.test} --cov={CODE_ROOT} --cov-report=term-missing > "$COVERAGE_REPORT" 2>&1

# Extrahuj celkový coverage %
TOTAL_COVERAGE=$(grep "TOTAL" "$COVERAGE_REPORT" | awk '{print $NF}' | sed 's/%//')

# Ověř minimální floor (default 50%)
COVERAGE_FLOOR=$(grep 'coverage_floor:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "50")

if [ -z "$TOTAL_COVERAGE" ]; then
  echo "WARN: Could not extract coverage percentage"
  COVERAGE_SCORE=0
elif [ "${TOTAL_COVERAGE%.*}" -lt "$COVERAGE_FLOOR" ]; then
  echo "CRITICAL: Code coverage ${TOTAL_COVERAGE}% < floor ${COVERAGE_FLOOR}%"
  CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
else
  echo "PASS: Code coverage ${TOTAL_COVERAGE}% >= floor ${COVERAGE_FLOOR}%"
fi
```

**Confidence enforcement (WQ10 fix):**
```bash
# KAŽDÝ finding MUSÍ mít confidence level. Pokud chybí → default LOW
# V reportu: formát = | Finding | Severity | Confidence | Detail |
# Povinné confidence hodnoty: HIGH (95%+) | MEDIUM (70-95%) | LOW (<70%)

# Validace: pokud je finding bez confidence v reportu → warning
grep -E '^\|.*\|.*CRITICAL|HIGH|MEDIUM|LOW\|' "$AUDIT_REPORT" | while read -r line; do
  if ! echo "$line" | grep -qE '\(HIGH|MEDIUM|LOW\)'; then
    echo "WARN: Finding without confidence level: $line"
  fi
done
```

**Repair procedures for each finding type (WQ4 fix):**

**Finding: Missing COMMANDS.test**
- Repair: Edit config.md, add COMMANDS.test: `pytest -q`
- Verification: `grep 'COMMANDS.test' {WORK_ROOT}/config.md` should return non-empty, non-TBD value

**Finding: Backlog item missing 'prio' field**
- Repair (auto-fix): Add `prio: 0` to YAML frontmatter
- Verification: `grep '^prio:' backlog/*.md | wc -l` should equal item count

**Finding: Stale item (>30 days unchanged)**
- Repair: Update `updated:` field to today's date OR move to done/ if completed
- Verification: `grep '^updated:' backlog/item-id.md` shows current date

**Finding: Process map missing or stale (>7 days)**
- Repair: Run `fabric-process` skill to regenerate
- Verification: `grep '^updated:' {WORK_ROOT}/fabric/processes/process-map.md` shows recent date (≤7d)

**Finding: Governance index out of sync**
- Repair: Run auto-fix: `python skills/fabric-init/tools/fabric.py governance-index`
- Verification: `{WORK_ROOT}/decisions/INDEX.md` and `{WORK_ROOT}/specs/INDEX.md` are current (contain all files in dirs)

**Stale thresholds — from config.md (WQ5 fix — ne hardcoded, with justification):**
```bash
# Nenačítej hardcoded hodnoty — vždycky z config.md
STALE_ITEM_DAYS=$(grep 'backlog_stale_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "30")
STALE_EPIC_DAYS=$(grep 'epic_stale_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "60")
STALE_REPORT_GAP_DAYS=$(grep 'report_stale_gap_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "30")

# WQ5 justification for thresholds:
# - STALE_ITEM_DAYS=30: typical 2-week sprint means item active every 2 weeks; 30d = miss 2 sprints
# - STALE_EPIC_DAYS=60: epics are longer-lived; 60d = miss 4 sprints (acceptable for multi-sprint epics)
# - STALE_REPORT_GAP_DAYS=30: analysis reports should refresh ≤monthly; >30d = data drift risk

echo "Using stale thresholds from config.md: items=${STALE_ITEM_DAYS}d (>2 sprints), epics=${STALE_EPIC_DAYS}d (>4 sprints), reports=${STALE_REPORT_GAP_DAYS}d"
```

**Contract module test coverage check (WQ9 fix):**
```bash
# Pro KAŻDY governance registry modul, ověř, že existuje test
# Načti seznam ze config.md GOVERNANCE.decisions.registry
grep -A 100 'registry:' "{WORK_ROOT}/config.md" | grep -E '^\s*-' | while read -r module; do
  MOD=$(echo "$module" | sed 's/.*:\s*\[//' | sed 's/\].*//' | xargs)
  TEST_FILE=$(echo "$MOD" | sed 's|/|_|g' | sed 's|\.py||')

  if [ -z "$(find "${TEST_ROOT}" -name "*${TEST_FILE}*test*.py" -o -name "*test*${TEST_FILE}*.py" 2>/dev/null)" ]; then
    echo "HIGH: Governance module $MOD has no test coverage"
    HIGH_COUNT=$((HIGH_COUNT + 1))
  fi
done
```

**Scoring example:**
```
2 CRITICAL × 30 = 60 points
1 HIGH × 10 = 10 points
0 MEDIUM = 0 points
2 LOW × 1 = 2 points
SCORE = 100 - 60 - 10 = 30 → FAIL
```

---

## Populated Audit Report Example with LLMem data (WQ2 fix)

```markdown
---
schema: fabric.report.v1
kind: check
run_id: "check-2026-03-06-abc123"
created_at: "2026-03-06T14:30:00Z"
version: "1.0"                                   # WQ9 fix: track report version
status: WARN
score: 65
---

# check — Audit Report 2026-03-06

## Summary

Workspace audit found 2 CRITICAL issues (missing test command, stale process map), 1 HIGH issue (governance drift), and auto-fixed 3 backlog item metadata gaps. Score: 65/100 (WARN). All CRITICAL issues have intake items.

## Metrics

| Check | Result | Detail |
|-------|--------|--------|
| Structural integrity | PASS | All required directories exist |
| Backlog schema | WARN | 3 items missing 'prio' field (auto-fixed) |
| Backlog vision-fit | PASS | All T0/T1 items linked to vision goals |
| Governance index | PASS | decisions/ and specs/ indices present and current |
| Sprint plan | PASS | Sprint 5 task queue validated, all items exist |
| Config COMMANDS | CRITICAL | COMMANDS.test is TBD (blocks testing) |
| Process map | WARN | process-map.md stale (8 days old, threshold 7d) |
| Code coverage | CRITICAL | 42% < 50% floor (collected from last pytest run) |
| Lint/Format | SKIPPED | COMMANDS.lint empty, format_check TBD |
| Governance module tests | HIGH | Module triage/patterns.py has no test coverage |

## Findings (High → Low severity)

| Finding | Severity | Confidence | Intake Item |
|---------|----------|------------|-------------|
| COMMANDS.test is TBD — tests cannot run | CRITICAL | HIGH (deterministic check) | check-missing-test-command |
| Code coverage 42% < floor 50% — need >50% coverage | CRITICAL | HIGH (measured from pytest run) | check-coverage-floor-failed |
| Governance module triage/patterns.py has 0 test coverage | HIGH | MEDIUM (heuristic: grep-based detection) | check-missing-governance-tests |
| Process map stale (8 days old, threshold 7) | MEDIUM | HIGH (timestamp-based) | check-process-map-stale |
| Backlog items: 3 missing 'prio' field (auto-fixed) | LOW | HIGH (schema validation) | None (auto-fixed) |

## Auto-fixes applied

- ✓ Regenerated backlog.md index (5 items reordered by priority)
- ✓ Added missing 'prio' fields to 3 backlog items (set to 0, needs manual review)
- ✓ Regenerated governance/INDEX.md for decisions

## Intake items created

1. `intake/check-missing-test-command.md` — COMMANDS.test must be configured
2. `intake/check-coverage-floor-failed.md` — Coverage 42% needs to reach 50% floor
3. `intake/check-missing-governance-tests.md` — Add tests for triage/patterns.py

## Warnings

- Process map not updated for 8 days — recommend running fabric-process to refresh
- 2 backlog items (epic-data-pipeline, task-llmem-ui-mockup) unchanged for >30 days
- Report freshness: gap-* report is 35 days old (threshold 30 days)

## Configuration notes

- Coverage floor: 50% (from config.md)
- Stale item threshold: 30 days (default)
- Stale epic threshold: 60 days (default)
- Report freshness thresholds: gap=30d, prio=45d, check=15d
```

## Self-check

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Všechny referované intake items existují v `{WORK_ROOT}/intake/` (pokud CRITICAL findings)
- [ ] Protocol log má START a END záznam s `skill: check`

### Quality checks
- [ ] Audit report má všechny povinné sekce: Summary, Metrics, Findings (tabulka se Severity+Confidence), Auto-fixes, Intake items, Warnings
- [ ] Pokud byly auto-fixes, jsou konkrétně popsány v reportu (soubor + before/after)
- [ ] Pro každý CRITICAL finding existuje intake item s odkazem (`source: check`, `linked_finding: {finding_id}`)
- [ ] Findings tabulka má sloupce: Finding, Severity, Confidence, Location (file:line), Auto-fix applied, Status
- [ ] Pokud audit PASS, report obsahuje summary: `0 CRITICAL, N WARN, M INFO`

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/reports/` a `{WORK_ROOT}/intake/` nebyl modifikován (fabric-check je read-only audit)
- [ ] Backlog.md NENÍ modifikován (audit nesmí měnit backlog bez intake item)
- [ ] State.md NENÍ modifikován
- [ ] Protocol log má START i END záznam

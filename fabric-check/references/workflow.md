# fabric-check — Detailní procedury

## 1) Strukturální integrita workspace

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

## 2) Templates integrity

Ověř, že v `{WORK_ROOT}/templates/` existují povinné šablony (viz config).
Pokud chybí → WARNING + intake.

## 3) Backlog item schema audit

Z `{WORK_ROOT}/config.md` načti kontrakty:
- `SCHEMA.backlog_item`
- `ENUMS.statuses`, `ENUMS.tiers`, `ENUMS.efforts`, `ENUMS.types`

Pro každý `{WORK_ROOT}/backlog/*.md` (mimo `backlog/done/`):

```bash
MAX_FINDINGS=${MAX_FINDINGS:-500}
FINDING_COUNTER=0

for item_file in {WORK_ROOT}/backlog/*.md; do
  FINDING_COUNTER=$((FINDING_COUNTER + 1))
  if [ "$FINDING_COUNTER" -ge "$MAX_FINDINGS" ]; then
    echo "WARN: max audit findings reached ($FINDING_COUNTER/$MAX_FINDINGS)"
    break
  fi
  # ... validate item schema
done
```

**Validace per item:**
- parse YAML frontmatter
- ověř povinné klíče: `schema`, `id`, `title`, `type`, `tier`, `status`, `effort`, `created`, `updated`, `source`, `prio`
- validuj hodnoty:
  - `schema` == `SCHEMA.backlog_item`
  - `status` ∈ `ENUMS.statuses`
  - `type` ∈ `ENUMS.types`
  - `tier` ∈ `ENUMS.tiers`
  - `effort` ∈ `ENUMS.efforts`
  - `prio` je integer
  - filename odpovídá `id` (např. `{id}.md`)

**Safe auto-fix (idempotentní):**
- pokud chybí `schema`, doplň `schema: <SCHEMA.backlog_item>`
- pokud chybí `updated`, doplň `updated: {YYYY-MM-DD}`
- pokud chybí `prio`, doplň `prio: 0` (a reportuj WARNING)

**Ne-safe (→ intake + WARNING/CRITICAL):**
- chybějící `id` nebo `title`
- `schema` existuje, ale je **jiný** než očekávaný (drift)
- nevalidní status/type/tier/effort

## 3.1) Vision-fit lint (backlog ↔ vize)

Cíl: zabránit tomu, aby se backlog stal „košem na všechno".

Pro každý backlog item (mimo `done/`):
- načti `tier` a `linked_vision_goal` (pokud existuje)

**Pravidla:**
- pokud `tier` je `T0` nebo `T1` a `linked_vision_goal` chybí nebo je prázdné:
  - vytvoř intake item `{WORK_ROOT}/intake/check-missing-vision-link-{id}.md`
  - do něj napiš: co chybí (goal/pillar), a návrh: doplnit `linked_vision_goal` nebo snížit tier
  - reportuj jako WARNING

- pokud `linked_vision_goal` je vyplněné, ale **neobjevuje se** ani v `{WORK_ROOT}/vision.md` ani v `{VISIONS_ROOT}/*.md`:
  - vytvoř intake item `{WORK_ROOT}/intake/check-unknown-vision-link-{id}.md`
  - reportuj WARNING (vision drift / překlep / chybí sub-vize)

## 4) Backlog index sync

Regeneruj „expected" tabulku z backlog itemů a porovnej s `{WORK_ROOT}/backlog.md`.

Pokud nesedí:
- safe auto-fix: přepiš backlog.md na kanonickou tabulku (seřazení PRIO desc)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```
- zapiš do reportu jako FIXED

## 4.1) Governance integrity (decisions/specs/reviews)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py governance-index
python skills/fabric-init/tools/fabric.py governance-scan
```

Vyhodnoť:
- chybějící `INDEX.md` → WARNING + intake (nebo auto-fix přes `governance-index`)
- proposed ADR starší než `GOVERNANCE.decisions.stale_proposed_days` → WARNING + intake
- draft SPEC starší než `GOVERNANCE.specs.stale_draft_days` → WARNING + intake
- missing `date`/`status` ve governance souborech → WARNING + intake

Pozn.: `governance-index` je safe auto-fix (jen přegeneruje indexy).

## 5) Sprint plan audit (pokud existuje)

Najdi aktuální sprint:
- ze `state.md` (`sprint: N`)
- sprint file: `{WORK_ROOT}/sprints/sprint-{N}.md` (pokud existuje)

**Validace:**
- má sekce `## Sprint Targets`
- má sekce `## Task Queue` s tabulkou
- každý Task Queue `ID` existuje jako backlog item
- `Order` je unikátní a začíná od 1 (nebo je aspoň monotónní)

Pokud Task Queue odkazuje na neexistující backlog item → CRITICAL + intake.

## 6) Config COMMANDS sanity

Z configu ověř:

- `COMMANDS.test` není `TBD` ani prázdné
- `COMMANDS.lint` není `TBD` *(prázdné = vypnuto)*
- `COMMANDS.format_check` není `TBD` *(prázdné = vypnuto)*

**COMMANDS.test:**
- Je-li `TBD` nebo prázdné: vytvoř intake item `intake/check-missing-test-command.md`, reportuj **CRITICAL**

**COMMANDS.lint a COMMANDS.format_check:**
- Je-li `TBD`: vytvoř intake item `intake/check-config-commands-tbd.md`, reportuj **WARNING**
- Je-li prázdné: reportuj `SKIPPED`, vytvoř intake item `intake/check-recommend-enable-lint-or-format.md` (doporučení)

**QUALITY.mode = strict:**
- Pokud lint/format jsou prázdné (`""`): reportuj **CRITICAL**, vytvoř intake item, FAIL

## 7) Volitelné runtime checks (pokud commands existují)

Pokud repo má čistý working tree:

```bash
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi
{COMMANDS.test}
```

Výsledek zapiš do reportu (PASS/FAIL).

### Auto-fix (safe, idempotentní)

Pokud lint nebo format check failne a config má příslušný fix příkaz, **spusť auto-fix a opakuj gate**:

1. **Lint fail** + `COMMANDS.lint_fix` není prázdné → spusť `{COMMANDS.lint_fix}`, pak znovu `{COMMANDS.lint}`.
2. **Format fail** + `COMMANDS.format` není prázdné → spusť `{COMMANDS.format}`, pak znovu `{COMMANDS.format_check}`.

Auto-fix smí proběhnout **max 1×** per gate. Pokud po auto-fixu gate stále failne → zapiš do reportu jako FAIL a vytvoř intake item.

Pokud auto-fix něco opravil, commitni změny:
```bash
git add -A && git commit -m "chore: auto-fix lint/format (fabric-check)"
```

Volitelně (framework self-test):
```bash
python skills/fabric-init/tools/validate_fabric.py --workspace --runnable
```
Pokud failne → CRITICAL + intake item `intake/check-validator-failed.md`.

## 7.1) Stale detection (backlog items + epics) — WQ10 BLOCKING

```bash
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

Stale items zapiš do audit reportu + vytvoř intake items pro top 5 nejstarších.

## 7.2) Report freshness monitoring

```bash
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

## 7.3) Spec completeness check (READY items)

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

## 7.4) E2E endpoint coverage ratio

```bash
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

## 7.5) Confidence scoring per check

Pro každý finding v audit reportu přidej confidence level:
- **HIGH (95%+):** Deterministický check (file existence, schema validation, enum match)
- **MEDIUM (70-95%):** Heuristický check (stale detection — threshold může být neadekvátní, grep-based code search)
- **LOW (<70%):** Best-effort check (doc coverage estimation, complexity heuristics)

Formát v reportu: `| Finding | Severity | Confidence | Detail |`

## 7.6) Process Map Freshness validation

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

**Výstupy:**
- Pokud `process-map.md` neexistuje a `state.sprint > 1` → vytvoř intake item `intake/check-process-map-missing.md`, reportuj **CRITICAL**
- Pokud `process-map.md` existuje ale `updated` je >7 dní starý → vytvoř intake item `intake/check-process-map-stale.md`, reportuj **HIGH**
- Pokud `process-map.md` má >0 UNIMPLEMENTED/ORPHAN → zaznamenej do reportu jako INFO
- Přílož `$PROCESS_MAP_FINDINGS` do audit reportu

## 8) Vygeneruj audit report

Vytvoř `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` dle šablony:
- summary + score
- CRITICAL/WARNING findings
- auto-fixes
- intake items created

Scoring:
```
SCORE = 100 - (CRITICAL_COUNT × 30) - (HIGH_COUNT × 10) - (MEDIUM_COUNT × 3) - (LOW_COUNT × 1)
VERDICT = SCORE ≥ 80 ? PASS : SCORE ≥ 50 ? WARN : FAIL
```

### Coverage floor check (WQ9 fix):
```bash
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

### Repair procedures for each finding type (WQ4 fix):

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
- Verification: `{WORK_ROOT}/decisions/INDEX.md` and `{WORK_ROOT}/specs/INDEX.md` are current

### Stale thresholds — from config.md (WQ5 fix — ne hardcoded, with justification):
```bash
STALE_ITEM_DAYS=$(grep 'backlog_stale_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "30")
STALE_EPIC_DAYS=$(grep 'epic_stale_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "60")
STALE_REPORT_GAP_DAYS=$(grep 'report_stale_gap_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "30")

# WQ5 justification:
# - STALE_ITEM_DAYS=30: typical 2-week sprint means item active every 2 weeks; 30d = miss 2 sprints
# - STALE_EPIC_DAYS=60: epics are longer-lived; 60d = miss 4 sprints (acceptable for multi-sprint epics)
# - STALE_REPORT_GAP_DAYS=30: analysis reports should refresh ≤monthly; >30d = data drift risk
```

### Contract module test coverage check (WQ9 fix):
```bash
grep -A 100 'registry:' "{WORK_ROOT}/config.md" | grep -E '^\s*-' | while read -r module; do
  MOD=$(echo "$module" | sed 's/.*:\s*\[//' | sed 's/\].*//' | xargs)
  TEST_FILE=$(echo "$MOD" | sed 's|/|_|g' | sed 's|\.py||')

  if [ -z "$(find "${TEST_ROOT}" -name "*${TEST_FILE}*test*.py" -o -name "*test*${TEST_FILE}*.py" 2>/dev/null)" ]; then
    echo "HIGH: Governance module $MOD has no test coverage"
    HIGH_COUNT=$((HIGH_COUNT + 1))
  fi
done
```

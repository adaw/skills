# fabric-sprint — Detailní pracovní postup

Tato příloha obsahuje kompletní algoritmy a procedury pro jednotlivé kroky spritu.

---

## Postup kroku 7.1 — Načti konfiguraci

**Co:** Přečti SPRINT pravidla (max_days, max_tasks, wip_limit) a taxonomii z `{WORK_ROOT}/config.md`.

**Jak:**
```bash
# Přečti config a extrahuj SPRINT sektor
SPRINT_MAX_DAYS=$(grep -A 20 '## SPRINT' "{WORK_ROOT}/config.md" | grep 'max_days:' | awk '{print $2}')
SPRINT_MAX_TASKS=$(grep -A 20 '## SPRINT' "{WORK_ROOT}/config.md" | grep 'max_tasks:' | awk '{print $2}')
SPRINT_WIP_LIMIT=$(grep -A 20 '## SPRINT' "{WORK_ROOT}/config.md" | grep 'wip_limit:' | awk '{print $2}')

# Defaulty pokud chybí
SPRINT_MAX_DAYS=${SPRINT_MAX_DAYS:-5}
SPRINT_MAX_TASKS=${SPRINT_MAX_TASKS:-10}
SPRINT_WIP_LIMIT=${SPRINT_WIP_LIMIT:-1}

# Extrahuj COMMANDS pro test, lint
COMMANDS_TEST=$(grep -A 20 '## COMMANDS' "{WORK_ROOT}/config.md" | grep 'test:' | sed 's/.*: //')
COMMANDS_LINT=$(grep -A 20 '## COMMANDS' "{WORK_ROOT}/config.md" | grep 'lint:' | sed 's/.*: //')

# Pokud SPRINT nebo COMMANDS chybí → vytvoř intake item a pokračuj s defaulty
if [ -z "$SPRINT_MAX_DAYS" ]; then
  echo "WARN: SPRINT config missing, using defaults"
  # Vytvoř intake item: intake/config-missing-sprint-or-commands.md
  cat > "{WORK_ROOT}/intake/config-missing-sprint-or-commands.md" <<EOF
---
schema: fabric.intake_item.v1
title: "SPRINT or COMMANDS block missing in config.md"
source: fabric-sprint
initial_type: Chore
raw_priority: 5
created: $(date +%Y-%m-%d)
status: new
---

## Kontext
fabric-sprint pokusil se načíst SPRINT a COMMANDS konfigurace z {WORK_ROOT}/config.md, ale blok chybí.

## Doporučená akce
Přidej do config.md SPRINT a COMMANDS bloky. Viz fabric-init template.
EOF
fi
```

**Minimum:** Máš SPRINT_MAX_DAYS, SPRINT_MAX_TASKS, SPRINT_WIP_LIMIT (defaulty OK).

---

## Postup kroku 7.2 — Načti state a zjisti sprint N

**Co:** Přečti `{WORK_ROOT}/state.md` → extrahuj `active_sprint = N`. Ověř, že N je číslo (K2 fix).

**Jak:**
```bash
CURRENT_SPRINT=$(grep 'active_sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')

# K2 Fix: Sprint counter enforcement — validate active_sprint is numeric
if ! echo "$CURRENT_SPRINT" | grep -qE '^[0-9]+$'; then
  echo "WARN: active_sprint is not a valid integer: $CURRENT_SPRINT"
  CURRENT_SPRINT=1
fi

echo "Processing sprint $CURRENT_SPRINT"
```

**Minimum:** Máš CURRENT_SPRINT jako číslo.

---

## Postup kroku 7.3 — Načti backlog kandidáty

**Co:** Vyfiltruj z `{WORK_ROOT}/backlog.md` tabulky položky s statusem ≠ DONE, preferuj READY a DESIGN.

**Jak:**
```bash
# Načti backlog index
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "STOP: backlog.md not found"
  exit 1
fi

# Vyfiltruj kandidáty (neguj DONE status)
CANDIDATES=$(grep '^| ' "{WORK_ROOT}/backlog.md" | \
  grep -v '^| *ID\|^|---|' | \
  grep -v '| *DONE\|| *CLOSED' | \
  awk -F'|' '{print $2, $3, $6}' | tr -d ' ')

# Seřaď podle priority (sloupec 3)
SORTED_CANDIDATES=$(echo "$CANDIDATES" | sort -t' ' -k3 -rn)

echo "Found $(echo "$SORTED_CANDIDATES" | wc -l) candidate items"

# Fallback: pokud backlog.md neexistuje, načti individual backlog/*.md files
if [ -z "$SORTED_CANDIDATES" ]; then
  echo "WARN: No candidates in backlog.md table, trying backlog/*.md files"
  for backlog_item in {WORK_ROOT}/backlog/*.md; do
    [ -f "$backlog_item" ] || continue
    ITEM_ID=$(basename "$backlog_item" .md)
    ITEM_PRIO=$(grep '^prio:' "$backlog_item" | awk '{print $2}')
    echo "$ITEM_ID $ITEM_PRIO"
  done | sort -t' ' -k2 -rn | head -"${SPRINT_MAX_TASKS}"
fi
```

**Minimum:** Máš seznam CANDIDATES seřazený podle priority.

---

## Postup kroku 7.4 — Effort Estimation Algorithm

**Co:** Vypočítej effort (XS/S/M/L/XL) pro každý kandidát.

**Jak:**

```bash
# EFFORT ESTIMATION ALGORITHM

estimate_effort() {
  local TASK_ID="$1"
  local TASK_FILE="{WORK_ROOT}/backlog/${TASK_ID}.md"

  # Zkoumej popisující parametry (pseudoalgoritmus)
  FILES=$(grep -c "^src/" "$TASK_FILE" 2>/dev/null || echo 1)
  TESTS=$(grep -c "^def test_" "$TASK_FILE" 2>/dev/null || echo 1)
  COMPLEXITY=$(grep "complexity:" "$TASK_FILE" 2>/dev/null | awk '{print $2}' || echo 5)

  # Mapuj na effort:
  if [ "$FILES" -le 2 ] && [ "$TESTS" -le 3 ] && [ "$COMPLEXITY" -le 5 ]; then
    echo "XS"
  elif [ "$FILES" -le 4 ] && [ "$TESTS" -le 6 ] && [ "$COMPLEXITY" -le 8 ]; then
    echo "S"
  elif [ "$FILES" -le 8 ] && [ "$TESTS" -le 12 ] && [ "$COMPLEXITY" -le 12 ]; then
    echo "M"
  elif [ "$FILES" -le 15 ] && [ "$TESTS" -le 20 ] && [ "$COMPLEXITY" -le 18 ]; then
    echo "L"
  else
    echo "XL"
  fi
}

# Příklad
# estimate_effort "T-101" → "S"
```

**Effort mapping na hodiny:**
- XS: < 4 hours
- S: 4-8 hours
- M: 8-16 hours
- L: 16-32 hours
- XL: > 32 hours (MUSÍ se rozdělit na 2+ tasks)

**Minimum:** Máš effort estimate pro každý kandidát.

**Anti-pattern:** ❌ XL tasks v sprintu bez rozdělení (vede k overrun).

---

## Postup kroku 7.5 — Vyber Sprint Targets

**Co:** Vyber top N items (max `SPRINT.max_tasks`) s fokusem. Každý target musí mít effort, status, AC.

**Jak:**

```bash
# Sprint size limit (P2 work quality)
MAX_TASKS_PER_SPRINT=12  # hard cap
RECOMMENDED_RANGE_MIN=5
RECOMMENDED_RANGE_MAX=8

# Vyběr algoritmem:
# 1. Vezmi top items podle priority
# 2. Respektuj max_tasks config limit
# 3. Pro Epic/Story: můžou být v Targets, ale impl přes tasks
# 4. Vybalancuj: max 40% L tasks, zbytek S/M

SELECTED_TARGETS=()
SELECTED_EFFORT_SUM=0
L_TASK_COUNT=0
TOTAL_CANDIDATES=$(echo "$SORTED_CANDIDATES" | wc -l)

while read prio_id prio priority; do
  [ -z "$prio_id" ] && continue

  # Validuj ID format (K7: Input Validation)
  if ! echo "$prio_id" | grep -qE '^[a-zA-Z0-9_-]+$'; then
    echo "WARN: invalid item ID format: '$prio_id' — skipping"
    continue
  fi

  EFFORT=$(estimate_effort "$prio_id")

  # Mapuj effort na číslo pro sumaci
  case $EFFORT in
    XS) EFFORT_NUM=3 ;;
    S) EFFORT_NUM=7 ;;
    M) EFFORT_NUM=12 ;;
    L) EFFORT_NUM=24 ;;
    XL) EFFORT_NUM=40 ;;
  esac

  # Ověř czy máme kapacitu
  if [ ${#SELECTED_TARGETS[@]} -ge "$MAX_TASKS_PER_SPRINT" ]; then
    echo "INFO: max sprint tasks reached ($MAX_TASKS_PER_SPRINT)"
    break
  fi

  # Ověř L task ratio (max 40%)
  if [ "$EFFORT" = "L" ]; then
    L_TASK_COUNT=$((L_TASK_COUNT + 1))
    MAX_L_ALLOWED=$((${#SELECTED_TARGETS[@]} * 40 / 100))
    if [ "$L_TASK_COUNT" -gt "$MAX_L_ALLOWED" ]; then
      echo "INFO: skipping $prio_id (L task, ratio exceeded)"
      continue
    fi
  fi

  SELECTED_TARGETS+=("$prio_id")
  SELECTED_EFFORT_SUM=$((SELECTED_EFFORT_SUM + EFFORT_NUM))
  echo "Selected: $prio_id (effort=$EFFORT, sum=$SELECTED_EFFORT_SUM)"
done <<< "$SORTED_CANDIDATES"

# Výstup
echo "=== SPRINT TARGET SELECTION ==="
echo "Selected ${#SELECTED_TARGETS[@]} targets (recommended: $RECOMMENDED_RANGE_MIN-$RECOMMENDED_RANGE_MAX)"
if [ ${#SELECTED_TARGETS[@]} -lt "$RECOMMENDED_RANGE_MIN" ] || [ ${#SELECTED_TARGETS[@]} -gt "$RECOMMENDED_RANGE_MAX" ]; then
  echo "WARN: Sprint size outside recommended range"
fi
```

**Minimum:** Máš seznam SELECTED_TARGETS seřazený podle priority, s effort estimates.

**Anti-pattern:** ❌ Příliš mnoho DESIGN items (vede ke skluzu). Cíl: >50% READY.

**Sprint goal:** Napiš jako 1 větu, která shrnuje společný outcome všech targetů. Např. "Zabezpečit API validací a rate limitingem; zvýšit coverage nad 70%."

---

## Postup kroku 7.6 — Dependency Graph & Ordering

**Co:** Sestav tabulku depencí, topologicky seřaď, identifikuj critical path.

**Jak:**

```bash
# Dependency extraction
declare -A TASK_DEPS
declare -A TASK_BLOCKS

for task_id in "${SELECTED_TARGETS[@]}"; do
  TASK_FILE="{WORK_ROOT}/backlog/${task_id}.md"

  # Extrahuj "depends_on:" z frontmatter
  DEPS=$(grep "^depends_on:" "$TASK_FILE" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
  TASK_DEPS[$task_id]="$DEPS"

  # Compute reverse: who does this task block?
  for other_task in "${SELECTED_TARGETS[@]}"; do
    OTHER_FILE="{WORK_ROOT}/backlog/${other_task}.md"
    OTHER_DEPS=$(grep "^depends_on:" "$OTHER_FILE" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
    if echo "$OTHER_DEPS" | grep -qw "$task_id"; then
      TASK_BLOCKS[$task_id]="${TASK_BLOCKS[$task_id]} $other_task"
    fi
  done
done

# Topological sort (pseudokód — detect cykly)
detect_cycles() {
  # Jednoduchý DFS check
  local task="$1"
  local -a visited=()
  local -a rec_stack=()

  dfs_visit() {
    local node="$1"
    visited+=("$node")
    rec_stack+=("$node")

    local deps="${TASK_DEPS[$node]}"
    for dep in $deps; do
      if [[ " ${rec_stack[@]} " =~ " ${dep} " ]]; then
        echo "FAIL: Circular dependency detected: $node → $dep → ... → $node"
        return 1
      fi
      if ! [[ " ${visited[@]} " =~ " ${dep} " ]]; then
        dfs_visit "$dep" || return 1
      fi
    done

    rec_stack=("${rec_stack[@]/$node}")
    return 0
  }

  dfs_visit "$task"
}

# Ověř žádné cykly
for task_id in "${SELECTED_TARGETS[@]}"; do
  if ! detect_cycles "$task_id"; then
    echo "FAIL: Sprint has circular dependencies"
    exit 1
  fi
done

# Tabulka depencí
echo ""
echo "## Dependency Graph"
echo ""
echo "| Task ID | Title | Depends On | Blocks | Critical Path |"
echo "|---------|-------|-----------|--------|--------------|"
for task_id in "${SELECTED_TARGETS[@]}"; do
  TASK_FILE="{WORK_ROOT}/backlog/${task_id}.md"
  TITLE=$(grep "^title:" "$TASK_FILE" 2>/dev/null | sed 's/title: //')
  DEPS="${TASK_DEPS[$task_id]:-None}"
  BLOCKS="${TASK_BLOCKS[$task_id]:-None}"
  # Critical path = je-li třeba pro top-level goal?
  CRITICAL="NO"  # LLM rozhoduje na základě kontextu
  echo "| $task_id | $TITLE | $DEPS | $BLOCKS | $CRITICAL |"
done
```

**Minimum:** Máš tabulku depencí bez cyklů, topologicky seřazený task queue.

---

## Postup kroku 7.7 — Risk Assessment

**Co:** Vyhodnoť HIGH/MEDIUM/LOW rizika per target.

**Jak:**

```bash
# Risk matrix
declare -A TASK_RISK

for task_id in "${SELECTED_TARGETS[@]}"; do
  TASK_FILE="{WORK_ROOT}/backlog/${task_id}.md"

  # Heuristics pro riziko
  USES_NEW_TECH=$(grep -i "new technology\|unfamiliar\|spike" "$TASK_FILE" | wc -l)
  IS_ASYNC=$(grep -i "async\|concurrent\|parallel" "$TASK_FILE" | wc -l)
  IS_COMPLEX=$(grep "complexity:" "$TASK_FILE" | awk '{print $2}' | grep -E '^(15|18|20)' | wc -l)

  # Mapuj na risk level
  if [ "$USES_NEW_TECH" -gt 0 ] || [ "$IS_COMPLEX" -gt 0 ]; then
    TASK_RISK[$task_id]="HIGH"
  elif [ "$IS_ASYNC" -gt 0 ]; then
    TASK_RISK[$task_id]="MEDIUM"
  else
    TASK_RISK[$task_id]="LOW"
  fi
done

# Výstup tabulky
echo ""
echo "## Risk Assessment"
echo ""
echo "| Task | Risk Level | Risk Description | Mitigation |"
echo "|------|-----------|------------------|-----------|"
for task_id in "${SELECTED_TARGETS[@]}"; do
  RISK="${TASK_RISK[$task_id]}"

  # LLM napíše description + mitigation na základě kontextu
  DESC="TBD"
  MIT="TBD"

  echo "| $task_id | $RISK | $DESC | $MIT |"
done

# Výstraha pokud >2 HIGH items
HIGH_COUNT=$(for r in "${TASK_RISK[@]}"; do echo "$r"; done | grep -c "^HIGH$")
if [ "$HIGH_COUNT" -gt 2 ]; then
  echo ""
  echo "⚠️  WARNING: Sprint has $HIGH_COUNT HIGH-risk items (>2). Consider increasing WIP limit or reducing scope."
fi
```

**Minimum:** Risk matrix s mitigations pro každý HIGH/MEDIUM item.

---

## Postup kroku 7.8 — Anti-Pattern Detection

**Co:** Detekuj skryté rizika automatizovaně.

**Jak:**

```bash
echo "=== DETECTING HIDDEN SPRINT RISKS ==="

# Anti-pattern 1: All tasks in same module
echo "Checking module concentration..."
MODULES=$(for task_id in "${SELECTED_TARGETS[@]}"; do
  grep "module:" "{WORK_ROOT}/backlog/${task_id}.md" 2>/dev/null | awk '{print $2}' || echo "unknown"
done | sort | uniq -c)
SINGLE_MODULE_TASKS=$(echo "$MODULES" | awk '$1 > 3 {count++} END {print count}')
if [ "$SINGLE_MODULE_TASKS" -gt 0 ]; then
  echo "WARN: >3 tasks in single module (high context switching risk)"
fi

# Anti-pattern 2: Single developer concentration (pokud máme capacity plan)
# → zkontroluj v kroku 7.11

# Anti-pattern 3: Critical path too long
CRITICAL_PATH_LENGTH=$(echo "... tabulka depencí ..." | grep "YES" | wc -l)
if [ "$CRITICAL_PATH_LENGTH" -gt 3 ]; then
  echo "WARN: Critical path has >3 tasks (likely to slip if blocker hits)"
fi

# Anti-pattern 4: Too many tasks in DESIGN status
DESIGN_COUNT=$(for task_id in "${SELECTED_TARGETS[@]}"; do
  grep "^status:" "{WORK_ROOT}/backlog/${task_id}.md" 2>/dev/null
done | grep -c "DESIGN")
READY_COUNT=$(for task_id in "${SELECTED_TARGETS[@]}"; do
  grep "^status:" "{WORK_ROOT}/backlog/${task_id}.md" 2>/dev/null
done | grep -c "READY")
if [ "$DESIGN_COUNT" -gt "$READY_COUNT" ]; then
  echo "WARN: More DESIGN tasks ($DESIGN_COUNT) than READY ($READY_COUNT) — may slip"
fi

# Anti-pattern 5: XL tasks (>32 hours) in sprint
XL_COUNT=$(for task_id in "${SELECTED_TARGETS[@]}"; do
  estimate_effort "$task_id"
done | grep -c "^XL$")
if [ "$XL_COUNT" -gt 0 ]; then
  echo "FAIL: Sprint has $XL_COUNT XL tasks (>32h); must split into L+M"
  exit 1
fi
```

**Minimum:** Bez XL tasks, modul rozprostřen, DESIGN ≤ READY.

---

## Postup kroku 7.9 — Pre-Sprint Gate (BLOCKING Validation)

**Co:** Ověř kapacitu, deps, effort, DoD.

**Jak:**

```bash
echo "=== PRE-SPRINT VALIDATION GATE ==="

# Gate 1: Capacity check
TOTAL_EFFORT=0
for task_id in "${SELECTED_TARGETS[@]}"; do
  EFFORT=$(estimate_effort "$task_id")
  case $EFFORT in
    XS) HOURS=3 ;;
    S) HOURS=7 ;;
    M) HOURS=12 ;;
    L) HOURS=24 ;;
  esac
  TOTAL_EFFORT=$((TOTAL_EFFORT + HOURS))
done

# Spočítej kapacitu: SPRINT_MAX_DAYS * 6h/day * DEVELOPER_COUNT
DEVELOPER_COUNT=$(grep -c "^-" "{WORK_ROOT}/config.md" | grep -A 20 "## TEAM" || echo 1)
TOTAL_CAPACITY=$((SPRINT_MAX_DAYS * 6 * DEVELOPER_COUNT))
UTILIZATION=$((TOTAL_EFFORT * 100 / TOTAL_CAPACITY))

if [ "$UTILIZATION" -gt 90 ]; then
  echo "FAIL: Sprint utilization is ${UTILIZATION}% (>90%). Remove items or reduce scope."
  exit 1
fi
echo "PASS: Capacity check (${UTILIZATION}% utilization, threshold 90%)"

# Gate 2: No circular dependencies
echo "Checking for dependency cycles..."
# Already done in 7.6, tak jen check
if [ "$?" -ne 0 ]; then
  echo "FAIL: Sprint has circular dependencies. Resolve before starting."
  exit 1
fi
echo "PASS: Dependency check (no cycles)"

# Gate 3: All tasks have effort estimates
MISSING_EFFORT=0
for task_id in "${SELECTED_TARGETS[@]}"; do
  EFFORT=$(estimate_effort "$task_id")
  if [ -z "$EFFORT" ] || [ "$EFFORT" = "?" ]; then
    MISSING_EFFORT=$((MISSING_EFFORT + 1))
  fi
done
if [ "$MISSING_EFFORT" -gt 0 ]; then
  echo "FAIL: ${MISSING_EFFORT} tasks missing effort estimates."
  exit 1
fi
echo "PASS: All tasks have effort estimates"

# Gate 4: Definition of Done is complete
DOD_CHECKBOXES=0  # Počítáno v kroku 7.10
if [ "$DOD_CHECKBOXES" -lt 5 ]; then
  echo "FAIL: Definition of Done has <5 checkboxes (insufficient)."
  exit 1
fi
echo "PASS: Definition of Done is complete"

echo "=== PRE-SPRINT GATE PASSED ==="
```

**Minimum:** Utilization ≤ 90%, žádné cykly, všechny estimates, DoD ≥ 5 checkboxes.

---

## Postup kroku 7.10 — Definition of Done (POVINNÉ)

**Co:** Vytvoř explicitní DoD jako CHECKLIST, ne proza.

**Šablona:**

```markdown
## Definition of Done

Sprint {N} je DONE když VŠECHNY tyto kritéria platí:

### Code Quality
- [ ] All tests PASS: `{COMMANDS.test}` exit 0 on main after all merges
- [ ] Linting PASS: `{COMMANDS.lint}` exit 0 (or SKIPPED with explicit reason)
- [ ] Coverage ≥ 60% for modified modules (no regression >5%)
- [ ] No stubs or TODOs in DONE code (pass/NotImplementedError/# TODO)

### Review & Design
- [ ] Code review verdict = CLEAN (no requested changes)
- [ ] Design decisions documented (if design-worthy)
- [ ] All PR comments resolved

### Documentation
- [ ] Public API documented (docstrings + examples if new endpoints)
- [ ] Major changes reflected in docs/ if doc-worthy
- [ ] README updated if behavior changes

### Operational
- [ ] Backlog item status = DONE (all tasks within epic marked DONE)
- [ ] No P0/P1 bugs introduced (verified by QA or automation)
- [ ] Performance regression checked (if applicable)

### Sprint-Specific Goals
- [ ] {Specifické cíle sprintu — např. "zero P0 bugs", "API v2 ready"}
```

**Minimum:** 5+ checkboxes, konkrétní (nie subjektivní), ověřitelné.

**Anti-pattern:** ❌ Proza ("tým je spokojený") — neverifiable.

---

## Postup kroku 7.11 — Capacity Planning

**Co:** Ověř, že TOTAL_EFFORT ≤ SPRINT_CAPACITY. Cíl: 80-90%.

**Jak:**

```bash
# Capacity Planning Table

SPRINT_CAPACITY=$((SPRINT_MAX_DAYS * 6))  # 5 days * 6h/day = 30h per dev

echo "## Capacity Planning"
echo ""
echo "| Dev | Availability | Max Hours | Assigned | Headroom | Utilization |"
echo "|-----|--------------|-----------|----------|----------|------------|"

# Příklad (LLM by měl načíst ze stvarné config):
echo "| Alice | 100% | 30h | 28h | 2h | 93% |"
echo "| Bob | 80% (PTO Wed) | 24h | 22h | 2h | 92% |"
echo "| **TOTAL** | - | 54h | 50h | 4h | 93% |"

echo ""
echo "Cíl: 80-90% utilization (zbytečný headroom pro emergency bugs)."

# Validation
TOTAL_ASSIGNED=50  # LLM počítá reálně
TARGET_CAPACITY=54
UTILIZATION=$((TOTAL_ASSIGNED * 100 / TARGET_CAPACITY))

if [ "$UTILIZATION" -lt 70 ]; then
  echo "WARN: Sprint underutilized (${UTILIZATION}% < 70%) — consider adding more tasks"
elif [ "$UTILIZATION" -gt 95 ]; then
  echo "WARN: Sprint overutilized (${UTILIZATION}% > 95%) — likely to slip"
fi
```

**Minimum:** Capacity table + validation check.

---

## Postup kroku 7.12 — Rollover Tracking

**Co:** Vezmi items z předchozího sprintu (N-1), co nejsou DONE. Analyzuj proč.

**Jak:**

```bash
# Načti předchozí sprint plan
PREVIOUS_SPRINT=$((CURRENT_SPRINT - 1))
PREVIOUS_SPRINT_FILE="{WORK_ROOT}/sprints/sprint-${PREVIOUS_SPRINT}.md"

if [ ! -f "$PREVIOUS_SPRINT_FILE" ]; then
  echo "INFO: No previous sprint found (first sprint)"
else
  echo "## Rollover from Sprint $PREVIOUS_SPRINT"
  echo ""
  echo "| Task | Original Est. | Actual Effort | Reason | Status in Sprint $CURRENT_SPRINT |"
  echo "|------|-------------|----------------|--------|------------------|"

  # Extrahuj items z Task Queue, co nejsou DONE
  grep '^| ' "$PREVIOUS_SPRINT_FILE" | grep -v '^| *Order\|^|---|' | grep -v 'DONE' | while read line; do
    TASK_ID=$(echo "$line" | awk -F'|' '{print $3}' | tr -d ' ')
    EST=$(echo "$line" | awk -F'|' '{print $5}' | tr -d ' ')

    # Přijmi ze kontextu: co se stalo?
    # LLM se rozhoduje na základě backlog/.../status a visibility do real world
    REASON="Underestimated; needs refinement"
    STATUS_IN_THIS="Moved to Sprint $((CURRENT_SPRINT+1))"

    echo "| $TASK_ID | $EST | {actual} | $REASON | $STATUS_IN_THIS |"
  done

  echo ""
  echo "**Rollover Analysis:** Co se neufinancovalo a proč? Jaké improvements?"
fi
```

**Minimum:** Rollover table + lessons learned.

---

## Postup kroku 7.13 — Vytvoř sprint plán

**Co:** Vytvoř `{WORK_ROOT}/sprints/sprint-{N}.md` dle šablony.

**Jak:**

```bash
SPRINT_FILE="{WORK_ROOT}/sprints/sprint-${CURRENT_SPRINT}.md"

cat > "$SPRINT_FILE" <<EOF
---
schema: fabric.report.v1
kind: sprint-plan
version: "1.0"
sprint_number: $CURRENT_SPRINT
start_date: "$(date +%Y-%m-%d)"
end_date: "$(date -d "+${SPRINT_MAX_DAYS} days" +%Y-%m-%d)"
goal: "$SPRINT_GOAL"
max_tasks: $SPRINT_MAX_TASKS
capacity_effort_hours: $((SPRINT_MAX_DAYS * 6 * DEVELOPER_COUNT))
---

# Sprint $CURRENT_SPRINT Plan

## Sprint Targets (Selected by fabric-prio)

| Priority | ID | Type | Title | Status | Effort | Confidence |
|----------|----|----|-------|--------|--------|-----------|
EOF

# Vyplň targets
for ((i=0; i<${#SELECTED_TARGETS[@]}; i++)); do
  task_id="${SELECTED_TARGETS[$i]}"
  priority=$((i+1))
  TASK_FILE="{WORK_ROOT}/backlog/${task_id}.md"

  TYPE=$(grep "^type:" "$TASK_FILE" | awk '{print $2}')
  TITLE=$(grep "^title:" "$TASK_FILE" | sed 's/title: //')
  STATUS=$(grep "^status:" "$TASK_FILE" | awk '{print $2}')
  EFFORT=$(estimate_effort "$task_id")
  CONFIDENCE="High"  # LLM rozhoduje

  echo "| $priority | $task_id | $TYPE | $TITLE | $STATUS | $EFFORT | $CONFIDENCE |" >> "$SPRINT_FILE"
done

# Přidej zbylé sekce (LLM je vyplní detaily)
cat >> "$SPRINT_FILE" <<EOF

## Sprint Goal Justification

{LLM napíše proč jsou tyto targets kritické}

**Effort Budget:** {suma effort estimates}

## Dependency Graph

{Vloženo z kroku 7.6}

## Risk Assessment

{Vloženo z kroku 7.7}

## Capacity Planning

{Vloženo z kroku 7.11}

## Rollover from Sprint $PREVIOUS_SPRINT

{Vloženo z kroku 7.12, pokud existuje}

## Definition of Done

{Vloženo z kroku 7.10}

## Task Queue

| Order | ID | Type | Status | Estimate | Description |
|-------|----|------|--------|----------|-------------|
{LLM vyplní z topologického řazení, výchozí placeholder}
EOF

echo "Created sprint plan: $SPRINT_FILE"
```

**Minimum:** Validní sprint plan s YAML, všechny povinné sekce.

---

## Postup kroku 7.14 — Update state metadata

**Co:** Nastav v `{WORK_ROOT}/state.md` pouze: sprint_started, sprint_ends, sprint_goal.

**Jak:**

```bash
# Čti originální state.md
STATE_FILE="{WORK_ROOT}/state.md"
TEMP_STATE="/tmp/state-update-$$.md"

# Aktualizuj jen tři pole
sed -E 's/^sprint_started:.*/sprint_started: '"$(date +%Y-%m-%d)"'/' "$STATE_FILE" > "$TEMP_STATE"
sed -i -E 's/^sprint_ends:.*/sprint_ends: '"$(date -d "+${SPRINT_MAX_DAYS} days" +%Y-%m-%d)"'/' "$TEMP_STATE"
sed -i -E 's/^sprint_goal:.*/sprint_goal: "'"$(echo "$SPRINT_GOAL" | sed 's/"/\\"/g')"'"/' "$TEMP_STATE"

# Proveď backup + swap
cp "$STATE_FILE" "${STATE_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
mv "$TEMP_STATE" "$STATE_FILE"

echo "Updated state.md with sprint metadata"

# Ověř, že jsme nechangeli phase či step
if grep -qE '^phase:|^step:' "$STATE_FILE".backup-*; then
  NEW_PHASE=$(grep '^phase:' "$STATE_FILE" | awk '{print $2}')
  NEW_STEP=$(grep '^step:' "$STATE_FILE" | awk '{print $2}')
  echo "INVARIANT: phase=$NEW_PHASE, step=$NEW_STEP (unchanged)"
fi
```

**Minimum:** Tři pole aktualizovány, backup vytvořen, phase/step unchanged.

---

## Postup kroku 7.15 — Vytvoř sprint report

**Co:** Vytvoř `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` se summary, risks, analysis.

**Jak:**

```bash
REPORT_FILE="{WORK_ROOT}/reports/sprint-${CURRENT_SPRINT}-$(date +%Y-%m-%d).md"

cat > "$REPORT_FILE" <<EOF
---
schema: fabric.report.v1
kind: sprint
run_id: "sprint-${CURRENT_SPRINT}-$(date +%s)"
created_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status: PASS
---

# Sprint $CURRENT_SPRINT Report — $(date +%Y-%m-%d)

## Souhrn

{LLM napíše 1–3 věty: kolik targetů bylo vybráno, jaký je sprint goal, jaká je kapacita, jaké jsou klíčové rizika}

## Sprint Targets vybrané

| Priority | ID | Type | Title | Effort | Confidence |
|----------|----|----|-------|--------|-----------|
EOF

# Vyplň targets z sprint plánu
grep '^| [0-9]' "$SPRINT_FILE" >> "$REPORT_FILE"

cat >> "$REPORT_FILE" <<EOF

## Rizika a Mitigace

{Vloženo z kroku 7.7}

## Rollover z předchozího sprintu

{Pokud existují carry-over items, seznam s důvody}

## Capacity Analysis

{Vloženo z kroku 7.11}

## Intake items vytvořené

{Seznam nebo "žádné"}

## Warnings

{Seznam nebo "žádné"}
EOF

echo "Created sprint report: $REPORT_FILE"
```

**Minimum:** Validní report s YAML, summary, targets, risks, capacity.

---

## K7: Path Traversal Guard (Input Validation)

**Povinné pro všechny dynamic path inputs:**

```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Aplikuj na všechny dynamic inputs:
for task_id in "${SELECTED_TARGETS[@]}"; do
  validate_path "$task_id"
done
```

---

## K2 Fix: Sprint Selection Counter

**Povinné pro evenci over-selection:**

```bash
MAX_SPRINT_TASKS=${MAX_SPRINT_TASKS:-50}  # hard cap z config
SPRINT_SELECTION_COUNTER=0

SELECTED_ITEMS=()
while read -r backlog_item; do
  SPRINT_SELECTION_COUNTER=$((SPRINT_SELECTION_COUNTER + 1))
  if [ "$SPRINT_SELECTION_COUNTER" -ge "$MAX_SPRINT_TASKS" ]; then
    echo "INFO: max sprint tasks reached ($SPRINT_SELECTION_COUNTER/$MAX_SPRINT_TASKS)"
    break
  fi
  SELECTED_ITEMS+=("$backlog_item")
done
```

---

## End-to-End Target Selection & Capacity Bash

Kompletní bash skript kombinující všechny kroky:

```bash
#!/bin/bash
echo "=== TARGET SELECTION PIPELINE ==="

# 1. Load backlog and sort by priority
echo "Loading backlog candidates..."
CANDIDATES=$(
  grep -E '^- ' {WORK_ROOT}/backlog.md | \
  while read line; do
    ID=$(echo "$line" | grep -oP 'T-\d+')
    PRIO=$(grep "priority: " {WORK_ROOT}/backlog/${ID}.md 2>/dev/null | awk '{print $2}')
    echo "${PRIO:-0} $ID"
  done | sort -rn | head -"${SPRINT.max_tasks}"
)

# 2. Effort estimation for each candidate
echo "Estimating effort..."
declare -A EFFORT_MAP
while read prio id; do
  [ -z "$id" ] && continue

  # Validate item ID format
  if ! echo "$id" | grep -qE '^[a-zA-Z0-9_-]+$'; then
    echo "WARN: invalid item ID format: '$id' — skipping"
    continue
  fi

  FILES=$(grep -l "$id" {CODE_ROOT}/src/**/*.py 2>/dev/null | wc -l)
  TESTS=$(grep -c "def test_" {TEST_ROOT}/test_*.py | grep "$id" | wc -l)
  COMPLEXITY=$(grep -r "cyclomatic" {CODE_ROOT}/src | grep "$id" | awk '{print $NF}' | sort -rn | head -1 || echo 5)

  if [ "$FILES" -le 2 ] && [ "$TESTS" -le 3 ] && [ "$COMPLEXITY" -le 5 ]; then
    EFFORT="XS"
  elif [ "$FILES" -le 4 ] && [ "$TESTS" -le 6 ] && [ "$COMPLEXITY" -le 8 ]; then
    EFFORT="S"
  elif [ "$FILES" -le 8 ] && [ "$TESTS" -le 12 ] && [ "$COMPLEXITY" -le 12 ]; then
    EFFORT="M"
  elif [ "$FILES" -le 15 ] && [ "$TESTS" -le 20 ] && [ "$COMPLEXITY" -le 18 ]; then
    EFFORT="L"
  else
    EFFORT="XL"
  fi
  EFFORT_MAP[$id]=$EFFORT
  echo "$id: $EFFORT (files=$FILES, tests=$TESTS, complexity=$COMPLEXITY)"
done <<< "$CANDIDATES"

# 3. Dependency ordering (topological sort)
echo "Computing dependency order..."
ORDERED_IDS=$(
  echo "$CANDIDATES" | awk '{print $2}' | while read id; do
    DEPS=$(grep "depends_on:" {WORK_ROOT}/backlog/${id}.md 2>/dev/null | awk '{print $2}' | tr ',' ' ')
    echo "$id:$DEPS"
  done | topological_sort 2>/dev/null || echo "$CANDIDATES" | awk '{print $2}'
)

# 4. Capacity check and final selection
echo "Selecting targets within capacity..."
SELECTED=""
TOTAL_EFFORT=0
while read id; do
  EFFORT_VAL=${EFFORT_MAP[$id]}
  case $EFFORT_VAL in
    XS) HOURS=5 ;;
    S) HOURS=7 ;;
    M) HOURS=12 ;;
    L) HOURS=24 ;;
    XL) HOURS=40 ;;
  esac

  if [ $((TOTAL_EFFORT + HOURS)) -le $((SPRINT_DAYS * 6 * DEVELOPER_COUNT)) ]; then
    SELECTED="$SELECTED $id"
    TOTAL_EFFORT=$((TOTAL_EFFORT + HOURS))
  fi
done <<< "$ORDERED_IDS"

echo "Selected ${SELECTED} (total: ${TOTAL_EFFORT}h)"
```

---

## Shrnutí: Workflow Decision Tree

```
1. Načti config (SPRINT, COMMANDS)
   ├─ OK → pokračuj
   └─ Chybí → intake item + defaulty

2. Načti state → CURRENT_SPRINT
   ├─ Je číslo? (K2 fix)
   ├─ Ne → CURRENT_SPRINT=1
   └─ OK → pokračuj

3. Načti backlog kandidáty
   ├─ Je backlog.md? → vyfiltruj
   └─ Není? → načti backlog/*.md

4. Vyber Sprint Targets
   ├─ Effort estimation (algo)
   ├─ Max tasks limit
   ├─ Effort ratio check
   └─ Seřaď dle priority

5. Dependency Graph
   ├─ Extract deps
   ├─ Check cycles
   └─ Topologicky seřaď

6. Risk Assessment
   ├─ HIGH/MEDIUM/LOW per task
   └─ Warn pokud >2 HIGH

7. Anti-Pattern Detection
   ├─ Module concentration
   ├─ Developer concentration
   ├─ Long critical path
   ├─ Too many DESIGN items
   └─ XL tasks (FAIL!)

8. Pre-Sprint Gate
   ├─ Capacity (≤90% util)
   ├─ No cycles
   ├─ All estimates
   ├─ DoD complete
   └─ FAIL? → STOP + intake

9. Definition of Done
   ├─ Code quality checks
   ├─ Review & design
   ├─ Documentation
   ├─ Operational
   └─ Sprint-specific goals

10. Capacity Planning
    ├─ Per-dev allocation
    ├─ Headroom calc
    └─ Warn pokud <70% nebo >95%

11. Rollover Tracking
    ├─ Previous sprint non-DONE items
    ├─ Analysis proč
    └─ Status in this sprint

12. Create Sprint Plan
    ├─ YAML frontmatter
    ├─ All sections
    └─ Topologically ordered task queue

13. Update state
    ├─ sprint_started
    ├─ sprint_ends
    └─ sprint_goal

14. Create Report
    ├─ Summary
    ├─ Targets table
    ├─ Risks & mitigations
    ├─ Capacity analysis
    └─ Status: PASS/WARN/FAIL
```

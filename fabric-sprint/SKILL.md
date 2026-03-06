---
name: fabric-sprint
description: "Create a sprint plan from the prioritized backlog. Selects top candidates (respecting SPRINT.max_tasks and WIP=1 flow), writes {WORK_ROOT}/sprints/sprint-{N}.md using the sprint-plan template, and sets sprint metadata in state.md (goal/start/end). Does not implement code."
---

# SPRINT — Plánování sprintu

## Účel

Vybrat nejlepší kandidáty z backlogu a vytvořit sprint plán (`sprints/sprint-{N}.md`) tak, aby:
- byl konzistentní s vizí,
- respektoval WIP=1 (single-piece flow),
- dal se bez ambiguity převést na konkrétní implementační tasky (`fabric-analyze` doplní `Task Queue`).

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-sprint" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-sprint" --event end --status OK --report "{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy (povinné)

1. `{WORK_ROOT}/config.md` (SPRINT pravidla + taxonomie)
2. `{WORK_ROOT}/state.md` (aktuální sprint N)
3. `{WORK_ROOT}/backlog.md` (prioritizovaný index)
4. `{WORK_ROOT}/backlog/*.md` (detail pro top kandidáty)
5. `{WORK_ROOT}/templates/sprint-plan.md` (kanonická šablona)

---

## Výstupy

- `{WORK_ROOT}/sprints/sprint-{N}.md` (dle šablony)
- Update `{WORK_ROOT}/state.md` (pouze):
  - `sprint_started`
  - `sprint_ends`
  - `sprint_goal`
- Report `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` (co a proč)

---


## FAST PATH (doporučeno)

Než budeš vybírat položky do sprintu, vezmi deterministický backlog snapshot:

```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

Použij ho jako zdroj pravdy pro výběr top-PRIO položek.

---

## Příklad vyplněného sprint plánu

```markdown
---
title: "Sprint 2 Plan"
version: "1.0"
sprint_number: 2
start_date: "2026-03-10"
end_date: "2026-03-14"
goal: "Secure the API with input validation and rate limiting; improve test coverage above 70% for core modules."
max_tasks: 8
---

## Sprint Targets

| Priority | ID | Type | Title | Status | Effort | Confidence |
|----------|----|----|-------|--------|--------|-----------|
| 1 | T-101 | Task | Add Pydantic validation to /capture endpoint | READY | S (7h) | High |
| 2 | T-102 | Task | Implement rate limiting middleware | READY | S (8h) | High |
| 3 | T-103 | Task | Add integration tests for /capture flow | READY | M (14h) | Medium |
| 4 | T-104 | Bug | Fix async embedder NotImplementedError stub | READY | XS (3h) | High |
| 5 | T-105 | Chore | Update API docs with /capture and /recall examples | DESIGN | M (12h) | Medium |
| 6 | T-106 | Task | Add coverage reporting to CI pipeline | READY | S (6h) | High |

## Sprint Goal Justification

T-101 + T-102 (security), T-103 (test coverage), T-104 (removes blocker for semantic embeddings spike) are critical for next phase. T-105/T-106 improve operational excellence.

## Dependency Graph

| Task ID | Depends On | Blocks | Critical Path |
|---------|-----------|--------|---------------|
| T-101 | None | T-103 | YES (security gate) |
| T-102 | None | T-103 | YES (security gate) |
| T-103 | T-101, T-102 | None | YES (test gate) |
| T-104 | None | T-107 (future spike) | NO |
| T-105 | None | None | NO |
| T-106 | None | None | NO |

**Critical Path Length:** T-101 → T-103 = 2 tasks (fits in 5-day sprint comfortably).

## Risk Assessment

| Task | Risk Level | Mitigation |
|------|-----------|-----------|
| T-101 | LOW | Pydantic is standard pattern, well-documented |
| T-102 | MEDIUM | Async middleware complexity; pair program with Alice |
| T-103 | MEDIUM | May uncover existing bugs; run tests in isolation first |
| T-104 | LOW | Stub removal is straightforward |
| T-105 | LOW | Documentation only; no runtime risk |
| T-106 | LOW | CI change, isolated scope |

**Action:** No HIGH-risk items; sprint is well-balanced.

## Capacity Planning

| Dev | Availability | Max Hours | Assigned | Headroom | Utilization |
|-----|--------------|-----------|----------|----------|------------|
| Alice | 100% | 30h | 29h (T-101, T-102, T-103 lead) | 1h | 97% |
| Bob | 80% (Fri off) | 24h | 22h (T-103, T-104, T-106) | 2h | 92% |
| **TOTAL** | - | 54h | 51h | 3h | 94% |

**Utilization Target:** 80-90%. Result: 94% (slightly high but acceptable for sprint with clear scope).

## Rollover from Sprint 1

| Task | Sprint 1 Est. | Sprint 1 Actual | Reason | Status in Sprint 2 |
|------|-------------|----------------|--------|------------------|
| T-051 | S (7h) | 11h | Underestimated; spec change mid-sprint | Moved to Sprint 3 (DESIGN) |
| T-062 | BLOCKED | BLOCKED | Waiting on external firm security audit | Carrying over; lowest priority |

**Lessons:** Estimation method needs refinement; pair estimation sessions recommended for next sprint.

## Definition of Done

Sprint 2 is DONE when:

### Code Quality
- [ ] All tests PASS: `pytest -q` exit 0 on main after all merges
- [ ] Linting PASS: `ruff check src tests` exit 0
- [ ] Coverage ≥ 70% for modified modules (test_capture.py, test_rate_limit.py, test_triage.py)
- [ ] No stubs in DONE tasks (T-101 through T-104 fully implemented)

### Review & Design
- [ ] All PRs have CLEAN verdict from fabric-review
- [ ] Design decisions documented in decisions/ (if applicable)
- [ ] All PR comments resolved

### Documentation
- [ ] /capture and /recall endpoints documented with curl examples
- [ ] CHANGELOG updated with T-101, T-102 changes
- [ ] README updated if behavior changes (rate limit config)

### Operational
- [ ] All target items marked DONE in backlog/
- [ ] No P0 bugs introduced (verified via integration tests)
- [ ] Rate limiting works under load (stress test: 1000 req/min)

### Security Gate (Sprint-Specific)
- [ ] T-101: Pydantic validation guards all user inputs
- [ ] T-102: Rate limiter enforces 100 req/min per client
- [ ] No hardcoded secrets in code/docs/tests

## Task Queue

| Order | ID | Type | Status | Estimate | Description |
|-------|----|------|--------|----------|-------------|
| 1 | T-101 | Task | READY | S (7h) | Add Pydantic validation to /capture endpoint |
| 2 | T-102 | Task | READY | S (8h) | Implement rate limiting middleware |
| 3 | T-103 | Task | DESIGN | M (14h) | Add integration tests for /capture flow |
| 4 | T-104 | Bug | READY | XS (3h) | Fix async embedder NotImplementedError stub |
| 5 | T-105 | Chore | DESIGN | M (12h) | Update API docs with examples |
| 6 | T-106 | Task | READY | S (6h) | Add coverage reporting to CI pipeline |
```

---

## Postup

### 1) Načti konfiguraci

- Z `{WORK_ROOT}/config.md` si přečti:
  - `SPRINT.max_days`
  - `SPRINT.max_tasks`
  - `SPRINT.wip_limit`
  - definici statusů backlogu
  - `GIT.main_branch` (jen informativně)

Pokud `SPRINT` nebo `COMMANDS` blok chybí → vytvoř intake item `intake/config-missing-sprint-or-commands.md` a pokračuj s defaulty:
- `max_days=5`, `max_tasks=10`, `wip_limit=1`

### 2) Načti state a zjisti sprint N

- Přečti `{WORK_ROOT}/state.md` → `sprint = N`
- Pokud N chybí → N=1 (a zapiš do reportu jako WARNING; neměň state, to řeší loop/init)

**Sprint counter enforcement (P2 fix):**
```bash
# Sprint counter enforcement — validate active_sprint is numeric
CURRENT_SPRINT=$(grep 'active_sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$CURRENT_SPRINT" | grep -qE '^[0-9]+$'; then
  echo "WARN: active_sprint is not a valid integer: $CURRENT_SPRINT"
  CURRENT_SPRINT=1
fi
```
This ensures the sprint counter is always a valid positive integer, preventing silent failures downstream.

### 3) Načti backlog kandidáty

Z `{WORK_ROOT}/backlog.md` vezmi tabulku a vyfiltruj:
- status NOT IN: `DONE`
- preferuj: `READY` a `DESIGN`
- `BLOCKED` může být vybrán jen pokud jde o „blocker task“ pro top priority chain (jinak ne)

Pokud backlog.md neexistuje:
- fallback: načti `{WORK_ROOT}/backlog/*.md` a seřaď podle `prio:` ve frontmatter.

### 4) Effort Estimation Algorithm

Před výběrem Sprint Targets, vypočítej effort pro každý kandidát. Použij ALGORITMICKÉ odhady, ne heuristiku:

**EFFORT ESTIMATION ALGORITHM:**

Spočítej pro každý candidate:
- FILES_MODIFIED = počet .py souborů k úpravě
- TESTS_ADDED = počet nových test funkcí
- COMPLEXITY = cykličita komplexita (max Cyclo v dotčených funkcích)

Mapuj na effort:

```
if FILES ≤ 2 AND TESTS ≤ 3 AND COMPLEXITY ≤ 5:
  effort = "XS" (< 4 hours)
else if FILES ≤ 4 AND TESTS ≤ 6 AND COMPLEXITY ≤ 8:
  effort = "S" (4-8 hours)
else if FILES ≤ 8 AND TESTS ≤ 12 AND COMPLEXITY ≤ 12:
  effort = "M" (8-16 hours)
else if FILES ≤ 15 AND TESTS ≤ 20 AND COMPLEXITY ≤ 18:
  effort = "L" (16-32 hours)
else:
  effort = "XL" (> 32 hours) — MUST SPLIT into 2+ tasks
```

**Example:**
- Task: Add rate limiting to /capture endpoint
  - FILES: 2 (api/routes/capture.py + middleware/rate_limit.py)
  - TESTS: 3 (test_rate_limit.py)
  - COMPLEXITY: 5 (simple conditional + counter)
  - Effort: XS → estimate 4-6 hours

### 4.1) Vyber Sprint Targets (co chceme posunout)

Vyber top kandidáty podle PRIO (sestupně) s těmito pravidly:

1. **Základ:** vyber až `SPRINT.max_tasks` položek (nebo méně), ale drž sprint fokus:
   - max 1–2 epics/stories (strategické cíle)
   - zbytek tasks/bugs/chores (exekuční práce)
2. Pokud je top item `Epic` nebo `Story`, může být v `Sprint Targets`,
   ale implementace musí proběhnout přes tasks (doplní analyze).
3. Každý vybraný target musí mít:
   - `title`, `type`, `tier`, `status`, `effort`, `prio` (frontmatter)
   - aspoň 1–3 AC checkboxy v těle (jinak označ jako DESIGN a počítej s analýzou)
   - Effort calculated using EFFORT ESTIMATION ALGORITHM above

**Sprint size limit (P2 work quality):**
- Maximum tasks per sprint: 12 (hard cap)
- Doporučený rozsah: 5-8 tasks (sweet spot)
- Pokud target decomposition > 12 tasks → rozděl na 2 sprinty
- Effort distribution: max 40% L tasks, zbytek S/M

**Sprint goal** napiš jako 1 větu, která shrnuje společný outcome všech targetů.

### 4.3) Dependency Graph & Ordering

Przed vytvořením sprint plánu, sestav dependency graph:

```
For each target in Sprint Targets:
  - Identified dependencies (tasks that must finish first)
  - Identifies blocked items (tasks waiting for this target)
  - Compute topological sort to find safe execution order

Template:
| Task ID | Title | Depends On | Blocks | Critical Path |
|---------|-------|-----------|--------|--------------|
| T-001 | Add rate limiting | None | T-003, T-004 | YES (blocks security goals) |
| T-002 | Update docs | T-001 | None | NO |
| T-003 | Integration tests | T-001 | None | YES (test gate) |

Topological Order:
1. T-001 (no deps)
2. T-003, T-002 (both depend on T-001)

Critical Path = longest chain of dependencies
If Critical Path > sprint duration → warn and rebalance
```

### 4.4) Risk Assessment per Sprint

Proveď RISK ASSESSMENT pro každý target:

| Task | Risk Level | Risk Description | Mitigation |
|------|-----------|------------------|-----------|
| T-001: New API endpoint | HIGH | Unfamiliar API design, might need refactor | Spike first (4h), write contract test, design review |
| T-002: Rate limiting | MEDIUM | Complexity with async/awaits | Reference existing code, pair program |
| T-003: Bug fix | LOW | Isolated fix, well-tested | Standard approach |
| T-004: Docs | LOW | No runtime impact | Can slip if time-constrained |

**Risk Levels:**
- `HIGH` — New technology, unfamiliar pattern, or complex integration
- `MEDIUM` — Moderate complexity, some unknowns
- `LOW` — Well-known pattern, isolated change

**Mitigations:**
- Spike first (reduce unknowns)
- Pair program (knowledge sharing)
- Contract test (validate interface early)
- Code review (reduce bugs)

Pokud máš >2 HIGH-risk items v sprintu → zvýší buď WIP limit nebo sníží počet tasks.

### 4.5b) Anti-Pattern Detection & Hidden Risks

**Detection Heuristics (POVINNÉ):**

```bash
echo "=== DETECTING HIDDEN SPRINT RISKS ==="

# Anti-pattern 1: All tasks in same module
echo "Checking module concentration..."
MODULES=$(grep "^| " "$SPRINT_TARGETS_TABLE" | awk '{print $4}' | grep -oP '^[^/]+' | sort | uniq -c)
SINGLE_MODULE_TASKS=$(echo "$MODULES" | awk '$1 > 3 {count++} END {print count}')
if [ "$SINGLE_MODULE_TASKS" -gt 0 ]; then
  echo "WARN: >3 tasks in single module (high context switching risk)"
fi

# Anti-pattern 2: Single developer concentration
echo "Checking developer concentration..."
MAX_ASSIGNED=$(grep "Assigned" "$CAPACITY_TABLE" | awk '{print $4}' | sort -rn | head -1)
if [ "$(echo "$MAX_ASSIGNED" | awk '$1 > 35 {print 1}')" = "1" ]; then
  echo "WARN: One developer has >35h assigned (>115% capacity)"
fi

# Anti-pattern 3: Critical path too long
echo "Checking critical path..."
CRITICAL_PATH_LENGTH=$(grep "YES" "$DEPENDENCY_TABLE" | wc -l)
if [ "$CRITICAL_PATH_LENGTH" -gt 3 ]; then
  echo "WARN: Critical path has >3 tasks (likely to slip if blocker hits)"
fi

# Anti-pattern 4: Too many tasks in DESIGN status
echo "Checking design status..."
DESIGN_COUNT=$(grep "DESIGN" "$SPRINT_TARGETS_TABLE" | wc -l)
READY_COUNT=$(grep "READY" "$SPRINT_TARGETS_TABLE" | wc -l)
if [ "$DESIGN_COUNT" -gt "$READY_COUNT" ]; then
  echo "WARN: More DESIGN tasks (${DESIGN_COUNT}) than READY (${READY_COUNT}) — may slip"
fi

# Anti-pattern 5: XL tasks (>32 hours) in sprint
echo "Checking for XL tasks..."
XL_COUNT=$(grep "XL" "$SPRINT_TARGETS_TABLE" | wc -l)
if [ "$XL_COUNT" -gt 0 ]; then
  echo "FAIL: Sprint has XL tasks (>32h); must split into L+M"
  exit 1
fi
```

### 4.5c) Pre-Sprint Gate (BLOCKING Validation)

**CRITICAL:** Perform these checks BEFORE finalizing sprint. Any FAIL blocks sprint start.

```bash
echo "=== PRE-SPRINT VALIDATION GATE ==="

# Gate 1: Capacity check
TOTAL_EFFORT=$(grep "^| " "$SPRINT_TARGETS_TABLE" | awk '{print $5}' | grep -oP '\d+' | awk '{sum+=$1} END {print sum}')
TOTAL_CAPACITY=$((SPRINT_DAYS * 6 * DEVELOPER_COUNT))
UTILIZATION=$((TOTAL_EFFORT * 100 / TOTAL_CAPACITY))
if [ "$UTILIZATION" -gt 90 ]; then
  echo "FAIL: Sprint utilization is ${UTILIZATION}% (>90%). Remove items or reduce scope."
  exit 1
fi
echo "PASS: Capacity check (${UTILIZATION}% utilization, threshold 90%)"

# Gate 2: No circular dependencies
echo "Checking for dependency cycles..."
# Topological sort; if fails, cycles exist
if ! topological_sort "$DEPENDENCY_TABLE" >/dev/null 2>&1; then
  echo "FAIL: Sprint has circular dependencies. Resolve before starting."
  exit 1
fi
echo "PASS: Dependency check (no cycles)"

# Gate 3: All tasks have effort estimates
echo "Checking effort estimates..."
MISSING_EFFORT=$(grep "^| " "$SPRINT_TARGETS_TABLE" | grep -v "XS\|S\|M\|L\|XL" | wc -l)
if [ "$MISSING_EFFORT" -gt 0 ]; then
  echo "FAIL: ${MISSING_EFFORT} tasks missing effort estimates. Require before sprint start."
  exit 1
fi
echo "PASS: All tasks have effort estimates"

# Gate 4: Definition of Done is complete
echo "Checking Definition of Done..."
DOD_CHECKBOXES=$(grep "^- \[" "$SPRINT_PLAN" | wc -l)
if [ "$DOD_CHECKBOXES" -lt 5 ]; then
  echo "FAIL: Definition of Done has <5 checkboxes (insufficient). Requires minimum 5."
  exit 1
fi
echo "PASS: Definition of Done is complete (${DOD_CHECKBOXES} checkboxes)"

echo "=== PRE-SPRINT GATE PASSED ==="
exit 0
```

### 4.2) Definition of Done (POVINNÉ) — CHECKLISTABLE FORMAT

Každý sprint MUSÍ mít explicitní DoD v sprint plánu. DoD MUSÍ být konkrétní checklist, ne proza:

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
```

**Specifické cíle sprintu:** Pokud sprint má specifické cíle (např. "zero P0 bugs", "API v2 ready", "semantic embeddings proof-of-concept"), přidej je jako additional checkboxes do DoD.

**Anti-pattern:** ❌ Sprint bez DoD nebo s prózou (nikdo neví kdy je "hotovo" — vede k scope creep nebo předčasnému uzavření)

**Jak ověřit DoD:**
- Každý checkbox MUSÍ být ověřitelný (ne subjektivní)
- DONE = všechny checkboxy checked
- In-Review = >80% checkboxů checked
- In-Progress = <80% checkboxů checked

### 4.5) Capacity Planning

Před finálním výběrem Sprint Targets, ověř kapacitu sprintu:

```
SPRINT_CAPACITY = SPRINT.max_days × 6 hours/day
                = e.g., 5 days × 6 h = 30 person-hours per dev

TOTAL_EFFORT = sum(task.effort_hours for task in Sprint Targets)
               e.g., XS=5h, S=7h, M=12h, M=12h = 36 hours

if TOTAL_EFFORT > SPRINT_CAPACITY:
  OVERLOAD_FACTOR = TOTAL_EFFORT / SPRINT_CAPACITY
  if OVERLOAD_FACTOR > 1.2:
    WARN: "Sprint overloaded by {OVERLOAD_FACTOR}x. Remove items or reduce scope."
```

**Capacity Planning Table:**

| Dev | Availability | Max Hours | Assigned Effort | Headroom |
|-----|--------------|-----------|-----------------|----------|
| Alice | 100% | 30h | 28h | 2h (67%) |
| Bob | 80% (PTO Wed) | 24h | 22h | 2h (92%) |
| **TOTAL** | - | 54h | 50h | 4h (93% utilization) |

Cíl: 80-90% utilization (zbytečný headroom pro emergency bugs).

### 4.6) Rollover Tracking (z předchozího sprintu)

Vezmi items z PREVIOUS sprint, které nejsou DONE:

| Sprint | Task ID | Title | Original Est. | Actual Effort | Reason for Carry-Over |
|--------|---------|-------|--------------|----------------|----------------------|
| Sprint N-1 | T-042 | Add semantic embeddings | S (7h) | 12h (actual) | Underestimated; waiting on backend spike |
| Sprint N-1 | T-051 | API docs | XS (5h) | BLOCKED | Blocked by T-042 design decision |
| Sprint N-1 | T-058 | Security audit | DESIGN | DESIGN | Waiting for external firm; moved to Sprint N+2 |

**Rollover Analysis:**
- Co se neufinancovalo a proč? (underestimate, blocked, spec change)
- Jaké improvements do estimation na příští sprint?
- Měl by být task rozdělen? (XL → L + M)

Zapiš na start Sprint N sprintu jako WARNING, aby se opakovaly chyby.

### 5) Vytvoř sprint plán (podle šablony)

Vytvoř soubor:
- `{WORK_ROOT}/sprints/sprint-{N}.md`

Použij `{WORK_ROOT}/templates/sprint-plan.md` a vyplň:
- sprint title (krátké)
- goal (z kroku 4)
- start = dnešek, end = start + `SPRINT.max_days` (kalendářní)
- `Sprint Targets` tabulku

`Task Queue`:
- pokud už máš konkrétní tasks typu `Task/Bug/Chore/Spike` ve statusu `READY`, můžeš předvyplnit 1–3 nejvyšší.
- jinak nech „Task Queue” s placeholderem (doplní `fabric-analyze`).

**Task Queue formát (P2 work quality):**
```markdown
| Order | ID | Type | Status | Estimate | Description |
|-------|----|------|--------|----------|-------------|
| 1 | task-xxx | Task | READY | S | Popis |
```
Povinné sloupce: Order, ID, Type, Status, Estimate. Description je volitelný.
Status: DESIGN | READY | IN_PROGRESS | IN_REVIEW | DONE | CARRY-OVER

### 6) Update state sprint metadata (povolené)

V `{WORK_ROOT}/state.md` nastav pouze:
- `sprint_started: <YYYY-MM-DD>`
- `sprint_ends: <YYYY-MM-DD>`
- `sprint_goal: "<goal>"`

Nesahej na `phase` ani `step`.

### 6.5) End-to-End Target Selection & Capacity Bash

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
  # Map effort to hours
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

### 7) Vytvoř sprint report

V `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` uveď:
- seznam targetů + proč (PRIO, vize)
- rizika (dependencies, blocked)
- jaký typ práce to je (feature vs debt vs security)
- co analyzovat jako první (dependency ordering hint)

## Downstream Contract

**fabric-analyze** (next skill) reads sprint plan fields:
- `sprint_number` (int) — active sprint identifier
- `start_date`, `end_date` (ISO date strings)
- `sprint_targets[]` — table with columns:
  - `id` (string, e.g. "T-101") — unique task identifier
  - `type` (enum) — Task | Bug | Chore | Epic | Story | Spike
  - `status` (enum) — DESIGN | READY | IN_PROGRESS | IN_REVIEW | DONE
  - `effort` (enum) — XS | S | M | L | XL (mapped to hours as above)
  - `title` (string) — task description
- `definition_of_done[]` — checklist of sprint exit criteria
- `task_queue[]` — ordered list of tasks to execute (Order, ID, Type, Status, Estimate)
- `capacity_plan` — table with developer availability and hours assigned

---

## Self-check (fail conditions)

- sprint plán byl vytvořen a má sekce `Sprint Targets` + `Task Queue`
- každý target ID odpovídá existujícímu `{WORK_ROOT}/backlog/{id}.md`
- state metadata byla nastavena (3 pole)

Pokud něco z toho neplatí → reportuj jako CRITICAL a vytvoř intake item `intake/sprint-plan-invalid.md`.

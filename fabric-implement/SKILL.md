---
name: fabric-implement
description: "Implement exactly one task (WIP=1) from the sprint Task Queue using VERIFY-FIRST workflow: read config+analysis, inspect code, create feature branch, implement minimal change + tests, run quality gates, and update backlog item status. Single-piece flow enforcement."
---
<!-- built from: builder-template -->

# IMPLEMENT — Kód + testy (WIP=1, VERIFY-FIRST)

## §1 Účel

Implementovat **jednu** backlog položku (Task/Bug/Chore/Spike) podle `Task Queue` ve sprint plánu (WIP=1).

**Princip:**
- **VERIFY-FIRST**: nejdřív čti, ověř, reprodukuj; až pak piš kód
- **Small batch**: malý diff, rychlé iterace
- **Evidence-driven**: testy + lint + format check musí projít

---

## §2 Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

```bash
python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" \
  --skill "fabric-implement" --event start

# Po úspěšném konci:
python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" \
  --skill "fabric-implement" --event end --status OK \
  --report "{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md"

# Pokud skončíš STOP nebo narazíš na CRITICAL:
python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" \
  --skill "fabric-implement" --event error --status ERROR \
  --message "short description (1 věta)"
```

---

## §3 Preconditions (fail fast)

1. `{CODE_ROOT}/` musí existovat
2. Backlog item soubor existuje: `{WORK_ROOT}/backlog/{TASK_ID}.md`
3. Config fields vyplněny:
   - `COMMANDS.test` (**povinné**; nesmí být `TBD` ani `""`)
   - `COMMANDS.lint` (volitelné; `""` = vypnuto)
   - `COMMANDS.format_check` (volitelné; `""` = vypnuto)

**Fail-fast bash checks:**
```bash
# K1: Phase validation — implement runs in implementation phase
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "implementation" ]; then
  echo "STOP: fabric-implement requires phase=implementation, current=$CURRENT_PHASE"
  exit 1
fi

# Precondition: backlog file exists
if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  echo "STOP: backlog file not found"
  exit 1
fi

# Precondition: test command configured
TEST_CMD=$(grep 'test:' "{WORK_ROOT}/config.md" | awk '{print $2}')
if [ -z "$TEST_CMD" ] || [ "$TEST_CMD" = "TBD" ]; then
  echo "STOP: COMMANDS.test is not configured"
  exit 1
fi

# K4: Git safety — verify clean working tree before branch creation
if [ -n "$(git -C "{CODE_ROOT}" status --porcelain 2>/dev/null)" ]; then
  echo "STOP: git working tree not clean — commit or stash changes first"
  exit 1
fi

# K7: Path traversal guard
validate_path() {
  if echo "$1" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected"
    exit 1
  fi
}
validate_path "$TASK_FILE"
```

---

## §4 Vstupy

Povinné:
- `{WORK_ROOT}/config.md` (COMMANDS + cesty + git)
- `{WORK_ROOT}/state.md` (wip_item/wip_branch + sprint N)
- `{WORK_ROOT}/sprints/sprint-{N}.md` (sekce `## Task Queue`)
- `{WORK_ROOT}/backlog/{id}.md`
- `{ANALYSES_ROOT}/{id}-analysis.md` (pokud existuje; preferované)
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`

Volitelné:
- předchozí `reports/review-*.md` (pokud jde o rework)

---

## §5 Výstupy

**Output schema:** `fabric.report.v1` s `version: "1.0"` fieldem.

Deliverables:
- git branch s commit(y)
- aktualizovaný backlog item `{WORK_ROOT}/backlog/{id}.md` (status: IN_REVIEW, branch, updated)
- updated `{WORK_ROOT}/state.md` (wip_item, wip_branch)
- `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md`

**Report template:**
```yaml
---
schema: fabric.report.v1
kind: implement
step: "implement"
version: "1.0"
task_id: "{wip_item}"
branch: "{branch_name}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
commit_hash: "{sha}"
test_result: "PASS"
coverage_pct: {percentage}
---

# Summary
# Changes
# Evidence (Tests, Lint, Coverage)
# Risks & Follow-ups
```

---

## §6 FAST PATH (doporučeno)

### State operations (bez ruční editace YAML)

```bash
# Přečti state
python skills/fabric-init/tools/fabric.py state-read

# Nastav WIP jakmile vybereš task + branch
python skills/fabric-init/tools/fabric.py state-patch \
  --fields-json '{"wip_item":"<id>","wip_branch":"<branch>"}'
```

### Objektivní gates (log capture)

```bash
python skills/fabric-init/tools/fabric.py run test --tail 200
python skills/fabric-init/tools/fabric.py run lint --tail 200
python skills/fabric-init/tools/fabric.py run format_check --tail 200
```

### Backlog metadata (plan/apply)

```yaml
schema: fabric.plan.v1
ops:
  - op: backlog.set
    id: "{wip_item}"
    fields:
      status: "IN_PROGRESS"
      branch: "{branch}"
      updated: "{YYYY-MM-DD}"
  - op: backlog.index
```

Apply:
```bash
python skills/fabric-init/tools/fabric.py apply \
  "{WORK_ROOT}/reports/implement-plan-{wip_item}-{YYYY-MM-DD}.yaml"
```

---

## §7 Postup (overview)

Detailní implementační kroky, coding patterns, anti-patterns a komplexní validační logika:

> Detaily viz `references/workflow.md` | Příklady viz `references/examples.md`

Stručný postup:

1. **State Validation** — ověř phase compatibility
2. **Path Traversal Guard** — validate all dynamic paths
3. **Select Task** (WIP=1) — z Task Queue
4. **Prepare Branch** — create nebo reuse (s Unicode normalizací)
5. **VERIFY-FIRST** — read analysis, check baseline tests, governance compliance
6. **Implement** — malá změna + povinné testy (happy/edge/error)
7. **Quality Gates** — test/lint/format_check (s auto-fix decision tree)
8. **Commit** — feat({id}): ... (conventional format)
9. **Self-review** — security + reliability scan
10. **Update State** — wip_item/wip_branch do state.md
11. **Update Backlog** — status=IN_REVIEW, branch, updated
12. **Generate Report** — evidence template s výsledky

> Stress test hledání: **Blocked dependencies detection**, **Spec/ADR drift detection**, **Separace pre-existing fixů**, **Regression detection post auto-fix**, **Code complexity validation**, **Coverage enforcement**.

---

## K10 — Concrete Example & Anti-patterns

### Example: Task b015 — Add Recall Scoring Tests (LLMem)

```
Input: fabric-implement selected task-b015 from sprint-3 Task Queue
  backlog/{WORK_ROOT}/backlog/b015.md: type=Task, effort=M, status=READY
  analysis: {WORK_ROOT}/analyses/b015-analysis.md exists (recall/scoring.py)
Analysis: recall/scoring.py has 3 scoring functions (tier_boost, scope_boost, recency_boost)
Test baseline: 2 existing tests, coverage 45% (need ≥60%)

VERIFY-FIRST:
  - Check current coverage: pytest --cov=llmem.recall.scoring --cov-report=term-missing
  - Coverage is 45%: test_tier_boost_basic, test_tier_boost_edge missing
  - Check existing tests for isolation: verified, no shared state

IMPLEMENT (4 new test functions):
  1. test_combine_score_happy: tier=T0, scope=global, fresh → score ≥90
  2. test_combine_score_old_memory: recency decay factor applied → score lower
  3. test_combine_score_minimal: default inputs → score normalizes to [0,100]
  4. test_combine_score_edge_stale_only: only pre-existing results → SKIPPED

Implementation: 45 LOC added (lines 127–172 in test_scoring.py)
All 4 tests PASS, coverage rises to 92%, no regressions

QUALITY GATES:
  - pytest: PASS (49 passed, 0 failed)
  - lint: PASS (ruff check clean)
  - format: PASS (ruff format idempotent)

REPORT:
  Branch: feat/task-b015-recall-scoring-tests
  Commit: feat(b015): add combine_score integration tests, coverage 45%→92%
  Status: IN_REVIEW
```

### Anti-patterns (FORBIDDEN detection & prevention)

```bash
# A1: Implement WITHOUT running baseline tests first
# DETECTION: Skip step 5 (VERIFY-FIRST)
# FIX: Run `pytest --co -q` to baseline before writing code
if ! pytest --co -q >/dev/null 2>&1; then
  echo "STOP: baseline test discovery failed — run triage first"
  exit 1
fi

# A2: Test coverage claim without evidence
# DETECTION: report says "coverage improved" but pytest --cov not run
# FIX: Require `pytest --cov --cov-report=json` in quality gate
if [ ! -f ".coverage" ]; then
  echo "FAIL: pytest --cov not executed — coverage report missing"
  exit 1
fi

# A3: Commit with @pytest.mark.skip tests
# DETECTION: grep -c '@pytest.mark.skip' test_file.py > 0 AND verdict=PASS
# FIX: Count skipped tests, report them as WARN not PASS
SKIPPED=$(pytest --collect-only -q 2>/dev/null | grep -c skipped || echo 0)
if [ "$SKIPPED" -gt 0 ]; then
  echo "WARN: $SKIPPED tests marked skip — hiding failures?"
  exit 1  # FAIL if skipped tests present post-implement
fi
```

### Minimum acceptance kritéria
- Implement report MUSÍ obsahovat: baseline test count, post-implement test count, delta
- Každý nový soubor musí mít alespoň 1 test (coverage evidence z pytest --cov)
- Backlog item musí být aktualizován na status IN_REVIEW s implement_report evidence

---

## §8 Quality Gates (enforcement)

**BLOCKING GATES** (MUST PASS):

```bash
# K5: Timeout bounds from config (defaults match config.md timeout_bounds)
TIMEOUT_TEST=$(awk '/timeout_bounds:/,/^[^ ]/{if(/  test:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_TEST=${TIMEOUT_TEST:-300}
TIMEOUT_LINT=$(awk '/timeout_bounds:/,/^[^ ]/{if(/lint:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_LINT=${TIMEOUT_LINT:-120}
TIMEOUT_FMT=$(awk '/timeout_bounds:/,/^[^ ]/{if(/format_check:/)print $2}' "{WORK_ROOT}/config.md"); TIMEOUT_FMT=${TIMEOUT_FMT:-120}

# 1. Tests (POVINNÉ)
timeout "$TIMEOUT_TEST" {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -ne 0 ]; then echo "FAIL: tests"; exit 1; fi

# 2. Coverage ≥60% pro CORE moduly (services/, api/, recall/, triage/)
pytest --cov="module_name" --cov-fail-under=60 -q
if [ $? -ne 0 ]; then echo "FAIL: coverage <60%"; exit 1; fi

# 3. Lint (volitelné, ale pokud je zapnuté)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout "$TIMEOUT_LINT" {COMMANDS.lint}
  if [ $? -ne 0 ]; then echo "FAIL: lint"; exit 1; fi
fi

# 4. Format check (volitelné)
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout "$TIMEOUT_FMT" {COMMANDS.format_check}
  if [ $? -ne 0 ]; then echo "FAIL: format"; exit 1; fi
fi
```

**Auto-fix decision tree (pokud lint failne):**
- ≤5 errors: auto-fix all, re-run
- 6-20 errors: auto-fix + regression check (>30% regression = revert)
- >20 errors: DON'T auto-fix, manual fix required

```bash
# K2: Regression detection post auto-fix (POVINNÉ)
# Capture baseline test count BEFORE auto-fix
BASELINE_PASS=$(timeout "$TIMEOUT_TEST" {COMMANDS.test} 2>&1 | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
BASELINE_PASS=${BASELINE_PASS:-0}
if ! echo "$BASELINE_PASS" | grep -qE '^[0-9]+$'; then BASELINE_PASS=0; fi

# Run auto-fix (lint --fix, format)
{COMMANDS.lint_fix} 2>/dev/null || echo "WARN: lint fix failed"

# Capture post-fix test count
POSTFIX_PASS=$(timeout "$TIMEOUT_TEST" {COMMANDS.test} 2>&1 | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
POSTFIX_PASS=${POSTFIX_PASS:-0}
if ! echo "$POSTFIX_PASS" | grep -qE '^[0-9]+$'; then POSTFIX_PASS=0; fi

# Regression check: >30% test regression = revert auto-fix
if [ "$BASELINE_PASS" -gt 0 ]; then
  REGRESSION_PCT=$(( (BASELINE_PASS - POSTFIX_PASS) * 100 / BASELINE_PASS ))
  if [ "$REGRESSION_PCT" -gt 30 ]; then
    echo "WARN: Regression detected ($REGRESSION_PCT% tests lost). Reverting auto-fix."
    git checkout -- . 2>/dev/null || echo "WARN: git checkout revert failed"
  fi
fi
```

---

## §9 Report Template

Vzor pro `implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md`:

```markdown
# {Task ID} Implementation Report

## Summary
[1–3 odrážky: co bylo dodáno]

## Changes
### Modified Files
[seznam top 10]

**Diff stats:**
[git diff --stat]

### Evidence
**Tests (PASS):** [výstup pytest -v]
**Coverage (PASS):** [coverage %]
**Lint (PASS):** [lint result]
**Commit:** [commit message]

## Risks & Follow-ups
[co zůstalo otevřené]

## Status
Task status: **IN_REVIEW**
```

---

## §10 Self-check

**Existence checks:**
- [ ] Report existuje s validní YAML frontmatter (schema: fabric.report.v1)
- [ ] Branch `{wip_branch}` existuje a obsahuje commit(y)
- [ ] Backlog item status = IN_REVIEW
- [ ] state.md aktualizován (wip_item, wip_branch)

**Quality checks (BLOCKING):**
- [ ] Tests PASS (exit code 0)
- [ ] Coverage ≥60% pro CORE moduly
- [ ] Žádné stubs/pass/TODO v production kódu
- [ ] Working tree CLEAN (git status --porcelain prázdný)
- [ ] Baseline tests nezhoršeny (no new regressions)

**Invariants:**
- [ ] Jen soubory v `{CODE_ROOT}/` modifikovány (exception: backlog + report)
- [ ] Commit message: `feat/fix({task_id}): {popis}`

Pokud self-check FAIL → EXIT 1 + intake item

---

## §11 Failure Handling

**Blocker error (CRITICAL) → create intake + STOP:**

```bash
# Branch not found
if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "implement" --slug "missing-backlog-file" \
    --title "Backlog file not found: ${TASK_ID}.md"
  exit 1
fi

# Tests timeout (config: timeout_bounds.test)
timeout "${TIMEOUT_TEST:-300}" {COMMANDS.test}
if [ $? -eq 124 ]; then
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "implement" --slug "implement-timeout-${TASK_ID}" \
    --title "Tests exceeded ${TIMEOUT_TEST:-300}s timeout"
  exit 1
fi

# Coverage <60% for CORE module
if [ "$CORE_MODULE_FAILED" -gt 0 ]; then
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "implement" --slug "coverage-fail-${TASK_ID}" \
    --title "Coverage <60% for CORE module (MUST FIX BEFORE COMMIT)"
  exit 1
fi
```

**Blocked dependencies (WARN but no auto-proceed):**
```bash
DEPENDS=$(grep 'depends_on:' "{WORK_ROOT}/backlog/${id}.md" | sed 's/depends_on://')
for DEP in $DEPENDS; do
  DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" | awk '{print $2}')
  if [ "$DEP_STATUS" != "DONE" ]; then
    echo "BLOCKED: dependency $DEP not DONE (status=$DEP_STATUS)"
    exit 1
  fi
done
```

---

## §12 — Metadata (pro fabric-loop orchestraci)

**Downstream Contract (WQ7):** fabric-review (Status=IN_REVIEW, tests+lint PASS), fabric-close (branch exists, conventional commit, no stubs).

> **Cross-sprint lookup:** fabric-implement depends_on fabric-close (closing phase) to read previous sprint's completion context and rollback/versioning records. This is a read-only lookup across sprint boundaries.

```yaml
depends_on: [fabric-analyze, fabric-architect, fabric-close, fabric-design]
feeds_into: [fabric-test, fabric-e2e]
phase: implementation
lifecycle_step: implement
touches_state: true
touches_git: true
estimated_ticks: 1-3
idempotent: false
fail_mode: fail-open
```

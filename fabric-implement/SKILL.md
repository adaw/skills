---
name: fabric-implement
description: "Implement exactly one task (WIP=1) from the sprint Task Queue. VERIFY-FIRST workflow: read config+analysis, inspect code, create/reuse feature branch, implement minimal change + tests, run COMMANDS (test/lint/format_check), commit, and update backlog item metadata (status/branch). Only updates state.md fields wip_item/wip_branch."
tags:
  - implementation
  - quality-gates
  - verify-first
  - wip=1
depends_on:
  - fabric-analyze
feeds_into:
  - fabric-review
  - fabric-close
schema: fabric.skill.v1
version: "1.0"
<!-- built from: builder-template -->
---

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

# Path traversal guard
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

> Detaily viz `references/workflow.md`

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

## §8 Quality Gates (enforcement)

**BLOCKING GATES** (MUST PASS):

```bash
# 1. Tests (POVINNÉ, timeout 300s)
timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -ne 0 ]; then echo "FAIL: tests"; exit 1; fi

# 2. Coverage ≥60% pro CORE moduly (services/, api/, recall/, triage/)
pytest --cov="module_name" --cov-fail-under=60 -q
if [ $? -ne 0 ]; then echo "FAIL: coverage <60%"; exit 1; fi

# 3. Lint (volitelné, ale pokud je zapnuté)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint}
  if [ $? -ne 0 ]; then echo "FAIL: lint"; exit 1; fi
fi

# 4. Format check (volitelné)
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check}
  if [ $? -ne 0 ]; then echo "FAIL: format"; exit 1; fi
fi
```

**Auto-fix decision tree (pokud lint failne):**
- ≤5 errors: auto-fix all, re-run
- 6-20 errors: auto-fix + regression check (>30% regression = revert)
- >20 errors: DON'T auto-fix, manual fix required

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

# Tests timeout (>300s)
timeout 300 {COMMANDS.test}
if [ $? -eq 124 ]; then
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "implement" --slug "implement-timeout-${TASK_ID}" \
    --title "Tests exceeded 300s timeout"
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
DEPENDS=$(grep 'depends_on:' {WORK_ROOT}/backlog/{id}.md | sed 's/depends_on://')
for DEP in $DEPENDS; do
  DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" | awk '{print $2}')
  if [ "$DEP_STATUS" != "DONE" ]; then
    echo "BLOCKED: dependency $DEP not DONE (status=$DEP_STATUS)"
    exit 1
  fi
done
```

---

## §12 Metadata

| Field | Value |
|-------|-------|
| **WIP Policy** | WIP=1 (never parallel) |
| **Timeout (tests)** | 300s |
| **Timeout (lint/fmt)** | 120s |
| **Coverage threshold** | ≥60% (CORE modules) |
| **Max function LOC** | ≤50 |
| **Max auto-fix counter** | 1× per task |
| **Phase** | implementation |
| **Downstream** | fabric-review, fabric-close |
| **Upstream** | fabric-analyze, Task Queue selection |

**Downstream Contract (WQ7):**
- fabric-review: Status=IN_REVIEW, all tests PASS, lint PASS
- fabric-close: Branch exists, commit msg conventional, no stubs
- backlog-index: Item updated with branch/status, timestamp current

**Errors breaking contract (CRITICAL):**
- ❌ Branch not created
- ❌ Status not IN_REVIEW
- ❌ Tests not PASS
- ❌ Stubs/pass/TODO in code

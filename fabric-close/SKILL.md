---
name: fabric-close
description: "Close the current sprint: merge approved task branches into main (squash), run quality gates on main, update backlog items to DONE with evidence (merge_commit), regenerate backlog index, and write a close report. Leaves carry-over items untouched and documents why."
tags: [fabric, sprint, merge, quality-gates, reporting]
depends_on: [fabric-review]
feeds_into: [fabric-archive, fabric-loop]
---
<!-- built from: builder-template -->

# §1 ÚČEL — Uzavření sprintu (merge + evidence)

Close the current sprint by:
- Squash-merge completed tasks into `main`
- Verify quality on `main` via quality gates (lint/format/tests)
- Update backlog items with `status: DONE` and `merge_commit` evidence
- Regenerate central backlog index
- Write sprint close report documenting merges and carry-overs

**Invariants:**
- Backlog index (`{WORK_ROOT}/backlog.md`) is source of truth
- No merge without review verdict = CLEAN
- All carry-over items must be documented with reason
- Close is fail-open: quality gate failures do not block close (logged as warnings)

---

# §2 PROTOKOL (povinné)

Log skill execution events to shared protocol log:

```bash
# START event
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-close" \
  --event start

# END event (on success)
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-close" \
  --event end \
  --status OK \
  --report "{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md"

# ERROR event (on critical failure)
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-close" \
  --event error \
  --status ERROR \
  --message "Brief one-sentence error description"
```

**Rule:** If you hit a CRITICAL error or STOP condition, log error before exiting.

---

# §3 PRECONDITIONS (bash)

Verify prerequisites before starting merge loop:

```bash
# Config validation
COMMANDS_TEST=$(grep '^COMMANDS.test:' "{WORK_ROOT}/config.md" | awk '{print $2}')
COMMANDS_LINT=$(grep '^COMMANDS.lint:' "{WORK_ROOT}/config.md" | awk '{print $2}')
COMMANDS_FORMAT=$(grep '^COMMANDS.format_check:' "{WORK_ROOT}/config.md" | awk '{print $2}')

if [ "$COMMANDS_TEST" = "TBD" ] || [ -z "$COMMANDS_TEST" ]; then
  echo "FAIL: COMMANDS.test not configured (TBD or empty)"
  exit 1
fi

# QUALITY.mode strict check
QUALITY_MODE=$(grep '^QUALITY.mode:' "{WORK_ROOT}/config.md" | awk '{print $2}')
if [ "$QUALITY_MODE" = "strict" ]; then
  if [ -z "$COMMANDS_LINT" ] || [ "$COMMANDS_LINT" = "TBD" ]; then
    echo "FAIL: strict mode requires COMMANDS.lint, but it is missing/TBD"
    exit 1
  fi
  if [ -z "$COMMANDS_FORMAT" ] || [ "$COMMANDS_FORMAT" = "TBD" ]; then
    echo "FAIL: strict mode requires COMMANDS.format_check, but it is missing/TBD"
    exit 1
  fi
fi

# Sprint plan existence
SPRINT_N=$(grep '^sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ ! -f "{WORK_ROOT}/sprints/sprint-${SPRINT_N}.md" ]; then
  echo "FAIL: sprint plan not found: sprints/sprint-${SPRINT_N}.md"
  exit 1
fi

# State validation (phase must be closing)
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "closing" ]; then
  echo "STOP: phase must be 'closing', current: $CURRENT_PHASE"
  exit 1
fi

# Reviews index governance (P2 fix #37)
if [ -f "{WORK_ROOT}/reviews/INDEX.md" ]; then
  REWORK_COUNT=$(grep -c "REWORK" "{WORK_ROOT}/reviews/INDEX.md" 2>/dev/null || echo 0)
  if [ "$REWORK_COUNT" -gt 0 ]; then
    echo "WARN: $REWORK_COUNT tasks have REWORK verdict — verify before closing"
  fi
fi
```

---

# §4 VSTUPY

**Required inputs (must exist):**

- `{WORK_ROOT}/config.md` — GIT and COMMANDS configuration
- `{WORK_ROOT}/state.md` — current sprint number, phase (must be "closing")
- `{WORK_ROOT}/sprints/sprint-{N}.md` — Task Queue with task IDs and verdicts
- `{WORK_ROOT}/backlog/{id}.md` — per-task metadata (branch, status, review_report)
- `{WORK_ROOT}/reports/review-*.md` — review reports with verdicts
- `{WORK_ROOT}/reviews/INDEX.md` (optional) — governance index for REWORK tracking

**Environment variables:**
- `WORK_ROOT` — project root (e.g., `/home/user/my-project`)
- `MAX_TASKS` (optional) — max tasks to merge per close run (default: 50)

---

# §5 VÝSTUPY

All reports use schema `fabric.report.v1` with optional `version: "1.0"` field.

**Per-task close reports (write-once, no overwrite):**
- `{WORK_ROOT}/reports/close-{task_id}-{YYYY-MM-DD}-{run_id}.md`
- Contains: merge_commit, test result, lint result, branch info
- Idempotence guard: if file exists, skip (already merged)

**Sprint summary report (append-only with dedup):**
- `{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md`
- Contains: Task Status table, Summary, Carry-over reasons
- Dedup guard: check if task_id already in table before appending

**Updated backlog items:**
- `{WORK_ROOT}/backlog/{id}.md` — update `status: DONE`, `merge_commit: {sha}`, `updated: {YYYY-MM-DD}`

**Updated indices:**
- `{WORK_ROOT}/backlog.md` — regenerated after each merge (or at end)
- `{WORK_ROOT}/sprints/sprint-{N}.md` — update Task Queue statuses to DONE/CARRY-OVER

**State reset:**
- `{WORK_ROOT}/state.md` — set `wip_item: null`, `wip_branch: null`

---

# §6 FAST PATH — Quality gates deterministico

After each merge to `main`, run gates via `fabric.py` (logs to `{WORK_ROOT}/logs/commands/`):

```bash
python skills/fabric-init/tools/fabric.py run test --tail 200
python skills/fabric-init/tools/fabric.py run lint --tail 200
python skills/fabric-init/tools/fabric.py run format_check --tail 200
```

Update merge_commit and status metadata via plan/apply pattern, not manually.

**Gate failure handling:**
- Test/lint/format failures are logged as warnings, not fatal
- Close continues with next task (fail-open principle)
- Evidence is recorded in per-task close report

---

# §7 POSTUP (Orchestrace a Sekvence)

Close is a **procedural batching skill** — run once per sprint, iterates all tasks in Task Queue sequentially.

**High-level workflow overview:**

1. **State & Precondition Validation** — verify config, phase, sprint plan exist
2. **Task Classification** — identify MERGEABLE vs CARRY-OVER tasks
3. **Sequential Merge Loop** — for each MERGEABLE task:
   - Security pre-scan (eval, exec, shell=True checks)
   - Prepare main branch (fetch, pull, reset)
   - Squash merge with conflict detection and recovery
   - Commit with message format validation (WQ8)
   - Run quality gates (test, lint, format_check)
   - Update backlog item with merge_commit and status: DONE
4. **Carry-Over Documentation** — for each CARRY-OVER task, record reason
5. **Index Regeneration** — update backlog.md and sprints/sprint-{N}.md
6. **Sprint Report Generation** — create close-sprint-{N}-{YYYY-MM-DD}.md
7. **State Reset** — clear wip_item and wip_branch

> **Detaily procedury merge loop, stub verification, commit message validation, squash conflict handling, rebase logic, pre-merge divergence checks, per-task file existence checks, security scan patterns, carry-over classification criteria, and full error recovery procedures viz references/workflow.md**

**Stub verification importance:**
- Task must not contain `pass`, `raise NotImplementedError`, `# TODO`, `# FIXME`, `... # stub`
- Review may have missed stubs; verify in merge diff before commit
- If stubs found: log as WARNING in close report (don't abort merge)

---

# §8 QUALITY GATES

**Gates run AFTER each merge to main:**

- **Test:** `COMMANDS.test` must complete within timeout; failures logged as warnings
- **Lint:** `COMMANDS.lint` must complete; failures logged as warnings (skip if empty in bootstrap mode)
- **Format Check:** `COMMANDS.format_check` must complete; failures logged as warnings (skip if empty)

**Gate failure semantics:**
- Does not block sprint close (fail-open)
- Evidence recorded in per-task close report
- Issue tracked in intake if consistent failures detected

**Pre-merge validations (no gate):**
- Review verdict = CLEAN (not REWORK/FAIL)
- Branch exists and is accessible
- Depends-on dependencies all DONE
- Squash merge conflict-free

---

# §9 REPORT TEMPLATE

Per-task close report structure:

```yaml
---
schema: fabric.report.v1
kind: close
version: "1.0"
task_id: "{task_id}"
sprint_number: {N}
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
merge_commit: "{sha}"
test_result: PASS|FAIL|SKIP
lint_result: PASS|FAIL|SKIP
format_result: PASS|FAIL|SKIP
---

# {task_id} Close Report

## Summary
[Brief summary of what was merged]

## Merge Details
- **Branch:** {branch_name}
- **Merge Commit:** {sha}
- **Squash:** Yes
- **Review Status:** CLEAN (from review-{task_id}-{date}.md)

## Quality Gates
- **Test Result:** {PASS|FAIL|SKIP} (exit code: {N})
- **Lint Result:** {PASS|FAIL|SKIP} (exit code: {N})
- **Format Result:** {PASS|FAIL|SKIP} (exit code: {N})

## Backlog Update
Updated `{WORK_ROOT}/backlog/{task_id}.md`:
```yaml
status: DONE
merge_commit: {sha}
updated: {YYYY-MM-DD}
```
```

Sprint summary report includes Task Status table with columns: `Task ID`, `Title`, `Status`, `Reason`, `Merge Commit`.

---

# §10 SELF-CHECK

Before closing skill execution, verify:

```bash
# 1. All MERGEABLE tasks have close reports
MERGEABLE_COUNT=$(grep "^| T-" "{WORK_ROOT}/reports/close-sprint-${SPRINT_N}-{YYYY-MM-DD}.md" | grep -c "DONE")
if [ "$MERGEABLE_COUNT" -eq 0 ]; then
  echo "WARN: no tasks merged (all carry-over?) — verify intentional"
fi

# 2. Backlog index regenerated and consistent
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "ERROR: backlog index not regenerated"
  exit 1
fi

# 3. State wip_item and wip_branch reset to null
WIP_ITEM=$(grep '^wip_item:' "{WORK_ROOT}/state.md" | awk '{print $2}')
WIP_BRANCH=$(grep '^wip_branch:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$WIP_ITEM" != "null" ] || [ "$WIP_BRANCH" != "null" ]; then
  echo "WARN: state wip_item/wip_branch not reset to null"
fi

# 4. Sprint report has required frontmatter and sections
if ! grep -q "schema: fabric.report.v1" "{WORK_ROOT}/reports/close-sprint-${SPRINT_N}-{YYYY-MM-DD}.md"; then
  echo "ERROR: sprint report missing schema frontmatter"
  exit 1
fi

echo "Self-check passed: sprint close complete"
```

---

# §11 FAILURE HANDLING

**Merge conflict during squash merge:**
- Run `git merge --abort` (or `git reset --merge` if --abort fails)
- Verify clean working tree: `git status --porcelain`
- If dirty: run `git checkout -- .` and `git clean -fd`
- Create intake item `intake/close-merge-conflict-{id}.md`
- Mark task as CARRY-OVER with reason: `MERGE_CONFLICT`
- Continue to next MERGEABLE task (do not block sprint close)

**Rebase failure (if branch diverged from main):**
- Run `git rebase --abort`
- Create intake item `intake/close-rebase-failed-{id}.md`
- Mark task as CARRY-OVER with reason: `REBASE_CONFLICT`
- Continue to next task

**Commit message validation failure:**
- Pattern must match: `^(feat|fix|chore|refactor)\([A-Z]+-[0-9]+\): .{10,}`
- If validation fails: reject merge, create intake item, mark CARRY-OVER
- Reason: `INVALID_COMMIT_MESSAGE`

**Precondition failure:**
- Create intake item `intake/close-missing-config.md`
- Exit with FAIL status
- Do not start merge loop

**Security scan detects injection patterns:**
- Create intake item `intake/close-security-scan-{id}.md` with diff snippet
- Log WARNING in close report
- Continue merge (human review required post-sprint)

---

# §12 METADATA

| Field | Value |
|-------|-------|
| **Skill Name** | fabric-close |
| **Phase** | closing |
| **Depends On** | fabric-review (task reviews must complete first) |
| **Feeds Into** | fabric-loop (orchestrator), backlog (via index regeneration) |
| **Estimated Duration** | ~2-5 min per task (merge + gates) |
| **Failure Mode** | Fail-open (gates failures don't block close, logged as warnings) |
| **Idempotence** | Per-task reports are write-once (rerunning skips merged tasks) |
| **Builder Template** | Yes (sections §1-§12) |

---

**For detailed procedures, concrete examples, stub verification logic, commit message patterns, and full error recovery flows, see:**
- `references/workflow.md` — detailed closing steps, burndown tracking, merge loop orchestration
- `references/examples.md` — K10 concrete examples with real LLMem project data

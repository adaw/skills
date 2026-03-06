# CLOSE WORKFLOW — Detailed Procedures

This document contains the detailed merge loop procedures, security checks, commit validation, conflict handling, and burndown tracking referenced from SKILL.md §7.

## Task Classification: MERGEABLE vs CARRY-OVER

### MERGEABLE Criteria

A task is MERGEABLE if ALL conditions hold:

```bash
# 1. Backlog file must exist
[ -f "{WORK_ROOT}/backlog/${id}.md" ] || MERGEABLE=false

# 2. Task status must be IN_REVIEW or DONE
TASK_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${id}.md" | awk '{print $2}')
[ "$TASK_STATUS" = "IN_REVIEW" ] || [ "$TASK_STATUS" = "DONE" ] || MERGEABLE=false

# 3. Branch must exist (local or remote)
TASK_BRANCH=$(grep 'branch:' "{WORK_ROOT}/backlog/${id}.md" | awk '{print $2}')
[ -z "$TASK_BRANCH" ] && MERGEABLE=false
git rev-parse --verify "$TASK_BRANCH" >/dev/null 2>&1 || MERGEABLE=false

# 4. Review verdict must be CLEAN (not REWORK, not FAIL)
REVIEW_REPORT=$(grep 'review_report:' "{WORK_ROOT}/backlog/${id}.md" | awk '{print $2}')
if [ -n "$REVIEW_REPORT" ] && [ -f "{WORK_ROOT}/${REVIEW_REPORT}" ]; then
  REVIEW_VERDICT=$(grep '^verdict:' "{WORK_ROOT}/${REVIEW_REPORT}" | awk '{print $2}')
  [ "$REVIEW_VERDICT" = "CLEAN" ] || MERGEABLE=false
else
  MERGEABLE=false  # No review report
fi

# 5. Depends-on check: all dependencies must be DONE
DEPENDS=$(grep 'depends_on:' "{WORK_ROOT}/backlog/${id}.md" | sed 's/depends_on://' | tr -d '[],' | xargs)
for DEP in $DEPENDS; do
  DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" 2>/dev/null | awk '{print $2}')
  [ "$DEP_STATUS" = "DONE" ] || MERGEABLE=false
done

# 6. No stubs (pass, NotImplementedError, TODO, FIXME) in diff
STUBS=$(git diff "${main_branch}...${TASK_BRANCH}" -- '*.py' 2>/dev/null | grep -cE 'pass$|raise NotImplementedError|# TODO|# FIXME|\.\.\.  # stub')
[ "$STUBS" -gt 0 ] && MERGEABLE=false
```

### CARRY-OVER Reasons

If any condition fails, classify as CARRY-OVER with reason:

| Reason | Condition |
|--------|-----------|
| `NO_BACKLOG` | backlog/{id}.md missing |
| `STATUS_NOT_READY` | status not IN_REVIEW or DONE |
| `NO_BRANCH` | branch missing or deleted |
| `NO_REVIEW` | review_report missing or not found |
| `REWORK` | review verdict = REWORK |
| `REVIEW_FAIL` | review verdict = FAIL |
| `BLOCKED` | depends-on dependency not DONE |
| `STUBS_FOUND` | diff contains pass/NotImplementedError/TODO/FIXME |
| `MERGE_CONFLICT` | squash merge failed with conflicts |
| `REBASE_CONFLICT` | branch rebase failed (diverged from main) |
| `INVALID_COMMIT_MESSAGE` | commit message does not match pattern |
| `SECURITY_SCAN_ISSUE` | diff contains injection patterns |

---

## Pre-Merge Security Scan

Before each squash merge, scan diff for injection patterns (POVINNÉ):

```bash
# Security scan on diff
git diff "${main_branch}...${branch}" -- '*.py' | grep -nE \
  'eval\(|exec\(|subprocess.*shell=True|__import__|pickle\.loads|yaml\.load\(|os\.system\(|input\(' \
  > /tmp/security-scan.txt 2>/dev/null

if [ -s /tmp/security-scan.txt ]; then
  echo "CRITICAL: potential security issues found in $id diff:"
  cat /tmp/security-scan.txt

  # Create intake item for review
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "close" \
    --slug "security-scan-${id}" \
    --title "Security scan found potential injection patterns in $id (review diff before merge)"

  # Mark as CARRY-OVER with reason: SECURITY_SCAN_ISSUE
  # Log WARNING in close report
  # Do NOT merge until manual review
fi
```

### Patterns Scanned

- `eval(` — arbitrary code execution
- `exec(` — arbitrary code execution
- `subprocess.*shell=True` — shell injection risk
- `__import__` — dynamic import risk
- `pickle.loads` — deserialization attack
- `yaml.load(` — unsafe YAML deserialization (no explicit Loader)
- `os.system(` — shell command execution
- `input(` — (only in specific contexts, may be false positive)

---

## Sequential Merge Loop

### Step 1: Prepare main branch

```bash
# Fetch all remotes with timeout
timeout 60 git fetch --all --prune 2>&1 | tee -a "{WORK_ROOT}/logs/close.log"
FETCH_EXIT=$?
if [ $FETCH_EXIT -ne 0 ] && [ $FETCH_EXIT -ne 124 ]; then
  echo "WARN: git fetch failed (exit $FETCH_EXIT)"
  GATE_RESULT="FETCH_FAIL"
fi

# Checkout main
git checkout "${main_branch}" 2>&1 | tee -a "{WORK_ROOT}/logs/close.log"
CHECKOUT_EXIT=$?
if [ $CHECKOUT_EXIT -ne 0 ]; then
  echo "ERROR: cannot checkout main ($main_branch)"
  exit 1
fi

# Pull latest from remote (fail-open if network issue)
git pull --ff-only 2>&1 | tee -a "{WORK_ROOT}/logs/close.log"
PULL_EXIT=$?
if [ $PULL_EXIT -ne 0 ]; then
  echo "WARN: pull failed (exit $PULL_EXIT), using local main"
fi

# Save pre-merge state
PRE=$(git rev-parse HEAD)
echo "Pre-merge main HEAD: $PRE"
```

### Step 2: Verify branch accessibility

```bash
# Local or remote branch check
if git show-ref --verify "refs/heads/${branch}" >/dev/null 2>&1; then
  echo "Branch exists locally: $branch"
elif git rev-parse --verify "origin/${branch}" >/dev/null 2>&1; then
  echo "Branch exists on remote, checking out: $branch"
  git checkout -b "${branch}" "origin/${branch}"
  CHECKOUT_EXIT=$?
  if [ $CHECKOUT_EXIT -ne 0 ]; then
    echo "ERROR: cannot checkout remote branch origin/$branch"
    # Mark CARRY-OVER: NO_BRANCH
    continue
  fi
else
  echo "ERROR: branch $branch not found (local or remote)"
  # Mark CARRY-OVER: NO_BRANCH
  continue
fi
```

### Step 3: Pre-merge divergence check (rebase if needed)

```bash
# Switch to main for divergence check
git checkout "${main_branch}"

# Check if branch is based on current main
MERGE_BASE=$(git merge-base "${main_branch}" "${branch}")
MAIN_HEAD=$(git rev-parse "${main_branch}")

if [ "$MERGE_BASE" != "$MAIN_HEAD" ]; then
  echo "WARN: branch $branch diverged from $main_branch"
  echo "  Merge-base: $MERGE_BASE"
  echo "  Main HEAD:  $MAIN_HEAD"

  # Attempt safe rebase on feature branch (not on main)
  git checkout "${branch}"
  git rebase "${main_branch}" 2>&1 | tee -a "{WORK_ROOT}/logs/close.log"
  REBASE_EXIT=$?

  if [ $REBASE_EXIT -ne 0 ]; then
    # Rebase failed — abort and mark CARRY-OVER
    git rebase --abort 2>/dev/null
    git checkout "${main_branch}" 2>/dev/null

    echo "ERROR: rebase failed for branch $branch"
    # Create intake item
    python skills/fabric-init/tools/fabric.py intake-new \
      --source "close" \
      --slug "rebase-failed-${id}" \
      --title "Rebase failed for $id branch: $branch (merge-base diverged)"

    # Mark CARRY-OVER: REBASE_CONFLICT
    # Continue to next task
    continue
  fi

  git checkout "${main_branch}"
fi
```

### Step 4: Stub verification (pre-merge warning check)

```bash
# Verify task files do not contain stubs
TASK_FILES=$(git diff --name-only "${main_branch}...${branch}" -- '*.py' 2>/dev/null)
STUBS_FOUND=0
STUB_FILES=""

for F in $TASK_FILES; do
  [ -f "$F" ] || continue
  if grep -qnE 'pass$|raise NotImplementedError|# TODO|# FIXME|\.\.\.  # stub' "$F" 2>/dev/null; then
    echo "WARN: stub detected in $F for task $id"
    STUB_FILES="${STUB_FILES}${F}, "
    STUBS_FOUND=$((STUBS_FOUND + 1))
  fi
done

if [ "$STUBS_FOUND" -gt 0 ]; then
  echo "WARN: $STUBS_FOUND files contain stubs (review may have missed them)"
  # Log in close report but CONTINUE merge (not fatal)
fi
```

### Step 5: Security pre-scan (before squash merge)

```bash
# Run security scan (see section above)
# If issues found: create intake item, mark CARRY-OVER, continue
```

### Step 6: Squash merge with conflict detection

```bash
git merge --squash "${branch}" 2>&1 | tee -a "{WORK_ROOT}/logs/close.log"
MERGE_EXIT=$?

if [ $MERGE_EXIT -ne 0 ]; then
  echo "ERROR: squash merge conflict for branch $branch"

  # Conflict resolution: clean up merge state
  git merge --abort 2>/dev/null || git reset --merge 2>/dev/null
  ABORT_EXIT=$?

  if [ $ABORT_EXIT -ne 0 ]; then
    echo "WARN: merge --abort failed, trying reset --merge"
    git reset --merge 2>/dev/null || true
  fi

  # Verify clean working tree
  if [ -n "$(git status --porcelain)" ]; then
    echo "WARN: dirty working tree after merge abort, cleaning"
    git checkout -- . 2>/dev/null
    git clean -fd 2>/dev/null

    # Last resort: hard reset to pre-merge HEAD
    if [ -n "$(git status --porcelain)" ]; then
      echo "WARN: cleanup failed, hard reset to pre-merge HEAD ($PRE)"
      git reset --hard "$PRE" 2>/dev/null
    fi
  fi

  # Verify final state is clean
  if [ -n "$(git status --porcelain)" ]; then
    echo "CRITICAL: cannot clean merge state for task $id"
    # Mark CARRY-OVER: MERGE_CONFLICT, create intake
    # Continue (fail-open)
  else
    echo "Merge state cleaned, continuing"
    # Mark CARRY-OVER: MERGE_CONFLICT
    # Log conflict details to intake
    # Continue
  fi

  # Create intake item
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "close" \
    --slug "merge-conflict-${id}" \
    --title "Squash merge conflict for $id branch: $branch (needs manual resolution)"

  continue  # Move to next task
fi

echo "Squash merge successful for $id"
```

### Step 7: Commit with message validation (WQ8 ENFORCEMENT)

```bash
# Prepare commit message
COMMIT_MSG="feat(${id}): ${title} (sprint ${N})"

# Validate message format
# Pattern: ^(feat|fix|chore|refactor)\([A-Z]+-[0-9]+\): .{10,}
# Requirements:
#   1. Type + scope: (feat|fix|chore|refactor)(ID): format
#   2. Description: ≥10 characters (no "fix stuff")
#   3. ID format: [A-Z]+-[0-9]+ (e.g., T-TRI-02)

if ! echo "$COMMIT_MSG" | grep -qE '^(feat|fix|chore|refactor)\([A-Z]+-[0-9]+\): .{10,}'; then
  echo "ERROR: commit message format invalid: $COMMIT_MSG"
  echo "Expected: feat|fix|chore|refactor({ID}): {description ≥10 chars}"

  # Additional validation: description must not be generic verb alone
  DESC=$(echo "$COMMIT_MSG" | sed 's/^[^)]*): //')
  if echo "$DESC" | grep -qE '^(fix|add|update|change|modify|improve|work|do|stuff|thing)$'; then
    echo "ERROR: commit description too generic: '$DESC'"
    echo "Use specific verb: 'implement', 'refactor', 'optimize', 'consolidate', etc."
  fi

  # Mark CARRY-OVER: INVALID_COMMIT_MESSAGE
  git reset HEAD 2>/dev/null  # Clean up staged changes
  continue
fi

# Commit with validated message
git commit -m "$COMMIT_MSG" 2>&1 | tee -a "{WORK_ROOT}/logs/close.log"
COMMIT_EXIT=$?

if [ $COMMIT_EXIT -ne 0 ]; then
  echo "ERROR: commit failed after squash merge (exit $COMMIT_EXIT)"
  git reset HEAD 2>/dev/null

  # Create intake item
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "close" \
    --slug "commit-failed-${id}" \
    --title "Commit failed for $id (after squash merge)"

  # Mark CARRY-OVER: COMMIT_FAILED
  continue
fi

# Save merge commit SHA
MERGE_COMMIT=$(git rev-parse HEAD)
echo "Merge commit: $MERGE_COMMIT for task $id"
```

### Step 8: Run quality gates (FAST PATH)

```bash
# After successful commit, run quality gates
# Failures are warnings, not fatal (fail-open)

TEST_RESULT="SKIP"
LINT_RESULT="SKIP"
FORMAT_RESULT="SKIP"

# Test gate
if [ -n "$COMMANDS_TEST" ] && [ "$COMMANDS_TEST" != "TBD" ]; then
  echo "Running test gate..."
  python skills/fabric-init/tools/fabric.py run test --tail 200 2>&1 | tee -a "{WORK_ROOT}/logs/commands/test.log"
  TEST_EXIT=$?
  TEST_RESULT=$([ $TEST_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")
  echo "Test result: $TEST_RESULT (exit code: $TEST_EXIT)"
fi

# Lint gate (skip if empty in bootstrap mode)
if [ -n "$COMMANDS_LINT" ] && [ "$COMMANDS_LINT" != "TBD" ] && [ "$COMMANDS_LINT" != "" ]; then
  echo "Running lint gate..."
  python skills/fabric-init/tools/fabric.py run lint --tail 200 2>&1 | tee -a "{WORK_ROOT}/logs/commands/lint.log"
  LINT_EXIT=$?
  LINT_RESULT=$([ $LINT_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")
  echo "Lint result: $LINT_RESULT (exit code: $LINT_EXIT)"
fi

# Format check gate (skip if empty in bootstrap mode)
if [ -n "$COMMANDS_FORMAT" ] && [ "$COMMANDS_FORMAT" != "TBD" ] && [ "$COMMANDS_FORMAT" != "" ]; then
  echo "Running format check gate..."
  python skills/fabric-init/tools/fabric.py run format_check --tail 200 2>&1 | tee -a "{WORK_ROOT}/logs/commands/format.log"
  FORMAT_EXIT=$?
  FORMAT_RESULT=$([ $FORMAT_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")
  echo "Format check result: $FORMAT_RESULT (exit code: $FORMAT_EXIT)"
fi

# Log gate results (warnings only, no exit)
if [ "$TEST_RESULT" = "FAIL" ] || [ "$LINT_RESULT" = "FAIL" ] || [ "$FORMAT_RESULT" = "FAIL" ]; then
  echo "WARN: one or more quality gates failed (logged for review, sprint close continues)"
fi
```

### Step 9: Update backlog item

```bash
# Update backlog item with merge evidence
BACKLOG_FILE="{WORK_ROOT}/backlog/${id}.md"

# Use sed to update status and merge_commit (or patch tool if available)
sed -i "s/^status:.*/status: DONE/" "$BACKLOG_FILE"
sed -i "s/^merge_commit:.*/merge_commit: $MERGE_COMMIT/" "$BACKLOG_FILE"
sed -i "s/^updated:.*/updated: $(date +%Y-%m-%d)/" "$BACKLOG_FILE"

echo "Updated backlog item: $id (status: DONE, merge_commit: $MERGE_COMMIT)"
```

### Step 10: Write per-task close report

```bash
# Create per-task close report
CLOSE_REPORT="{WORK_ROOT}/reports/close-${id}-$(date +%Y-%m-%d)-${RUN_ID}.md"

# Idempotence guard
if [ -f "$CLOSE_REPORT" ]; then
  echo "SKIP: close report already exists: $CLOSE_REPORT (already merged)"
  continue
fi

# Write report with frontmatter and details
cat > "$CLOSE_REPORT" << EOF
---
schema: fabric.report.v1
kind: close
version: "1.0"
task_id: "${id}"
sprint_number: ${SPRINT_N}
created_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
merge_commit: "${MERGE_COMMIT}"
test_result: ${TEST_RESULT}
lint_result: ${LINT_RESULT}
format_result: ${FORMAT_RESULT}
---

# ${id} Close Report

## Summary

Successfully merged task \`${id}: ${title}\` into main branch.

## Merge Details

- **Branch:** \`${branch}\`
- **Merge Commit:** \`${MERGE_COMMIT}\`
- **Squash:** Yes (1 logical commit)
- **Review Status:** CLEAN

## Quality Gates

- **Test Result:** ${TEST_RESULT}
- **Lint Result:** ${LINT_RESULT}
- **Format Check Result:** ${FORMAT_RESULT}

## Stub Verification

- **Stubs Found:** ${STUBS_FOUND}
- **Affected Files:** ${STUB_FILES}

## Backlog Update

Updated \`backlog/${id}.md\`:
\`\`\`yaml
status: DONE
merge_commit: ${MERGE_COMMIT}
updated: $(date +%Y-%m-%d)
\`\`\`
EOF

echo "Per-task close report written: $CLOSE_REPORT"
```

---

## Carry-Over Documentation

For each CARRY-OVER task, record reason in sprint summary:

```bash
# Append to sprint summary carry-over section
SPRINT_REPORT="{WORK_ROOT}/reports/close-sprint-${N}-$(date +%Y-%m-%d).md"

if [ -n "$CARRY_OVER_REASON" ]; then
  echo "| ${id} | ${title} | CARRY-OVER | ${CARRY_OVER_REASON} |" >> "$SPRINT_REPORT.carry-over"
  echo "Carry-over: $id — reason: $CARRY_OVER_REASON"
fi
```

---

## Burndown Tracking

Track completed tasks and carry-overs for burndown:

```bash
# Count tasks by status at sprint end
TOTAL_TASKS=$(grep -c "^| T-" "{WORK_ROOT}/sprints/sprint-${N}.md")
DONE_COUNT=$(grep "^| T-" "{WORK_ROOT}/reports/close-sprint-${N}-$(date +%Y-%m-%d).md" | grep -c "DONE" 2>/dev/null || echo 0)
CARRY_OVER_COUNT=$(grep "^| T-" "{WORK_ROOT}/reports/close-sprint-${N}-$(date +%Y-%m-%d).md" | grep -c "CARRY-OVER" 2>/dev/null || echo 0)

echo "Burndown Summary:"
echo "  Total tasks: $TOTAL_TASKS"
echo "  Completed (DONE): $DONE_COUNT"
echo "  Carry-over: $CARRY_OVER_COUNT"
echo "  Sprint burn rate: $((DONE_COUNT * 100 / TOTAL_TASKS))%"
```

---

## Sprint Summary Report Structure

Generated at sprint close, append-only with dedup guard:

```yaml
---
schema: fabric.report.v1
kind: sprint-close
version: "1.0"
sprint_number: {N}
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
---

# Sprint {N} Close Report

## Task Status

| Task ID | Title | Status | Reason | Merge Commit |
|---------|-------|--------|--------|--------------|
| T-TRI-02 | Implement triage heuristics | DONE | Merged cleanly | abc1234def567 |
| T-EMB-01 | Add hash embedder | CARRY-OVER | STUBS_FOUND | — |

## Summary

- Total tasks: 12
- Completed: 10 (83%)
- Carry-over: 2 (17%)

## Next Sprint

- Rework T-EMB-01 (remove stubs, resubmit review)
- Carry T-STO-03 (depends-on T-EMB-01)

## Quality Gates Summary

- Test: 10/10 PASS (100%)
- Lint: 10/10 PASS (100%)
- Format: 10/10 PASS (100%)
```

---

## Path Traversal Guard

All dynamic path inputs must be validated:

```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic inputs
validate_path "$TASK_FILE"
validate_path "$BRANCH_NAME"
validate_path "$REVIEW_REPORT"
```

---

## Max Tasks Guard (K2 Fix)

Prevent runaway merge loops with counter:

```bash
MAX_TASKS=${MAX_TASKS:-50}
MERGE_COUNTER=0

while read -r task_id; do
  MERGE_COUNTER=$((MERGE_COUNTER + 1))

  if [ "$MERGE_COUNTER" -ge "$MAX_TASKS" ]; then
    echo "WARN: max task merges reached ($MERGE_COUNTER/$MAX_TASKS)"
    echo "Create new close dispatch to continue remaining tasks"
    break
  fi

  # ... merge task ...
done
```

---

## Error Recovery Checklist

When merge fails at any step:

1. Verify clean working tree: `git status --porcelain`
2. If dirty: `git checkout -- .` then `git clean -fd`
3. If still dirty: `git reset --hard HEAD`
4. Verify on main branch: `git rev-parse --abbrev-ref HEAD`
5. Create intake item with: task_id, branch_name, error message, pre-merge HEAD
6. Mark task as CARRY-OVER with appropriate reason
7. Continue to next MERGEABLE task (do not break loop)
8. Log summary in sprint close report

---

## Dedup Guard for Sprint Summary

When appending to sprint summary, check for duplicate task entries:

```bash
SPRINT_REPORT="{WORK_ROOT}/reports/close-sprint-${N}-$(date +%Y-%m-%d).md"

if [ -f "$SPRINT_REPORT" ]; then
  # Check if task_id already in table (prevents duplicate rows)
  if grep -q "| ${TASK_ID} |" "$SPRINT_REPORT" 2>/dev/null; then
    echo "SKIP: task $TASK_ID already in sprint summary (dedup)"
    # Do not append duplicate row
  else
    echo "Appending new task row to sprint summary"
    # Append row to Task Status table
  fi
else
  # Create new sprint summary with header
  cat > "$SPRINT_REPORT" << 'EOF'
---
schema: fabric.report.v1
kind: sprint-close
version: "1.0"
sprint_number: {N}
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
---

# Sprint {N} Close Report

## Task Status

| Task ID | Title | Status | Reason | Merge Commit |
|---------|-------|--------|--------|--------------|
EOF
fi
```

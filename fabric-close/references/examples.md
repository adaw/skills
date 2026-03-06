# CLOSE EXAMPLES — K10 Concrete Cases with LLMem Data

Real-world sprint close examples using the LLMem project as reference context.

---

## Example 1: Successful Task Merge (T-TRI-02)

**Task:** T-TRI-02 — Implement triage heuristics (deterministic extraction)

### Backlog State Before Close

**File:** `{WORK_ROOT}/backlog/T-TRI-02.md`

```yaml
---
task_id: T-TRI-02
title: "Implement triage heuristics"
type: Feature
status: IN_REVIEW
priority: P1
effort_estimate: M
branch: feature/tri-02-heuristics
review_report: reports/review-T-TRI-02-2026-03-05.md
depends_on: []
---

# T-TRI-02 — Implement Triage Heuristics

## What

Implement deterministic triage heuristics for triaging observations into memory items.
Regex-based extraction (no LLM in hot path) for secrets, preferences, decisions, facts.

## Why

Memory system needs efficient event → item mapping. Heuristics enable fail-open capture.

## Done When

- [ ] Heuristics module added to src/llmem/triage/heuristics.py
- [ ] Pattern matching for secret detection (PII, API keys, passwords)
- [ ] Coverage ≥60% on heuristics module
- [ ] All tests PASS
- [ ] Code review PASS (no REWORK)

## Evidence

- Branch: feature/tri-02-heuristics
- Tests: tests/test_triage_and_recall.py (9/9 PASS)
- Coverage before: 62% → after: 78%
- Review: CLEAN (2026-03-05)
```

### Review Report State

**File:** `{WORK_ROOT}/reports/review-T-TRI-02-2026-03-05.md`

```yaml
---
schema: fabric.report.v1
kind: review
version: "1.0"
task_id: T-TRI-02
reviewed_at: "2026-03-05T14:30:00Z"
verdict: CLEAN
reviewer: reviewer1
---

# T-TRI-02 Review — CLEAN

## Verdict: CLEAN

Task T-TRI-02 is ready for merge. All requirements met:

✓ Code quality acceptable (style, readability)
✓ Tests complete and passing (9/9)
✓ Coverage goal met (78% vs target 60%)
✓ No hardcoded secrets in diff
✓ No security concerns in heuristics
✓ Documentation adequate

## Changes Summary

- `src/llmem/triage/heuristics.py` — 450 lines added
  - `extract_memory_items()` main function
  - Secret detection via regex (patterns.py)
  - Deterministic MemoryItem creation
  - Mask PII in non-secret items

- `tests/test_triage_and_recall.py` — 3 test cases added
  - test_triage_deterministic_ids
  - test_triage_secret_detection
  - test_triage_pii_masking

## Minor Notes

- Docstring on `extract_memory_items` is brief; consider expanding for maintainability
- Consider future refactor: extract pattern matching to separate module

**Reviewer:** reviewer1 (2026-03-05 14:30 UTC)
```

### Close Execution

**Task classification:** MERGEABLE ✓

```bash
TASK_ID="T-TRI-02"
TASK_STATUS="IN_REVIEW"  # ✓ Ready for merge
TASK_BRANCH="feature/tri-02-heuristics"
git rev-parse --verify "feature/tri-02-heuristics" >/dev/null 2>&1  # ✓ Branch exists
REVIEW_VERDICT="CLEAN"  # ✓ Review CLEAN
DEPENDS=""  # ✓ No dependencies
STUBS=$(git diff main...feature/tri-02-heuristics -- '*.py' | grep -cE 'pass$|NotImplementedError')  # ✓ 0 stubs
```

### Merge Steps

1. **Prepare main:**
   ```bash
   git fetch --all --prune
   git checkout main
   git pull --ff-only
   PRE=$(git rev-parse HEAD)  # Save pre-merge state
   ```

2. **Squash merge:**
   ```bash
   git merge --squash feature/tri-02-heuristics
   # Merge succeeded (no conflicts)
   ```

3. **Commit with validation:**
   ```bash
   COMMIT_MSG="feat(T-TRI-02): implement triage heuristics (sprint 2)"
   # Validation: ✓ Format matches ^feat\([A-Z]+-[0-9]+\): .{10,}
   # Validation: ✓ Description is specific ("implement triage heuristics" > 10 chars)
   git commit -m "$COMMIT_MSG"
   MERGE_COMMIT="abc1234def567"
   ```

4. **Quality gates:**
   ```bash
   python skills/fabric-init/tools/fabric.py run test --tail 200
   # EXIT: 0 — TEST_RESULT="PASS" (9/9 tests pass)

   python skills/fabric-init/tools/fabric.py run lint --tail 200
   # EXIT: 0 — LINT_RESULT="PASS"

   python skills/fabric-init/tools/fabric.py run format_check --tail 200
   # EXIT: 0 — FORMAT_RESULT="PASS"
   ```

5. **Update backlog:**
   ```yaml
   # Before:
   status: IN_REVIEW
   merge_commit: null

   # After:
   status: DONE
   merge_commit: abc1234def567
   updated: 2026-03-06
   ```

### Close Report Generated

**File:** `{WORK_ROOT}/reports/close-T-TRI-02-2026-03-06-run123.md`

```yaml
---
schema: fabric.report.v1
kind: close
version: "1.0"
task_id: "T-TRI-02"
sprint_number: 2
created_at: "2026-03-06T15:45:00Z"
merge_commit: "abc1234def567"
test_result: PASS
lint_result: PASS
format_result: PASS
---

# T-TRI-02 Close Report — Triage Heuristics

## Summary

Successfully merged feature/tri-02-heuristics into main. Deterministic triage heuristics now live in production.

## Merge Details

- **Branch:** feature/tri-02-heuristics
- **Merge Commit:** abc1234def567
- **Squash:** Yes (1 logical commit)
- **Review Status:** CLEAN (review-T-TRI-02-2026-03-05.md)

## Quality Gates

- **Test Result:** PASS (exit code: 0)
  - 9/9 tests passed (triage suite)
  - Coverage: 78% (up from 62%)
- **Lint Result:** PASS (exit code: 0)
  - 0 style violations
- **Format Check Result:** PASS (exit code: 0)

## Stub Verification

- **Stubs Found:** 0
- **Verification Status:** PASS (no stubs in diff)

## Backlog Update

Updated `backlog/T-TRI-02.md`:
```yaml
status: DONE
merge_commit: abc1234def567
updated: 2026-03-06
```
```

---

## Example 2: Carry-Over — Stubs Found (T-EMB-01)

**Task:** T-EMB-01 — Add hash embedder for deterministic embeddings

### Classification

**Task classification:** CARRY-OVER ✗

**Reason:** STUBS_FOUND (3 files contain `pass` or `# TODO`)

### Backlog State

**File:** `{WORK_ROOT}/backlog/T-EMB-01.md`

```yaml
---
task_id: T-EMB-01
title: "Add hash embedder for deterministic embeddings"
type: Feature
status: IN_REVIEW
priority: P2
branch: feature/emb-01-hash-embedder
review_report: reports/review-T-EMB-01-2026-03-05.md
---
```

### Review Verdict

**File:** `{WORK_ROOT}/reports/review-T-EMB-01-2026-03-05.md`

```yaml
---
verdict: CLEAN
---

# Review CLEAN

However, during close-time stub verification, we detect:
```

### Pre-Merge Verification Detects Stubs

```bash
TASK_ID="T-EMB-01"
git diff main...feature/emb-01-hash-embedder -- '*.py' | \
  grep -nE 'pass$|raise NotImplementedError|# TODO|# FIXME' > /tmp/stubs.txt

# Output (3 stubs found):
# src/llmem/embeddings/hash_embedder.py:45:    pass  # TODO: implement SHA256 hash
# src/llmem/embeddings/hash_embedder.py:67:    # TODO: add salt parameter
# tests/test_embeddings.py:120:    raise NotImplementedError("placeholder test")
```

### Carry-Over Decision

Task T-EMB-01 marked as CARRY-OVER:

```bash
CARRY_OVER_REASON="STUBS_FOUND (3 files contain pass/TODO/NotImplementedError)"
```

### Intake Item Created

**File:** `{WORK_ROOT}/intake/close-stubs-T-EMB-01.md`

```yaml
---
title: "T-EMB-01: Stubs found during close verification (remove before next review)"
status: OPEN
source: fabric-close
priority: P2
---

# Stubs Found in T-EMB-01 During Close Verification

During pre-merge stub verification in fabric-close, detected 3 stubs:

1. `src/llmem/embeddings/hash_embedder.py:45`
   ```python
   def hash_embedding(self, text):
       pass  # TODO: implement SHA256 hash
   ```

2. `src/llmem/embeddings/hash_embedder.py:67`
   ```python
   def add_salt(self, salt):
       # TODO: add salt parameter
       ...
   ```

3. `tests/test_embeddings.py:120`
   ```python
   def test_hash_embedder_with_salt():
       raise NotImplementedError("placeholder test")
   ```

**Action:** Remove all stubs and resubmit to review before next close.
```

### Sprint Summary Entry

**File:** `{WORK_ROOT}/reports/close-sprint-2-2026-03-06.md`

```markdown
| T-EMB-01 | Add hash embedder | CARRY-OVER | STUBS_FOUND (3 files with pass/TODO) | — |
```

---

## Example 3: Carry-Over — Merge Conflict (T-STO-03)

**Task:** T-STO-03 — Implement Qdrant backend

### Classification

**Task classification:** CARRY-OVER ✗

**Reason:** MERGE_CONFLICT (squash merge failed due to diverged branch)

### Pre-Merge State

```bash
TASK_ID="T-STO-03"
TASK_BRANCH="feature/sto-03-qdrant"

# Branch diverged from main (merge-base ≠ main HEAD)
MERGE_BASE=$(git merge-base main feature/sto-03-qdrant)
MAIN_HEAD=$(git rev-parse main)

# They differ → branch is stale
```

### Merge Attempt

1. **Rebase attempt:**
   ```bash
   git checkout feature/sto-03-qdrant
   git rebase main
   # Conflict in src/llmem/storage/backends/__init__.py
   # Lines 15-35: imports of backend classes clash with main's refactor
   ```

2. **Rebase fails, abort:**
   ```bash
   git rebase --abort
   git checkout main
   # Merge state cleaned
   ```

### Carry-Over Decision

Task marked as CARRY-OVER:

```bash
CARRY_OVER_REASON="REBASE_CONFLICT (branch diverged, rebase conflict in __init__.py)"
```

### Intake Item Created

**File:** `{WORK_ROOT}/intake/close-rebase-failed-T-STO-03.md`

```yaml
---
title: "T-STO-03: Branch rebase conflict (needs manual resolution)"
source: fabric-close
priority: P1
---

# Rebase Conflict for T-STO-03

Branch `feature/sto-03-qdrant` diverged from main. Attempted rebase failed:

**Conflict File:** `src/llmem/storage/backends/__init__.py`

**Merge-base:** `a1b2c3d` (old main)
**Current main HEAD:** `def4567`
**Task branch HEAD:** `ghijkl8`

**Conflict Markers:**
```
<<<<<<< HEAD (main current)
from .qdrant_backend import QdrantBackend
from .inmemory_backend import InMemoryBackend
=======
from .backends.qdrant import QdrantBackend  # Old import style
from .backends.inmemory import InMemoryBackend
>>>>>>> feature/sto-03-qdrant
```

**Action:** Manually rebase and resolve conflict, or recreate branch from current main.
```

### Sprint Summary Entry

```markdown
| T-STO-03 | Implement Qdrant backend | CARRY-OVER | REBASE_CONFLICT (__init__.py) | — |
```

---

## Example 4: Security Scan Detects Injection Pattern (T-API-04)

**Task:** T-API-04 — Implement custom recall API endpoint

### Pre-Merge Security Scan

```bash
TASK_ID="T-API-04"
TASK_BRANCH="feature/api-04-recall"

git diff main...feature/api-04-recall -- '*.py' | \
  grep -nE 'eval\(|exec\(|subprocess.*shell=True|__import__|pickle\.loads|yaml\.load\(' \
  > /tmp/security-scan.txt

# Output (CRITICAL):
# src/llmem/api/routes/recall.py:156:    result = eval(user_query)  # DANGEROUS!
```

### Security Scan Decision

Task marked as CARRY-OVER (fail-safe):

```bash
CARRY_OVER_REASON="SECURITY_SCAN_ISSUE (eval() detected in recall.py:156)"
```

### Intake Item Created

**File:** `{WORK_ROOT}/intake/close-security-scan-T-API-04.md`

```yaml
---
title: "CRITICAL: T-API-04 security scan detected eval() injection risk"
priority: CRITICAL
source: fabric-close
---

# Security Scan — T-API-04 (CRITICAL)

Pre-merge security scan detected potential code injection vulnerability:

**File:** `src/llmem/api/routes/recall.py:156`

**Issue:**
```python
@app.post("/recall")
def recall_endpoint(query: RecallQuery):
    # DANGEROUS: evaluating user input
    result = eval(query.text)  # line 156
    return result
```

**Risk:** Arbitrary code execution if user provides malicious query

**Remediation:**
- Remove `eval()` usage
- Use safe query parsing instead (e.g., QueryParser class)
- Add input validation with pydantic schema
- Re-test and re-review

**Action:** Fix security issue before merge to main. Do NOT merge this branch.
```

### Sprint Summary Entry

```markdown
| T-API-04 | Custom recall API endpoint | CARRY-OVER | SECURITY_SCAN_ISSUE (eval detected) | — |
```

---

## Example 5: Sprint Summary Report (Sprint 2 Completion)

**File:** `{WORK_ROOT}/reports/close-sprint-2-2026-03-06.md`

```yaml
---
schema: fabric.report.v1
kind: sprint-close
version: "1.0"
sprint_number: 2
created_at: "2026-03-06T17:00:00Z"
---

# Sprint 2 Close Report

## Task Status

| Task ID | Title | Status | Reason | Merge Commit |
|---------|-------|--------|--------|--------------|
| T-TRI-02 | Implement triage heuristics | DONE | Merged cleanly | abc1234def567 |
| T-REV-01 | Review framework setup | DONE | Merged cleanly | bcd2345efg678 |
| T-EMB-01 | Add hash embedder | CARRY-OVER | STUBS_FOUND (3 files) | — |
| T-STO-03 | Implement Qdrant backend | CARRY-OVER | REBASE_CONFLICT | — |
| T-API-04 | Custom recall API endpoint | CARRY-OVER | SECURITY_SCAN_ISSUE | — |

## Summary

- **Sprint Duration:** 2026-03-01 to 2026-03-06 (5 days)
- **Total Tasks:** 5
- **Completed (DONE):** 2 (40%)
- **Carry-over:** 3 (60%)
- **Sprint Burn Rate:** 40%

## Quality Gates Summary

- **Test Gates:** 2/2 PASS (100%)
- **Lint Gates:** 2/2 PASS (100%)
- **Format Gates:** 2/2 PASS (100%)

## Coverage Impact

- Coverage before sprint: 62%
- Coverage after sprint: 78% (+ 16 percentage points from T-TRI-02)

## Next Sprint Actions

1. **T-EMB-01 — Remove stubs**
   - Remove `pass` from hash_embedder.py:45
   - Implement SHA256 hash function
   - Complete test_hash_embedder_with_salt
   - Resubmit to review

2. **T-STO-03 — Resolve rebase conflict**
   - Manually rebase feature/sto-03-qdrant onto current main
   - Resolve __init__.py import conflict
   - Test mergeability
   - Resubmit to close

3. **T-API-04 — Fix security issue**
   - Remove eval() usage in recall endpoint
   - Implement safe query parsing
   - Re-test for security
   - Resubmit to review

## Governance Notes

- Carry-over rate (60%) indicates need for stricter review in intake/prio phase
- Review process successfully flagged security issue in T-API-04 (defer merge)
- Stub detection in close phase effective (T-EMB-01 caught)

## Sprint Retrospective

**What Went Well:**
- Security scan caught injection pattern in T-API-04
- Deterministic triage heuristics (T-TRI-02) delivered high quality
- Test and lint coverage maintained across merges

**What Could Improve:**
- Carry-over rate too high; earlier design review needed
- Feature branch rebasing workflow needs clearer documentation
- Stub detection should be part of review, not close phase

**Next Sprint Planning Recommendation:**
- Reduce scope by 20% (5 tasks → 4 tasks) to improve delivery rate
- Add pre-merge rebase check in review workflow
- Implement automated stub detection in pre-commit hooks
```

---

## Example 6: Depends-On Blocking (T-REC-02)

**Task:** T-REC-02 — Implement recall scoring and combination

**Status:** IN_REVIEW, branch ready

**But:**
```yaml
depends_on: [T-EMB-01]
```

**T-EMB-01 status:** CARRY-OVER (stubs found)

### Classification

**Task classification:** CARRY-OVER ✗

**Reason:** BLOCKED (dependency T-EMB-01 not DONE)

```bash
DEPENDS="T-EMB-01"
for DEP in $DEPENDS; do
  DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" | awk '{print $2}')
  if [ "$DEP_STATUS" != "DONE" ]; then
    CARRY_OVER_REASON="BLOCKED (dependency $DEP status=$DEP_STATUS, not DONE)"
  fi
done
```

### Sprint Summary Entry

```markdown
| T-REC-02 | Implement recall scoring | CARRY-OVER | BLOCKED (depends-on T-EMB-01 CARRY-OVER) | — |
```

---

## Example 7: Review REWORK Verdict (T-INJ-01)

**Task:** T-INJ-01 — Implement XML injection block output

### Review State

**File:** `{WORK_ROOT}/reports/review-T-INJ-01-2026-03-05.md`

```yaml
---
verdict: REWORK
---

# T-INJ-01 Review — REWORK

The XML injection output has a security issue: no CDATA wrapping.
Memory content could break XML parsing if it contains `</memory>` markers.

**Required Rework:**
- Wrap memory content in CDATA sections
- Test with adversarial content (e.g., "</memory>" in memory text)
- Resubmit for review
```

### Close-Time Classification

**Task classification:** CARRY-OVER ✗

**Reason:** REWORK (review verdict REWORK, not CLEAN)

```bash
REVIEW_VERDICT=$(grep '^verdict:' "{WORK_ROOT}/reports/review-T-INJ-01-2026-03-05.md" | awk '{print $2}')
if [ "$REVIEW_VERDICT" = "REWORK" ]; then
  CARRY_OVER_REASON="REWORK"
fi
```

### Sprint Summary Entry

```markdown
| T-INJ-01 | XML injection block output | CARRY-OVER | REWORK (CDATA wrapping needed) | — |
```

---

## Example 8: Idempotence Guard (Re-Run Close for Same Sprint)

**Scenario:** Close skill accidentally runs twice for Sprint 2.

**First Run (2026-03-06 15:45):**
```bash
RUN_ID="run123"
CLOSE_REPORT="{WORK_ROOT}/reports/close-T-TRI-02-2026-03-06-run123.md"
# Created successfully
```

**Second Run (2026-03-06 16:30):**
```bash
RUN_ID="run124"
CLOSE_REPORT="{WORK_ROOT}/reports/close-T-TRI-02-2026-03-06-run124.md"

# Different RUN_ID → different filename
# But idempotence check uses backlog status:
TASK_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/T-TRI-02.md" | awk '{print $2}')
if [ "$TASK_STATUS" = "DONE" ]; then
  echo "SKIP: T-TRI-02 already DONE (merge_commit already set)"
  continue
fi
```

Result: Task skipped on second run (idempotence preserved).

---

## Example 9: Max Tasks Guard (K2 Fix)

**Scenario:** Close runs with 47 tasks in queue, MAX_TASKS=50.

```bash
MAX_TASKS=50
MERGE_COUNTER=0

# Tasks 1-47 merge successfully
# Tasks 48-50 not reached in first close run

echo "Processed $MERGE_COUNTER tasks"
# Output: Processed 47 tasks

# Later run picks up remaining 3 tasks:
MERGE_COUNTER=0
# Tasks 48-50 merge in second close dispatch
```

This prevents runaway merge loops and allows batching closes across multiple dispatches.

---

## Example 10: State Reset After Close (WQ9)

**Before close:**
```yaml
# {WORK_ROOT}/state.md
phase: closing
sprint: 2
wip_item: T-TRI-02
wip_branch: feature/tri-02-heuristics
```

**After close completes:**
```yaml
# {WORK_ROOT}/state.md
phase: closing  # (next phase will be set by orchestrator)
sprint: 2
wip_item: null
wip_branch: null
```

**Verification step:**
```bash
WIP_ITEM=$(grep '^wip_item:' "{WORK_ROOT}/state.md" | awk '{print $2}')
WIP_BRANCH=$(grep '^wip_branch:' "{WORK_ROOT}/state.md" | awk '{print $2}')

if [ "$WIP_ITEM" = "null" ] && [ "$WIP_BRANCH" = "null" ]; then
  echo "State reset successful"
else
  echo "WARN: state wip_item/wip_branch not fully reset"
fi
```

This ensures orchestrator can detect sprint close completion and transition to next phase.

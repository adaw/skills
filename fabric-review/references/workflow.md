# Review Workflow — Detailed R1–R9 Checklist & Scoring

This document complements SKILL.md §7 (Postup) with comprehensive review dimensions, checklists, scoring anchors, and fix strategies.

## Table of Contents

1. [Objective Gates](#objective-gates)
2. [Diff Analysis](#diff-analysis)
3. [R1–R9 Checklists & Scoring](#r1-r9-checklists--scoring)
4. [Verdikt Logic](#verdikt-logic)
5. [Finding Severity Taxonomy](#finding-severity-taxonomy)
6. [Numeric Scoring Anchors (WQ10)](#numeric-scoring-anchors-wq10)
7. [Fix Strategy Per Finding Type](#fix-strategy-per-finding-type)
8. [Anti-Pattern Detection Bash](#anti-pattern-detection-bash)
9. [R8 Compliance Deep Dive](#r8-compliance-deep-dive)
10. [R9 Process Chain Validation](#r9-process-chain-validation)

---

## Objective Gates

### Run lint + format checks

On the WIP branch:

```bash
git checkout "${wip_branch}"

# Lint (optional, timeout 120s)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint}
  LINT_EXIT=$?
  if [ $LINT_EXIT -eq 124 ]; then
    LINT_RESULT="TIMEOUT"
  elif [ $LINT_EXIT -ne 0 ]; then
    LINT_RESULT="FAIL"
  else
    LINT_RESULT="PASS"
  fi
else
  LINT_RESULT="SKIPPED"
fi

# Format check (optional, timeout 120s)
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check}
  FMT_EXIT=$?
  if [ $FMT_EXIT -eq 124 ]; then
    FMT_RESULT="TIMEOUT"
  elif [ $FMT_EXIT -ne 0 ]; then
    FMT_RESULT="FAIL"
  else
    FMT_RESULT="PASS"
  fi
else
  FMT_RESULT="SKIPPED"
fi
```

### Gate failure diagnosis

If gate fails, determine scope of failure:

```bash
# Get changed files in task diff
git diff --name-only {main_branch}...{wip_branch} > /tmp/task-files.txt

# Distinguish task files vs pre-existing failures
TASK_ERRORS=$(timeout 60 {COMMANDS.lint} 2>&1 | while read error_line; do
  error_file=$(echo "$error_line" | awk -F: '{print $1}')
  if grep -q "$error_file" /tmp/task-files.txt; then
    echo "$error_line"
  fi
done)

if [ -n "$TASK_ERRORS" ]; then
  echo "GATE FAIL in task files (REWORK): $TASK_ERRORS"
  VERDICT="REWORK"
else
  echo "GATE FAIL in pre-existing files only (CLEAN verdict, create intake)"
  VERDICT="CLEAN"
  # Create intake item for pre-existing issues
fi
```

---

## Diff Analysis

Obtain full diff and categorize changes:

```bash
git fetch --all --prune 2>/dev/null || true

# Summary
git diff --stat {main_branch}...{wip_branch}

# Full diff (for manual review)
git diff {main_branch}...{wip_branch} > /tmp/review.diff

# Changed files
git diff --name-only {main_branch}...{wip_branch} > /tmp/changed-files.txt

# Categorize by type
echo "=== Code files ===" && grep '\.py$' /tmp/changed-files.txt
echo "=== Test files ===" && grep 'test_.*\.py$' /tmp/changed-files.txt
echo "=== Doc files ===" && grep -E '\.(md|rst|txt)$' /tmp/changed-files.txt
```

---

## R1–R9 Checklists & Scoring

### R1 Correctness (Logic, Edge Cases, Complexity)

**Checklist (POVINNÉ):**

- [ ] Logic correctly implements all AC (map 1:1 to requirements)
- [ ] Edge cases handled: None, empty, 0, negative, max_int, unicode, oversized input
- [ ] Off-by-one boundaries correct in loops and ranges (`<` vs `<=`, array indexing)
- [ ] Nesting ≤3 levels (if deeper, extract function)
- [ ] Cyclomatic complexity ≤10 per function (count if/elif/for/while/try/except/and/or)
- [ ] No dead code (unreachable branches, unused variables)
- [ ] Magic numbers replaced with named constants (MAX_PAYLOAD_SIZE, MIN_ITEMS, etc.)

**Finding format:**
```
| R1 | Missing None check in validate_email() line 120 | MEDIUM | Add guard: `if score is None: return 0.0` |
```

**Scoring (0–100 per finding):**
- 100% = All checks pass, zero logic bugs
- 80% = Minor edge case partially handled, one unused variable
- 50% = Logic bug exists (inverted condition, missing range check)
- 0% = Fundamentally broken, AC not met, crash risk

---

### R2 Security (Input Validation, Secrets, Auth)

**Checklist (POVINNÉ):**

- [ ] ALL user inputs validated at entry point (type, range, format, length)
- [ ] No `eval()`, `exec()`, `subprocess(shell=True)`, `pickle.loads()` without sanitization
- [ ] Secrets/credentials absent from code, logs, error messages
- [ ] SQL/NoSQL queries parameterized (never string concatenation)
- [ ] Path traversal prevented (realpath + prefix check for dynamic paths)
- [ ] Auth/authz check on EVERY new endpoint/handler (`@auth_required` decorator, etc.)

**Finding format:**
```
| R2 | Missing input validation on 'instance_id' (SQL injection risk) | CRITICAL | Use Pydantic validator or regex whitelist |
```

**Scoring (0–100):**
- 100% = All inputs validated, no eval/exec, secrets absent, queries parameterized, auth on all endpoints
- 80% = One optional field unvalidated OR one log may leak PII
- 50% = Unvalidated user input reaches core code, missing auth on one endpoint
- 0% = Code injection, credential exposure, no auth

---

### R3 Performance (Algorithms, I/O, Caching)

**Checklist (POVINNÉ):**

- [ ] Algorithm complexity ≤O(n log n) for hot paths (O(n²) = finding)
- [ ] No N+1 queries (DB/API calls in loops — use batch operations)
- [ ] I/O operations paginated/limited (no unbounded `read()` or `fetchall()`)
- [ ] Cache hit ratio: repeated computations cached in memory?
- [ ] Memory bounded: no unbounded collections (list.append in loop without limit)

**Finding format:**
```
| R3 | Nested loop O(n²) in dedup() line 150 | HIGH | Refactor: use set-based dedup, O(n) |
```

**Scoring (0–100):**
- 100% = ≤O(n log n), no N+1, I/O paginated, cache hits, memory bounded
- 80% = One O(n²) loop on non-critical path OR one potential N+1 in rare case
- 50% = O(n²) on hot path, N+1 detected, unbounded read()
- 0% = O(n³), infinite recursion, memory leak

---

### R4 Reliability (Error Handling, Timeouts, Retries)

**Checklist (POVINNÉ):**

- [ ] EVERY I/O call has specific `try/except {SpecificError}` (never bare `except:`)
- [ ] EVERY I/O call has timeout (explicit parameter or wrapper)
- [ ] Graceful degradation: if dependency fails, system continues (fail-open for LLMem)
- [ ] Resource cleanup: `with` statement for file/connection handles
- [ ] Retry logic has backoff + max_retries (never infinite retry)
- [ ] Error messages include context (what failed, with what input, why)

**Finding format:**
```
| R4 | Qdrant search() has no timeout (could hang forever) | HIGH | Add timeout from config.md COMMANDS.timeout_backend |
```

**Scoring (0–100):**
- 100% = All I/O has try/except + timeout, graceful degradation, resource cleanup, backoff retry
- 80% = Missing timeout on one I/O call OR bare except: on one handler
- 50% = Multiple I/O calls without error handling, infinite retry, no graceful fallback
- 0% = Crashes on transient error, resource leaks, deadlock risk

---

### R5 Testability (Test Quality, Coverage)

**Checklist (POVINNÉ):**

- [ ] Tests cover ALL AC (map 1:1, one test per AC item)
- [ ] ≥2 assertions per test (not just `assert True` or single assertion)
- [ ] Edge case tests: None, empty, oversized, boundary values
- [ ] Error path tests: `pytest.raises` for expected exceptions
- [ ] Test isolation: no shared mutable state between tests (no module-level fixtures)
- [ ] Mock boundaries: mock only external deps (storage, API), not internal modules
- [ ] No flaky tests: avoid `time.sleep()`, use `freezegun` or mocks for time

**Finding format:**
```
| R5 | Error path for invalid score type untested | HIGH | Add test_combine_score_invalid_input() |
```

**Scoring (0–100):**
- 100% = All AC tested, ≥2 assertions/test, edge cases, error paths, isolated, correct mocks, no flaky
- 80% = Missing one edge case test OR one test has only one assertion
- 50% = One AC untested, flaky tests with time.sleep, shared state
- 0% = No tests for core logic, impossible to debug

---

### R6 Maintainability (Naming, Size, DRY)

**Checklist (POVINNÉ):**

- [ ] Functions: `{verb}_{noun}` naming (describe_action, calculate_score, validate_input)
- [ ] Classes: `{Noun}{Role}` naming (CaptureService, HashEmbedder, InMemoryBackend)
- [ ] Functions ≤50 LOC (>50 = finding, recommend split)
- [ ] Single Responsibility: each function does ONE thing
- [ ] DRY: no copy-paste code (≥3 identical lines → extract function)
- [ ] Import ordering: stdlib → third-party → local (consistent)

**Finding format:**
```
| R6 | capture() is 120 LOC (should split into _validate, _triage, _store) | MEDIUM | Refactor into 3 functions |
```

**Scoring (0–100):**
- 100% = {verb}_{noun}, {Noun}{Role}, ≤50 LOC, single responsibility, no duplication, imports ordered
- 80% = One function 60 LOC OR one naming anomaly
- 50% = >100 LOC god function, multiple responsibilities, copy-paste block appears 3 times
- 0% = >200 LOC, unreadable, massive duplication, circular imports

---

### R7 Documentation (Docstrings, Comments, CHANGELOG)

**Checklist (POVINNÉ):**

- [ ] EVERY public function has docstring (≥1 sentence, Args/Returns/Raises sections)
- [ ] Complex logic has inline comment (WHY, not WHAT — code says what)
- [ ] README updated if user-facing change
- [ ] CHANGELOG updated for non-test code changes
- [ ] API spec updated if endpoint changes
- [ ] ADR created for architectural decisions

**Finding format:**
```
| R7 | Function combine_score() has no docstring | LOW | Add docstring with Args/Returns sections |
```

**Scoring (0–100):**
- 100% = All public functions have docstring, complex logic commented, README/CHANGELOG/API specs updated
- 80% = Missing one docstring on private function OR one complex block without comment
- 50% = Missing docstrings on >2 functions, stale README/CHANGELOG, API change not documented
- 0% = No docstrings, code completely unexplained, impossible to use

---

### R8 Compliance (ADR/Spec Validation)

**Checklist (POVINNÉ):**

1. Load `{WORK_ROOT}/decisions/INDEX.md` — extract all `Status: Accepted` or `Status: Active` ADRs
2. Load `{WORK_ROOT}/specs/INDEX.md` — extract all `Status: active` and `Status: draft` specs
3. For EACH changed file in diff, check against GOVERNANCE registry in `{WORK_ROOT}/config.md`:
   - Get `contract_modules` list for each ADR/spec
   - If changed file matches contract_modules, verify compliance
4. Porušení `accepted` ADR or `active` spec = **CRITICAL finding**
5. Porušení `draft` spec = **HIGH** (unless GOVERNANCE.specs.draft_enforcement says otherwise)

**Finding format:**
```
| R8 | Violates D0001 (secrets masking required) — stores plaintext | CRITICAL | Implement masking per D0001 pattern |
```

**Scoring (0–100):**
- 100% = Zero ADR/spec violations, all changed files match governance contracts
- 0% = Violates accepted ADR or active spec (supersede ADR required to fix)

---

### R9 Process Chain Validation (Process Contracts)

**Checklist (conditional — skip if process-map.md missing):**

1. Check if `{WORK_ROOT}/fabric/processes/process-map.md` exists
2. For EACH changed file in diff:
   - Extract process contracts from process-map.md (contract_modules lists)
   - If file matches contract_modules, flag as ALERT
   - Check process-chain test: `{WORK_ROOT}/tests/test_processes/test_{process_name}.py`
   - If test exists and fails, mark as **CRITICAL**
   - If test missing, mark as **HIGH**
3. Process-map missing = SKIPPED (fail-open)

**Finding format:**
```
| R9 | File triage/heuristics.py changed (contract_modules) but test_triage_and_recall.py FAILED | CRITICAL | Fix implementation to restore test PASS |
```

**Scoring (0–100):**
- 100% = No changed files in contract_modules OR changed files have passing process-chain tests
- 50% = Changed file in contract_modules, process-chain test missing
- 0% = Changed file in contract_modules, process-chain test FAILS

---

## Verdikt Logic

**CLEAN:**
- Gates PASS (or pre-existing issues only)
- Zero CRITICAL findings
- Test evidence exists and is PASS (or explained)
- All R1–R9 pass without blockers

**REWORK:**
- Gates fail in task files (task code must be clean)
- OR ≥1 CRITICAL finding that is opravitelný in current approach
- OR ≥3 HIGH findings (accumulation)

**REDESIGN:**
- ≥1 CRITICAL finding that requires fundamental change (architecture, new ADR/spec)
- OR task violates accepted ADR/active spec without quick fix
- OR rework_count ≥ max_rework_iters (3) — task needs different approach

---

## Finding Severity Taxonomy

| Severity | Definition | Verdict Impact | Examples |
|----------|-----------|-----------------|----------|
| **CRITICAL** | Blocks merge; security issue, data corruption risk, untested AC, breaking change, ambiguous behavior, ADR/spec violation | ≥1 CRITICAL (opravitelný) → REWORK; ≥1 CRITICAL (redesign) → REDESIGN | SQL injection, plaintext secrets, AC not met, process-chain test fails |
| **HIGH** | Should fix before merge; missing error handling for main flow, untested edge case for core logic, performance regress | ≥3 HIGH (no CRITICAL) → REWORK | Missing try/except on I/O, N+1 query, missing timeout |
| **MEDIUM** | Recommend fix, non-blocking; naming, minor refactor, missing doc comment, suboptimal but functional | Cosmetic improvements; contribute to score reduction but don't block | Function 60 LOC, missing docstring, suboptimal algorithm on non-critical path |
| **LOW** | Nice-to-have; stylistic, preference, minor improvements | Improvement suggestions only; score reduction minimal | Unused import, variable naming nitpick, whitespace |

---

## Numeric Scoring Anchors (WQ10)

Per dimension, average scores across findings to get final score (0–100):

```
Dimension R1: findings [100, 80, 50] → avg 76.67 → Grade: "R1: 76/100 (MEDIUM)"
```

### R1 Correctness

- **100%** = Zero logic bugs. All edge cases handled. Off-by-one boundaries correct. Nesting ≤3. Complexity ≤10. No dead code. Constants named.
- **80%** = Minor edge cases partially handled. Off-by-one potential in 1 boundary. Nesting 4 levels. Complexity 10–15. One unused variable.
- **50%** = Significant logic bug (inverted condition, missing range check, N+1 access). AC not fully met.
- **0%** = Fundamentally broken. Crash risk.

### R2 Security

- **100%** = All inputs validated at entry. No eval/exec/pickle. Secrets absent. Queries parameterized. Path traversal protected. Auth on all endpoints.
- **80%** = One optional field unvalidated OR one log may leak PII.
- **50%** = Unvalidated input reaches code. No SQL guards. Secrets in comments. Missing auth on one endpoint.
- **0%** = Code injection, credential exposure, no auth.

### R3 Performance

- **100%** = ≤O(n log n). No N+1. I/O paginated. Cache hits. Memory bounded.
- **80%** = One O(n²) loop on non-critical path OR one potential N+1 in rare case.
- **50%** = O(n²) on hot path. N+1 detected. Unbounded read().
- **0%** = O(n³), infinite recursion, memory leak.

### R4 Reliability

- **100%** = All I/O has try/except + timeout. Graceful degradation. Cleanup. Retry with backoff. Contextual errors.
- **80%** = Missing timeout on one call OR bare except: on one handler.
- **50%** = Multiple I/O without error handling. Infinite retry. No graceful fallback.
- **0%** = Crashes on error. Resource leaks. Deadlock.

### R5 Testability

- **100%** = All AC tested. ≥2 assertions/test. Edge cases. Error paths. Isolated. Correct mocks. No flaky.
- **80%** = Missing one edge case test OR one test has one assertion.
- **50%** = One AC untested. Flaky tests with sleep. Shared state.
- **0%** = No core tests. Impossible to debug.

### R6 Maintainability

- **100%** = {verb}_{noun}. {Noun}{Role}. ≤50 LOC. Single responsibility. DRY. Imports ordered.
- **80%** = One function 60 LOC OR one naming anomaly.
- **50%** = >100 LOC god function. Multiple responsibilities. Copy-paste block ×3.
- **0%** = >200 LOC, unreadable, circular imports.

### R7 Documentation

- **100%** = All public functions have docstring. Complex logic commented. README/CHANGELOG/API/ADR updated.
- **80%** = Missing one private function docstring OR one complex block without comment.
- **50%** = Missing docstrings on >2 functions. Stale README/CHANGELOG.
- **0%** = No docstrings. Code unexplained.

### R8 Compliance

- **100%** = Zero ADR/spec violations.
- **0%** = Violates accepted ADR or active spec.

### R9 Process Chain

- **100%** = No changed files in contract_modules OR process-chain tests PASS.
- **50%** = Changed file in contract_modules, test missing.
- **0%** = Changed file in contract_modules, test FAILS.

---

## Fix Strategy Per Finding Type

When verdict is REWORK, EVERY finding MUST include:

| Column | Description | Example |
|--------|-------------|---------|
| File:Line | Exact location | `src/llmem/models.py:45` |
| Dimension | R1–R9 | R2 |
| Severity | CRITICAL\|HIGH\|MEDIUM\|LOW | HIGH |
| Finding | Concrete problem (not vague) | Missing input validation on 'instance_id' (SQL injection risk) |
| Fix | Explicit steps (not "improve") | Use Pydantic UUID validator or regex check: `if not re.match(r'^[a-z0-9-]{36}$', instance_id): raise ValueError()` |
| Effort | Time estimate | 5min |

### Anti-patterns (FORBIDDEN):

- ❌ "Oprav bug v souboru X" (neříká JAK)
- ❌ "Přidej testy" (neříká KOLIK a JAKÉ)
- ❌ "Vylepši error handling" (neříká KTERÝ error)
- ✅ "V `scoring.py:45` přidej `try/except ValueError:` kolem `float(score)` s fallback `score=0.0` + test `test_scoring_invalid_input`"

### Per-finding-type fix strategies:

**R1 Logic bugs:**
```
src/llmem/recall/scoring.py:78 | R1 | CRITICAL | Missing None check before float() call
→ Add: if score is None: return 0.0; return float(score)
→ Add test: test_scoring_none_input()
→ Effort: 5 min
```

**R2 Missing validation:**
```
src/llmem/api/routes/recall.py:15 | R2 | CRITICAL | RecallQuery.query_text not validated for max length
→ Add Pydantic validator: @field_validator('query_text') def validate_length(v):
   if len(v) > 10000: raise ValueError('max 10k chars')
→ Test: test_recall_query_text_max_length()
→ Effort: 10 min
```

**R2 Secret/credential exposure:**
```
src/llmem/config.py:120 | R2 | CRITICAL | API key appears in debug logs
→ Replace print(environ) with {k: mask_secrets(v) for k, v in environ.items()}
→ Test: test_config_no_secrets_in_logs()
→ Effort: 15 min
```

**R3 O(n²) algorithm:**
```
src/llmem/recall/pipeline.py:150 | R3 | HIGH | Nested loop compares every candidate (O(n²) dedup)
→ Refactor: seen = set(); dedup = [x for x in candidates if not (h := hash(x)) in seen and not seen.add(h)]
→ Benchmark: test with 1000 items
→ Effort: 30 min
```

**R4 Missing error handling:**
```
src/llmem/api/routes/recall.py:25 | R4 | CRITICAL | backend.search() call has no try/except
→ Wrap: try: results = backend.search(...) except BackendError: log.warning(...); return graceful_empty_response()
→ Test: test_capture_backend_unavailable_still_logs()
→ Effort: 20 min
```

**R5 Untested code path:**
```
src/llmem/triage/patterns.py:200 | R5 | HIGH | Secret detection for Bearer tokens has no test
→ Add test: test_detect_secrets_bearer_token() with input "Bearer sk-1234"
→ Verify pattern matches real token examples
→ Effort: 15 min
```

**R6 God function:**
```
src/llmem/services/capture_service.py:30 | R6 | MEDIUM | capture() is 120 LOC (validation + triage + storage + logging mixed)
→ Refactor: _validate_input(), _triage_items(), _store_items() (each ~30 LOC)
→ Compose in capture(), update docstrings
→ Effort: 1 hour
```

**R6 Bad naming:**
```
src/llmem/scoring.py:50 | R6 | LOW | Function calc() unclear
→ Rename: calc() → calculate_importance_score() (2 call sites affected)
→ Update docstring
→ Effort: 5 min
```

**R7 Missing docstring:**
```
src/llmem/recall/scoring.py:78 | R7 | LOW | combine_score() has no docstring
→ Add: """Combine multi-layer recall scores with tier/scope/recency boosts.
   Args: base_score (float), tier_boost (float). Returns: float ≥0, ≤1."""
→ Effort: 5 min
```

**R8 ADR violation:**
```
src/llmem/triage/heuristics.py:50 | R8 | CRITICAL | Secrets stored plaintext, violates D0001
→ Either: (a) Implement masking per D0001 Section 3 patterns,
   OR (b) Create ADR-0006 "Plaintext Secrets MVP" with sunset date
→ Effort: 1–2 hours
```

**R9 Process contract violation:**
```
src/llmem/triage/heuristics.py | R9 | HIGH | File in contract_modules of int-capture-triage-store, but test_triage_and_recall.py FAILS
→ (a) Debug test: pytest tests/test_triage_and_recall.py -v
→ (b) Fix implementation to restore test PASS
→ (c) Verify backward compat with previous data
→ Effort: 30–60 min
```

---

## Anti-Pattern Detection Bash

Automated screening for R1–R9 violations:

```bash
#!/bin/bash
echo "=== R1-R9 ANTI-PATTERN DETECTION ==="

# Get changed files
git diff --name-only {main_branch}...{wip_branch} > /tmp/changed_files.txt

# R1: Logic bugs & edge cases
echo "=== R1: Correctness Anti-Patterns ==="
grep -rn "if.*==" /tmp/changed_files.txt | head -5 && echo "R1-CHECK: equality comparisons (verify off-by-one boundaries)"
grep -rn "if not\|if !" /tmp/changed_files.txt | head -5 && echo "R1-CHECK: inverted logic (verify logic is correct)"

# R2: Security
echo "=== R2: Security Anti-Patterns ==="
grep -rn "eval\|exec\|pickle\.loads" /tmp/changed_files.txt && echo "R2-FAIL: Found eval/exec/pickle (CRITICAL)"
grep -rn "password\|secret\|api_key\|token" /tmp/changed_files.txt | grep -i "=\s*['\"]" | grep -v "# \|mock\|test" && echo "R2-FAIL: Potential hardcoded secret"
grep -rn "request\.\|args\[" /tmp/changed_files.txt | grep -v "Pydantic\|BaseModel" && echo "R2-WARN: User input without validation guard visible"

# R3: Performance
echo "=== R3: Performance Anti-Patterns ==="
grep -rn "for.*in.*for.*in" /tmp/changed_files.txt && echo "R3-WARN: Nested loop (check O(n²))"
grep -rn "\.append\(" /tmp/changed_files.txt | grep -B 2 "for " && echo "R3-WARN: list.append in loop (pre-allocate or use set)"

# R4: Reliability
echo "=== R4: Reliability Anti-Patterns ==="
grep -rn "except:" /tmp/changed_files.txt && echo "R4-FAIL: Bare except: (specify exception type)"
grep -rn "request\.\|urllib\.\|socket\." /tmp/changed_files.txt | grep -v "timeout" && echo "R4-WARN: Network call without timeout guard"

# R5: Testability
echo "=== R5: Testability Anti-Patterns ==="
grep -rn "sleep(" tests/ --include='*.py' | grep -v "mock\|patch" && echo "R5-FAIL: sleep() in test (use mock time)"

# R6: Maintainability
echo "=== R6: Maintainability Anti-Patterns ==="
grep -rn "^def " /tmp/changed_files.txt | head -10 && echo "R6-CHECK: Review function sizes (target ≤50 LOC)"

# R7: Documentation
echo "=== R7: Documentation Anti-Patterns ==="
grep -rn "^def [^_]" /tmp/changed_files.txt | head -5 && echo "R7-CHECK: Verify public functions have docstrings"
git diff --name-only {main_branch}...{wip_branch} | grep -v test | grep -q . && ! git diff {main_branch}...{wip_branch} | grep -q "CHANGELOG" && echo "R7-WARN: Code changed but CHANGELOG not updated"

# R8: Compliance (ADR/Spec)
echo "=== R8: Compliance Anti-Patterns ==="
for adr_file in {WORK_ROOT}/decisions/*.md; do
  [ -f "$adr_file" ] && grep -q "Status: Accepted" "$adr_file" && echo "R8-CHECK: Verify no conflicts with $(basename "$adr_file")"
done

# R9: Process Chain
echo "=== R9: Process Chain Anti-Patterns ==="
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
[ -f "$PROCESS_MAP" ] && echo "R9-CHECK: Verify changed files don't violate process contracts" || echo "R9-SKIP: process-map.md missing (fail-open)"

echo "=== DETECTION COMPLETE ==="
```

---

## R8 Compliance Deep Dive

### Load ADR & Spec registries

```bash
echo "=== R8 COMPLIANCE CHECK ==="

# Step 1: Extract all accepted ADRs
echo "Accepted ADRs:"
grep -A 10 "^## " {WORK_ROOT}/decisions/INDEX.md | grep -E "Status: (Accepted|Active)" -B 2 | grep "^##"

# Step 2: Extract all active specs
echo "Active Specs:"
grep -A 10 "^## " {WORK_ROOT}/specs/INDEX.md | grep -E "Status: active" -B 2 | grep "^##"

# Step 3: Load GOVERNANCE registry
echo "Governance Registry:"
grep -A 20 "^GOVERNANCE:" {WORK_ROOT}/config.md | head -40
```

### Check changed files against contracts

```bash
git diff --name-only {main_branch}...{wip_branch} > /tmp/changed_files.txt

# For each ADR, extract contract_modules
for adr_file in {WORK_ROOT}/decisions/*.md; do
  [ -f "$adr_file" ] || continue
  grep -q "Status: Accepted" "$adr_file" || continue

  ADR_NAME=$(basename "$adr_file" .md)
  echo "Checking ADR: $ADR_NAME"

  # Extract contract_modules
  MODULES=$(awk '/^contract_modules:/,/^[^ ]/' "$adr_file" | grep '^\s*-' | sed 's/.*"\(.*\)".*/\1/')

  # Check if any changed file matches
  while read module; do
    while IFS= read -r changed_file; do
      if [[ "$changed_file" == "$module" ]]; then
        echo "MATCH: $changed_file is contract_module of $ADR_NAME"
        echo "→ Verify compliance with $ADR_NAME spec and acceptance criteria"
      fi
    done < /tmp/changed_files.txt
  done <<< "$MODULES"
done
```

---

## R9 Process Chain Validation

### Load process-map and check contracts

```bash
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"

if [ ! -f "$PROCESS_MAP" ]; then
  echo "INFO: process-map.md missing — R9 SKIPPED (fail-open)"
  R9_STATUS="SKIPPED"
  exit 0
fi

echo "=== R9 PROCESS CHAIN VALIDATION ==="

git diff --name-only {main_branch}...{wip_branch} > /tmp/changed_files.txt

while IFS= read -r changed_file; do
  [ -z "$changed_file" ] && continue

  # For each process in process-map, check contract_modules
  PROCESSES=$(grep "^[a-zA-Z_-]*:" "$PROCESS_MAP" | sed 's/:$//')

  for process in $PROCESSES; do
    # Extract contract_modules for this process
    CONTRACT_MODULES=$(awk "/^$process:/,/^[a-zA-Z]/ {print}" "$PROCESS_MAP" \
      | grep -A 100 "contract_modules:" \
      | grep '^\s*- "' \
      | sed 's/^\s*- "//' | sed 's/".*//')

    # Check if changed_file matches any contract_module
    if echo "$CONTRACT_MODULES" | grep -qF "$changed_file"; then
      echo "ALERT: Changed file '$changed_file' is in process '$process' contract"

      # Check process-chain test
      PROCESS_TEST="{WORK_ROOT}/tests/test_processes/test_${process}.py"
      if [ -f "$PROCESS_TEST" ]; then
        timeout 60 python -m pytest "$PROCESS_TEST" -v
        TEST_EXIT=$?
        if [ $TEST_EXIT -ne 0 ]; then
          echo "CRITICAL: Process-chain test FAILED: $PROCESS_TEST"
          R9_STATUS="CRITICAL"
        fi
      else
        echo "HIGH: Process-chain test missing: $PROCESS_TEST"
        R9_STATUS="HIGH"
      fi
    fi
  done
done < /tmp/changed_files.txt

echo "R9 Status: $R9_STATUS"
```

---

## End of Workflow Reference

See `examples.md` for concrete review report examples with LLMem data.

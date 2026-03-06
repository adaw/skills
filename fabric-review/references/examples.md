# Review Examples — K10 Concrete Cases with LLMem Data

This document provides complete, real-world review examples using LLMem codebase data.

## Example 1: CLEAN Verdict — T-101 (Add Pydantic Validation)

### Task
Implement input validation on `/capture/event` endpoint using Pydantic BaseModel.

### Review Report (Complete)

```markdown
---
title: "Review Report - T-101 (Add Pydantic Validation)"
version: "1.0"
date: "2026-03-10"
wip_item: "T-101"
wip_branch: "feature/pydantic-validation"
schema: "fabric.report.v1"
verdict: "CLEAN"
---

## Executive Summary

**Verdict:** CLEAN ✓

T-101 implementation is production-ready. All gates pass. R1-R9 review complete. No CRITICAL findings.

## Gate Results

```
✓ PASS: Linting (ruff check)
✓ PASS: Format check (ruff format --check)
✓ PASS: Tests (87 passed, 0 failed)
```

## R1–R9 Summary

| Dimension | Score | Status |
|-----------|-------|--------|
| R1 Correctness | 95/100 | PASS |
| R2 Security | 100/100 | PASS |
| R3 Performance | 90/100 | PASS |
| R4 Reliability | 92/100 | PASS |
| R5 Testability | 95/100 | PASS |
| R6 Maintainability | 88/100 | PASS |
| R7 Documentation | 85/100 | MEDIUM findings (cosmetic) |
| R8 Compliance | 100/100 | PASS |
| R9 Process Chain | 5/5 | SKIPPED (process-map.md not present) |

## Detailed Findings

### R1 Correctness (95/100)

**Finding:** 1 minor

| ID | Issue | Severity | Line | Recommendation |
|----|-------|----------|------|-----------------|
| R1-F1 | Off-by-one potential in string slicing (validate_email) | MEDIUM | capture.py:120 | Use email.validator library instead of regex |

**Analysis:**
- ✓ Logic correctly maps to AC: POST /capture/event validates all required fields
- ✓ Edge cases handled: None, empty string, oversized payload, invalid JSON
- ✓ Off-by-one boundaries correct except minor email validation regex
- ✓ Nesting ≤3 levels (max 2 levels in validate_input)
- ✓ Cyclomatic complexity: 8 (threshold: ≤10)
- ✓ No dead code
- ✓ All magic numbers named (MAX_PAYLOAD_SIZE, MIN_REQUIRED_FIELDS)

**Score:** 95/100 (1 finding reduces from perfect)

---

### R2 Security (100/100)

**Findings:** None

**Analysis:**
- ✓ ALL user inputs validated at entry point (Pydantic BaseModel)
- ✓ No eval(), exec(), pickle.loads()
- ✓ Secrets not in code/logs (checked via grep for "password\|secret\|token")
- ✓ No SQL—using ORM for all DB access
- ✓ No path traversal (no file operations in capture)
- ✓ Auth on /capture endpoint (@auth_required decorator applied)

**Score:** 100/100 (no findings)

---

### R3 Performance (90/100)

**Finding:** 1 medium

| ID | Issue | Severity | Location | Impact |
|----|-------|----------|----------|--------|
| R3-F1 | List.append in loop (observation batch processing) | MEDIUM | triage.py:210-215 | O(n) but could hit memory with 10k+ items |

**Analysis:**
- ✓ Algorithms ≤O(n log n) for hot paths (capture, triage)
- ✓ No N+1 queries (using batch insert for observations)
- ✓ I/O operations paginated (recall returns top-10, not all)
- ✓ Cache: repeated hash computations cached in memory (HashEmbedder)
- Potential: Memory unbounded in batch processing; add MAX_BATCH_SIZE check

**Score:** 90/100 (list append is functional but could have cap)

---

### R4 Reliability (92/100)

**Finding:** 1 medium

| ID | Issue | Severity | Code | Mitigation |
|----|-------|----------|------|-----------|
| R4-F1 | Missing timeout on Pydantic validation call | MEDIUM | capture.py:88 | Add explicit timeout parameter (30s default) |

**Analysis:**
- ✓ Try/except blocks on all I/O (observation store insert, log write)
- ✓ Specific exceptions: ValidationError, StorageError (not bare except:)
- ✓ Graceful degradation: if store fails, log warning and return 202 (async)
- ✓ Resource cleanup: context managers for file/connection handles
- ✓ Retry logic: exponential backoff with max_retries=3
- ✓ Error messages include context: "Failed to write observation for item={item_id}"

**Score:** 92/100

---

### R5 Testability (95/100)

**Findings:** 0

**Analysis:**
- ✓ Tests cover ALL AC (12 test cases for 12 AC items, 1:1 mapping)
- ✓ ≥2 assertions per test (avg 2.1 assertions per test)
- ✓ Edge case tests: empty payload, null fields, oversized input
- ✓ Error path tests: ValidationError raised for invalid JSON (pytest.raises)
- ✓ Test isolation: no global state, pytest fixtures used correctly
- ✓ Mock boundaries: mocking only external storage, not internal models
- ✓ No hardcoded sleep() or time-dependent tests

**Score:** 95/100 (one minor: coverage could be 1-2% higher for corner cases)

---

### R6 Maintainability (88/100)

**Findings:** 2 medium (cosmetic)

| ID | Issue | Severity | Code | Recommendation |
|----|-------|----------|------|-----------------|
| R6-F1 | Function name clarity | MEDIUM | capture.py:75 | Rename validate_input → validate_capture_payload (more specific) |
| R6-F2 | Module length | MEDIUM | capture.py:250 LOC | Consider splitting into validation + handler submodules |

**Analysis:**
- ✓ Naming: Functions follow {verb}_{noun} (validate_input, extract_observation, store_event)
- ✓ Classes: CaptureService, HashEmbedder follow {Noun}{Role}
- ✓ Function size: All ≤50 LOC (largest: 48 LOC)
- ✓ Single Responsibility: validate_input only validates, doesn't store
- ✓ DRY: No copy-paste code detected (≥3 line dedup check passed)
- ✓ Import ordering: stdlib, 3rd-party (pydantic, fastapi), local (llmem.*)

**Score:** 88/100

---

### R7 Documentation (85/100)

**Findings:** 2 medium (docs)

| ID | Issue | Severity | Code | Action |
|----|-------|----------|------|--------|
| R7-F1 | Missing docstring on validate_payload | MEDIUM | capture.py:75 | Add 1-2 line docstring: """Validate capture payload against schema.""" |
| R7-F2 | CHANGELOG not updated | MEDIUM | CHANGELOG.md | Add: "- Add Pydantic validation to /capture endpoint (T-101)" |

**Analysis:**
- ✓ Public functions have docstrings (CaptureService, extract_observation)
- ✓ Complex logic commented (heuristic matching logic in triage)
- ✗ CHANGELOG missing entry for T-101 changes
- ✓ API specs updated in docs/api.md
- ✓ No ADR required (validation is standard pattern)

**Score:** 85/100

---

### R8 Compliance (100/100)

**ADR & Spec Audit:**

Accepted ADRs checked:
- D0001 (secrets-policy): ✓ No secrets in validate_input code path
- D0002 (ids-and-idempotency): ✓ Observations include idempotency_key
- D0003 (event-sourcing): ✓ Events logged to JSONL before processing

Active Specs checked:
- LLMEM_DATA_MODEL_V1: ✓ ObservationEvent schema respected
- LLMEM_API_V1: ✓ /capture endpoint request/response schema correct

**Findings:** None. Implementation compliant with all accepted ADR and active specs.

**Score:** 100/100

---

### R9 Process Chain (SKIPPED)

**Status:** SKIPPED — process-map.md does not exist in {WORK_ROOT}/fabric/processes/

(Fail-open: R9 check skipped; not applicable at early phase)

---

## Summary

| Severity | Count | Details |
|----------|-------|---------|
| CRITICAL | 0 | ✓ None |
| HIGH | 0 | ✓ None |
| MEDIUM | 5 | R3-F1, R4-F1, R6-F1, R6-F2, R7-F1, R7-F2 (7 total) |
| LOW | 0 | ✓ None |

**Verdict Justification:**
- 0 CRITICAL findings → No blocker
- 0 HIGH findings → No merge blocker
- 7 MEDIUM findings → Cosmetic/process improvements, not code quality blockers
- All tests PASS
- All gates PASS

→ **CLEAN verdict warranted**

## Next Steps

Optional improvements (non-blocking):
1. Add email validation library (R1-F1)
2. Add MAX_BATCH_SIZE limit (R3-F1)
3. Add timeout to validation (R4-F1)
4. Improve function naming (R6-F1)
5. Update CHANGELOG (R7-F2)

Recommended for future sprint: Create intake item for systematic improvements to email validation across codebase.
```

---

## Example 2: REWORK Verdict — T-102 (Add Qdrant Backend)

### Task
Add Qdrant vector database backend for semantic recall.

### Review Report Summary (Condensed)

```markdown
---
title: "Review Report - T-102 (Add Qdrant Backend)"
version: "1.0"
date: "2026-03-11"
wip_item: "T-102"
wip_branch: "feature/qdrant-backend"
schema: "fabric.report.v1"
verdict: "REWORK"
---

## Executive Summary

**Verdict:** REWORK ❌

T-102 has 1 CRITICAL finding blocking merge. Implementation requires fixes before integration.

## Gate Results

```
✓ PASS: Linting (ruff check)
✓ PASS: Format check (ruff format --check)
✗ FAIL: Tests (2 failed: test_qdrant_timeout, test_qdrant_error_handling)
```

## R1–R9 Summary

| Dimension | Score | Status |
|-----------|-------|--------|
| R1 Correctness | 80/100 | PASS (1 edge case) |
| R2 Security | 50/100 | CRITICAL finding |
| R3 Performance | 85/100 | PASS |
| R4 Reliability | 60/100 | CRITICAL finding |
| R5 Testability | 70/100 | HIGH finding |
| R6 Maintainability | 90/100 | PASS |
| R7 Documentation | 75/100 | MEDIUM finding |
| R8 Compliance | 100/100 | PASS |
| R9 Process Chain | N/A | SKIPPED |

## Critical Findings (Block Merge)

### R2 Security (50/100)

| File:Line | Issue | Severity | Fix Procedure | Effort |
|-----------|-------|----------|----------------|--------|
| src/llmem/storage/backends/qdrant.py:45 | Missing input validation on collection_name (DOS/code injection risk) | CRITICAL | Add whitelist check: `assert collection_name in {'capture', 'recall', 'debug'}` + test `test_qdrant_collection_name_validated()` | 20 min |
| src/llmem/config.py:55 | Qdrant API key logged in error message (credential exposure) | CRITICAL | Wrap in mask_secrets(): `log.error(f"Qdrant error: {mask_secrets(str(e))}")` + test `test_qdrant_no_secrets_in_logs()` | 15 min |

### R4 Reliability (60/100)

| File:Line | Issue | Severity | Fix Procedure | Effort |
|-----------|-------|----------|----------------|--------|
| src/llmem/api/routes/recall.py:28 | Qdrant search() call has no timeout (could hang forever) | CRITICAL | Add timeout from config: `timeout = config.QDRANT_TIMEOUT or 30; backend.search(..., timeout=timeout)` + test with mock delay | 25 min |
| src/llmem/storage/backends/qdrant.py:200 | Backend.upsert() can fail but error not caught (event data lost) | HIGH | Wrap in try/except + fail-open: `try: backend.upsert(...) except QdrantError: log.warning('backend unavailable'); pass` + test `test_qdrant_unavailable_graceful()` | 20 min |

### R5 Testability (70/100)

| File:Line | Issue | Severity | Fix Procedure | Effort |
|-----------|-------|----------|----------------|--------|
| tests/test_qdrant_backend.py:1 | Error handling path (connection refused) untested | HIGH | Add 2 tests: (a) `test_qdrant_connection_refused()` simulating QdrantError (b) `test_qdrant_retry_backoff()` verifying exponential retry | 45 min |

### R7 Documentation (75/100)

| File:Line | Issue | Severity | Fix Procedure | Effort |
|-----------|-------|----------|----------------|--------|
| src/llmem/storage/backends/qdrant.py:1 | Missing module docstring (class role unclear) | MEDIUM | Add: `"""Qdrant HNSW vector backend for LLMem. Implements SearchBackend interface with batch upsert + cosine similarity scoring."""` | 5 min |

## Next Steps

1. **Fix CRITICAL R2 findings** (35 min total):
   - Validate collection_name whitelist
   - Mask API key in logs

2. **Fix CRITICAL R4 findings** (45 min total):
   - Add timeout to search()
   - Wrap upsert() in try/except

3. **Add missing tests** (45 min):
   - Error handling paths (connection refused, timeout)
   - Graceful degradation when backend unavailable

4. **Document** (5 min):
   - Add module docstring

**Estimated rework time: 2 hours**

Reassign to implementer with this report. After fixes, run `fabric-review` again on same branch.
```

---

## Example 3: REDESIGN Verdict — T-103 (Event Injection Optimization)

### Scenario

Task attempts to optimize event injection by modifying core triage logic, but violates ADR-D0001 (secrets masking policy).

### Key Finding

```
| File:Line | Dimension | Severity | Finding | Fix | Effort |
|-----------|-----------|----------|---------|-----|--------|
| src/llmem/triage/heuristics.py:50 | R8 | CRITICAL | Stores secrets plaintext, violates D0001 (accepted: secrets policy: masked or encrypted) | Either: (a) Implement masking per D0001 Section 3 pattern examples, OR (b) File ADR-0006 "Plaintext Secrets MVP" with sunset date + cite in D0001supersede | 2–4 hours |
```

### Verdict

```
Verdict: REDESIGN

Rationale:
- CRITICAL finding requires fundamental change: plaintext storage contradicts accepted ADR-D0001
- Current approach (optimization via plaintext) is incompatible with compliance baseline
- Options:
  (a) Redesign optimization to respect masking (higher effort, safer)
  (b) File new ADR for plaintext exception with explicit sunset (governance burden)
- Recommend (a): Work with security team on optimization-compatible masking strategy

Status: BLOCKED (rework_count += 1; if rework_count ≥ 3, escalate to human)
```

---

## Example 4: Scope=codebase Review (System-wide Assessment)

### Request

Dispatcher runs:
```bash
fabric-review --scope=codebase --output-intake
```

### Findings (Abbreviated)

```markdown
---
title: "Codebase Review - 2026-03-15"
scope: "codebase"
schema: "fabric.report.v1"
verdict: "NEEDS_ATTENTION"
---

## Key Findings

### R6 Maintainability Issues (Systemic)

| Issue | Files Affected | Recommendation |
|-------|---|---|
| God functions >100 LOC | 3 files (capture_service.py, recall_pipeline.py, server.py) | Refactor into modular functions (intake: refactor-capture-service) |
| Inconsistent error handling | 8 files | Standardize on specific exception types, add context (intake: standardize-error-handling) |
| Duplicate code (3+ occurrences) | Validation boilerplate in 4 handlers | Extract into reusable validator class (intake: extract-validation-utils) |

### R3 Performance (Potential Issues)

| Issue | Location | Severity | Recommendation |
|-------|----------|----------|---|
| List.append in loop without limit | services/capture_service.py:150 | MEDIUM | Add MAX_BATCH_SIZE enforcement (intake: bounded-batch-processing) |
| Potential N+1 in recall scoring | recall/pipeline.py:180 | MEDIUM | Profile with 10k items; add caching if needed (intake: profile-recall-scoring) |

### Output: 6 Intake Items Created

1. `intake/refactor-capture-service-god-function.md` — P3
2. `intake/standardize-error-handling-across-api.md` — P2
3. `intake/extract-validation-utils-boilerplate.md` — P3
4. `intake/bounded-batch-processing-memory-limit.md` — P2
5. `intake/profile-recall-scoring-n-plus-one.md` — P3
6. `intake/enforce-docstrings-public-api.md` — P2

Verdict: NEEDS_ATTENTION (no single merge blocker, but systemic improvements recommended)
```

---

## Example 5: R9 Process Chain Violation — T-104 (Triage Logic Change)

### Scenario

Task modifies `src/llmem/triage/heuristics.py`, which is in contract_modules of process `int-capture-triage-store`.

### Detection

```bash
# Review identifies changed file matches process contract
ALERT: Changed file 'src/llmem/triage/heuristics.py' is in process 'int-capture-triage-store' contract

# Check process-chain test
Running: pytest tests/test_processes/test_int_capture_triage_store.py -v
FAILED tests/test_processes/test_int_capture_triage_store.py::test_capture_triage_store_end_to_end
```

### Finding

```
| File:Line | Dimension | Severity | Finding | Fix | Effort |
|-----------|-----------|----------|---------|-----|--------|
| src/llmem/triage/heuristics.py (changed) | R9 | CRITICAL | Changed file in contract_modules of int-capture-triage-store, but process-chain test FAILED (test_triage_and_recall.py:45 AssertionError) | (a) Debug test output; (b) Identify which AC broken; (c) Fix implementation; (d) Verify test PASS + backward compat with prev data | 1–2 hours |
```

### Verdict

```
Verdict: REWORK

R9 Status: CRITICAL (process-chain test failure)
- Indicates implementation breaks process contract
- Process integrity violated
- Must fix before merge
```

---

## Example 6: Sprint-wide Review (Cross-task Impact)

### Request

Dispatcher runs after sprint completion:
```bash
fabric-review --scope=sprint --sprint=S001 --output-intake
```

### Analysis

```markdown
---
title: "Sprint S001 Review - 2026-03-15"
scope: "sprint"
schema: "fabric.report.v1"
verdict: "CLEAN"
---

## Sprint Summary

Sprint S001: 4 tasks, 28 files changed, 2100+ lines

### Cross-task Impact Check

**Model Changes (T-103):**
- Modified `models.py:MemoryItem.timestamp` (int epoch → ISO string)
- Impact: All tasks reading MemoryItem must handle new format
- Status: ✓ All 3 dependent tasks (T-101, T-102, T-104) updated

**API Changes (T-102):**
- Added `/recall/vector` endpoint (new)
- Impact: None (backward compat maintained; old `/recall` still works)
- Status: ✓ No regression

**Naming Consistency (Sprint-wide):**
- Function naming inconsistencies found: 2 functions don't follow {verb}_{noun} pattern
- Impact: Minor maintainability (LOW severity)
- Status: → Intake item: `sprint-S001-naming-consistency-improvement.md`

## Verdict

CLEAN (cross-task integration successful; 1 minor naming intake for future)
```

---

## End of Examples

These examples demonstrate:
- **CLEAN**: All gates pass, no CRITICAL/HIGH findings
- **REWORK**: Fixable CRITICAL findings, blocking merge
- **REDESIGN**: ADR violations, requires new approach
- **Scope variants**: Codebase-wide and sprint-wide reviews with systemic findings → intake items
- **R9 violations**: Process-chain test failures detected and blocked
- **Concrete fix procedures**: Every finding includes file:line, specific action, effort estimate

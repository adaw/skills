# fabric-test — Příklady a katalog

## Příklad: Vyplnený test report (PASS case)

```markdown
---
schema: fabric.report.v1
kind: test
run_id: "run-20260310-093847"
created_at: "2026-03-10T09:38:47Z"
status: PASS
version: "1.0"
---

# Test Report — T-101 (Add Pydantic Validation)

## Souhrn

Spuštěny testy pro feature T-101: 87 passed, 0 failed, 0 errors, 5 skipped. Coverage 78.3% pro core modules (target ≥60%: PASS). Test/Code LOC ratio 65% (target ≥50%: PASS). Žádné flaky testy detekováno. Všechna acceptance criteria splněna.

## Test Results

| Metrika | Hodnota |
|---------|---------|
| Tests Passed | 87 |
| Tests Failed | 0 |
| Tests Errored | 0 |
| Tests Skipped | 5 |
| Total Tests | 92 |
| Coverage (Overall) | 78.3% |
| Coverage (Core Modules) | 82% |

**Command:** `pytest -q --cov=src/llmem --cov-report=term-missing --tb=short`

**Output:**
```
tests/test_capture.py::test_capture_with_valid_input PASSED
tests/test_capture.py::test_capture_with_invalid_json PASSED
tests/test_capture.py::test_capture_with_missing_fields PASSED
tests/test_capture.py::test_capture_pydantic_validation PASSED [NEW]
tests/test_triage.py::test_triage_deterministic_ids PASSED
tests/test_triage.py::test_triage_secret_masking PASSED
...
87 passed, 5 skipped in 12.4s
```

## Coverage Analysis

**Modified Modules (T-101 scope):**
| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| api/routes/capture.py | 12 | 92% | ✓ PASS |
| api/validation.py | 8 | 95% | ✓ PASS |
| models.py | 15 | 85% | ✓ PASS |
| triage/heuristics.py | 28 | 81% | ✓ PASS |
| storage/backends/inmemory.py | 18 | 76% | ✓ PASS |
| recall/pipeline.py | 9 | 68% | ✓ PASS |

**Overall Project Coverage:** 78.3% (target: ≥60% → PASS)

**Key coverage areas:**
- Capture validation: All Pydantic validations trigger on invalid input ✓
- Edge cases: Empty JSON, missing fields, null values, oversized payloads ✓
- Triage flow: Validation errors propagate correctly without data corruption ✓
- Backward compatibility: Existing endpoints unaffected ✓

## Test Execution Details

**Duration:** 12.4 seconds (all tests ran in parallel)

**Test Isolation:** ✓ Verified
- No global state modifications detected
- pytest fixtures used correctly (not hardcoded)
- Database mock reset between tests

**Performance:** ✓ Normal
- Slowest test: test_triage_deterministic_ids (87ms)
- Slowest test: test_capture_with_invalid_json (45ms)

## Flakiness Detection

Re-ran all 87 tests 3 times:
- Run 1: 87 PASS
- Run 2: 87 PASS
- Run 3: 87 PASS

**Flaky tests:** 0 (all consistent)

## Test/Code LOC Ratio

- **Test LOC:** 3,240 lines (tests/)
- **Code LOC:** 5,000 lines (src/llmem)
- **Ratio:** 65% (target: ≥50% → PASS)

## Acceptance Criteria Validation

T-101 AC checklist:
- [x] POST /capture/event validates input with Pydantic
- [x] Invalid JSON rejected with 400 status
- [x] Missing required fields rejected with clear error message
- [x] No data corruption on validation error
- [x] Backward compatibility: Existing endpoints unaffected

**All AC met:** ✓ PASS

## Notes

All 87 tests passed without regression. Coverage improved to 78.3% (baseline 45%), meeting target ≥60%. Key modules (capture, validation) at 92-95% coverage. Test/Code LOC ratio 65% indicates healthy test investment. No flakiness detected across 3 reruns. No test isolation issues. Ready for review.

```

---

## Příklad: Vyplnený test report (FAIL case)

```markdown
---
schema: fabric.report.v1
kind: test
run_id: "run-20260311-140522"
created_at: "2026-03-11T14:05:22Z"
status: FAIL
version: "1.0"
---

# Test Report — T-102 (Add Rate Limiting)

## Souhrn

Spuštěny testy pro feature T-102: 83 passed, 4 failed, 0 errors, 5 skipped. Coverage 71% (target ≥60%: PASS). Však 4 testy selhaly v rate_limiter modulu — root cause: chybějící pytest fixture initialization. Žádné intake items vytvořeny; oprava snadná.

## Test Results

| Metrika | Hodnota |
|---------|---------|
| Tests Passed | 83 |
| Tests Failed | 4 |
| Tests Errored | 0 |
| Tests Skipped | 5 |
| Total Tests | 92 |
| Coverage (Overall) | 71% |

**Command:** `pytest -q --cov=src/llmem --cov-report=term-missing --tb=short`

## Failures

All 4 failures in single module: `api/middleware/rate_limiter.py`

| Test | File:Line | Error Type | Message |
|------|-----------|-----------|---------|
| test_rate_limiter_increment | test_rate_limiter.py:45 | AssertionError | expected calls to mock_redis.incr(), got 0 |
| test_rate_limiter_reset | test_rate_limiter.py:78 | AttributeError | 'NoneType' object has no attribute 'reset' |
| test_rate_limiter_threshold | test_rate_limiter.py:102 | AssertionError | expected RateLimitError on 101st request, got success |
| test_rate_limiter_concurrent | test_rate_limiter.py:145 | RuntimeError | redis client not initialized in fixture |

## Root Cause Analysis

**Heuristic Match:** Single Module Failure

Root cause: Rate limiter tests require `mock_redis` fixture, but fixture is defined in separate conftest.py with incorrect import path. Tests fail before reaching assertions.

**Evidence:**
```
ImportError: cannot import name 'mock_redis' from 'tests.fixtures'
Failing module: api/middleware/rate_limiter.py (4 failures)
All failures: fixture/setup issues, not logic errors
```

## Coverage Analysis

| Module | Tests | Coverage |
|--------|-------|----------|
| api/middleware/rate_limiter.py | 4 | 0% (not reached) |
| api/routes/capture.py | 12 | 91% |
| api/routes/recall.py | 8 | 85% |

Overall: 71% (target: ≥60% → PASS for other modules, but rate_limiter uncovered)

## Notes

4 tests failed due to fixture setup issue (mock_redis import path). Root cause isolated to rate_limiter module — no regression in capture/recall/triage. Fix: correct import path in conftest.py to `from tests.mocks import mock_redis`. Other 83 tests all passed. No flaky tests. Recommend: fix import, re-run gate-test, expect PASS.

## Next Action

1. Fix conftest.py: `from tests.mocks import mock_redis` (not from tests.fixtures)
2. Re-run gate-test
3. Expect: 87 passed, 0 failed (rate_limiter tests now covered)

```

---

## Příklad: Test report — TIMEOUT case

```markdown
---
schema: fabric.report.v1
kind: test
run_id: "run-20260312-164500"
created_at: "2026-03-12T16:45:00Z"
status: WARN
version: "1.0"
---

# Test Report — T-103 (Add Vector Embeddings) — TIMEOUT

## Souhrn

Testy pro feature T-103 dosáhly timeout po 300s. Poslední úspěšný test: test_embedding_model_load (skončil v ~150s). Zbývajících 15 testů neběželo. Root cause: embedding model initialization je neoptimalizovaná (model.load() nepoužívá caching).

## Test Results

| Metrika | Hodnota |
|---------|---------|
| Tests Started | 92 |
| Tests Completed | 77 |
| Tests Timed Out | 15 |
| Coverage (Partial) | 64% |

**Exit Code:** 124 (timeout after 300s)

**Last Completed Test:** `test_embedding_model_load` (150.2s)

**First Timed Out Test:** `test_embedding_similarity_cosine` (never completed)

## Root Cause

**Type:** Performance regression (not logic error)

Embedding model fixture loads full model on every test. No caching:
```python
@pytest.fixture
def embedding_model():
    return EmbeddingModel.load("model-v1")  # 15s per test, not cached
    # Total: 15s × 20 tests = 300s timeout

# Should be:
@pytest.fixture(scope="session")
def embedding_model():  # Cache across session
    ...
```

## Intake Item Created

- **ID:** intake/test-timeout-20260312-embedding.md
- **Title:** E2E test timeout: optimize embedding model fixture caching
- **Recommendation:** Add pytest fixture caching (scope="session") + implement lazy loading

## Notes

Tests did not fail logic-wise — execution just too slow. 77 tests completed (64% coverage). Root cause: missing fixture caching. Recommend: add @pytest.fixture(scope="session") to embedding_model, re-run. Expected: all 92 tests complete in ~60s.

## Next Action

1. Modify test fixture: add `scope="session"` + lazy load
2. Re-run gate-test
3. Expect: 92 passed, 0 failed, ~60s total

```

---

## Katalog: Root Cause Templates

### Template 1: Single Module Import Error

```markdown
## Root Cause

Single module failure (API: `test_models.py`, 3 failures):
- import error in models.py:1 (missing dependency)
- all tests in that module affected

## Evidence
```
ImportError: cannot import name 'ValidationError'
```

## Next Action
1. Check models.py imports
2. Install missing dependency or fix import path
3. Re-run tests
```

### Template 2: Spanning Failures (Shared Dependency)

```markdown
## Root Cause

Failures span capture + triage (shared dependency):
- 2 failures in test_capture.py
- 3 failures in test_triage.py
- common root: models.py schema change

## Evidence
```
AssertionError: ObservationEvent schema changed (expected 'metadata', got none)
```

## Next Action
1. Check models.py for schema breaking changes
2. Update test fixtures to match new schema
3. Consider backward compatibility wrapper
4. Re-run tests
```

### Template 3: Isolated Test Logic Failure

```markdown
## Root Cause

Single test failure (isolated bug):
- test_capture_with_null_tags fails
- other 86 tests pass
- logic error in feature code: null handling

## Evidence
```
AssertionError: assert None == []
```

## Next Action
1. Check capture.py null handling for 'tags' field
2. Fix logic: `tags = tags or []`
3. Re-run tests
```

### Template 4: Test Infrastructure Issue

```markdown
## Root Cause

Multiple failures, all with same error:
- all failures: "conftest fixture not found"
- pytest infrastructure issue, not code issue

## Evidence
```
fixture 'mock_redis' not found
```

## Next Action
1. Check conftest.py exists in test root
2. Verify fixture definitions present
3. Run: `pytest --fixtures | grep mock_redis`
4. Re-run tests
```

---

## Checklist: Common Test Mistakes to Avoid

- [ ] Empty test (no assertions) → add assertions
- [ ] Test sleeps hardcoded `time.sleep(1)` → use mocks or fixtures
- [ ] Test uses random without seed → add seed or mock
- [ ] Test modifies global state → use fixtures to isolate
- [ ] Test calls external API → mock requests
- [ ] Test timeout not set → add `@pytest.mark.timeout(30)`
- [ ] Test isolation issues → run tests in random order: `pytest --random-order`
- [ ] Coverage target missing → add cov-fail-under flag
- [ ] Notes section empty → VIOLATION, must add interpretation

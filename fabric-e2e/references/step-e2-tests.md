# E2: Test Execution (Detailed Procedure)

**Co:** Run the E2E test suite against the live server. This phase executes all tests, captures results, and determines pass/fail status.

## Full Implementation

### 1. Set environment for test discovery:
```bash
export LLMEM_E2E_URL="http://localhost:$E2E_PORT"
export LLMEM_E2E_HOME="$E2E_HOME"
cd "$CODE_ROOT"  # cd to project root for test discovery
```

### 2. Run pytest with timeout and output capture:
```bash
mkdir -p reports
LOG_FILE="reports/e2e-$(date +%Y-%m-%d).log"

timeout 300 pytest tests/e2e/ -v --tb=short 2>&1 | tee "$LOG_FILE"
E2E_EXIT=$?

if [ $E2E_EXIT -eq 124 ]; then
  echo "Tests timed out after 300s"
fi
```

### 3. Parse and count test results from output:
```bash
PASSED=$(grep -c "PASSED" "$LOG_FILE" || echo 0)
FAILED=$(grep -c "FAILED" "$LOG_FILE" || echo 0)
ERRORS=$(grep -c "ERROR" "$LOG_FILE" || echo 0)
TOTAL=$((PASSED + FAILED + ERRORS))
echo "Results: $PASSED passed, $FAILED failed, $ERRORS errors (Total: $TOTAL)"
```

### 4. If FILTER environment variable is set, run only matching tests:
```bash
if [ -n "$FILTER" ]; then
  timeout 300 pytest tests/e2e/ -k "$FILTER" -v --tb=short 2>&1 | tee -a "$LOG_FILE"
fi
```

## Target E2E Test Structure (10 Categories)

| Test File | Tests | Coverage | Minimum |
|-----------|-------|----------|---------|
| `test_health_live.py` | /healthz returns 200, server info | Health endpoint | ≥1 test |
| `test_api_live.py` | POST /capture/event, GET /recall, GET /memories | HTTP API surface | ≥3 tests |
| `test_capture_live.py` | Event capture, JSONL logging, idempotency | Capture pipeline | ≥2 tests |
| `test_triage_live.py` | Secret detection, PII hashing, deterministic IDs | Triage heuristics | ≥2 tests |
| `test_recall_live.py` | Candidate scoring, budget, dedup, XML injection | Recall pipeline | ≥2 tests |
| `test_memory_live.py` | Write → Read → Context retrieval flow | End-to-end memory flow | ≥2 tests |
| `test_batch_live.py` | Batch capture endpoint, bulk insert | Batch operations | ≥1 test |
| `test_error_live.py` | Invalid JSON, missing fields, type errors, edge cases | Error handling | ≥3 tests |
| `test_backend_live.py` | InMemory and Qdrant (if running) backend switching | Backend abstraction | ≥1 test |
| `test_injection_live.py` | XML CDATA escaping, budget truncation, preamble | Injection format | ≥1 test |

**Total: ≥18 E2E tests recommended; minimum gate: ≥8 tests must pass**

## Success Criteria

**Minimum:** All tests run without timeout, at least 8 tests passing, test output logged, results parsed.

## Anti-patterns to Avoid

- ❌ Don't run pytest without timeout — 300s max per test suite
- ❌ Don't swallow test output — always `tee` to log file
- ❌ Don't skip error/edge case tests — they validate robustness
- ❌ Don't hardcode URLs — use LLMEM_E2E_URL environment variable
- ❌ Don't ignore timeout exit code (124) — log it as a failure
- ❌ Don't run tests from the wrong directory — cd to CODE_ROOT first
- ❌ Don't run without `-v --tb=short` — need verbose output for debugging

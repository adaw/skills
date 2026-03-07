---
name: fabric-e2e
description: "Run end-to-end tests against a live running LLMem system to validate the full stack: API, CLI, capture pipeline, triage, recall with scoring, storage, and error handling. Final quality gate before close confirming observations flow correctly."
---
<!-- built from: builder-template -->

# Fabric E2E: End-to-End Testing

## §1 Účel

Run end-to-end tests against a live running LLMem system. Validates that the full stack works: API, CLI, capture pipeline, triage, recall with scoring, memory storage, error handling, and edge cases. Without E2E tests, unit tests pass but the system may fail in integration. E2E is the final quality gate before close: it confirms that observations flow from capture → triage → storage, and that recall returns budgeted, scored results with proper XML injection.

## §2 Protokol

```bash
# START
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "e2e" --event start

# ... E2E test execution ...

# END
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "e2e" --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/e2e-{YYYY-MM-DD}.md"
```

All major checkpoints (preconditions pass, server started, tests begin, server stopped) are logged with timestamp and status.

## §3 Preconditions (bash code)

1. **config.md exists**: Project config file with commands, backend settings
2. **state.md exists**: Current state/checkpoint file
3. **CODE_ROOT exists**: Root of the project (usually `$PWD`)
4. **tests/e2e/ directory exists**: E2E test suite with ≥8 tests
5. **Port is free**: `! lsof -i :${E2E_PORT:-8099}`
6. **pip install done**: Project is installable: `pip show llmem` or similar
7. **Optional**: .env file for API keys (fallback to mock/in-memory if missing)

**Dependency chain**: `fabric-implement` → `fabric-test` → `fabric-e2e`

## §4 Vstupy

**Povinné:**
- config.md (provides CODE_ROOT, COMMANDS.serve, COMMANDS.test, LLMEM_BACKEND)
- state.md (current state checkpoint)
- CODE_ROOT (absolute path to project root)
- COMMANDS from config (serve, test commands)

**Volitelné:**
- .env (API keys; fallback to mock provider if missing)
- Previous e2e reports in reports/e2e-*.md (for regression baseline)
- Environment variables: E2E_PORT (default 8099), LLMEM_BACKEND (default inmemory), LLMEM_DATA_DIR (default temp)

## §5 Výstupy

**Primární:**
- `reports/e2e-{YYYY-MM-DD}.md` — Structured report (fabric.report.v1 schema)

**Vedlejší:**
- `reports/e2e-{YYYY-MM-DD}.log` — Raw stdout/stderr from server and tests
- Intake items for each failed test (fed into next sprint backlog)

---

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

---

## §6 FAST PATH

Before full execution, perform quick checks:
1. Run `backlog-index` to confirm environment is ready
2. Run `governance-index` to check for blockers
3. Port check: `lsof -i :${E2E_PORT:-8099}` (must not be in use)
4. Check previous e2e report (if exists) for regression baseline
5. If preconditions fail, STOP and report why

## §7 Postup — 5 steps (E1-E5)

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="implementation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-e2e. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### Path Traversal Guard (K7: Input Validation)

```bash
# Path traversal guard — reject any input containing ".."
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic path inputs:
# validate_path "$TEST_FILE"
# validate_path "$TEMP_DIR"
```

### K2 Fix: E2E Test Run Counter

```bash
MAX_TEST_RUNS=${MAX_TEST_RUNS:-20}
TEST_RUN_COUNTER=0

# Validate MAX_TEST_RUNS is numeric (K2 tight validation)
if ! echo "$MAX_TEST_RUNS" | grep -qE '^[0-9]+$'; then
  MAX_TEST_RUNS=20
  echo "WARN: MAX_TEST_RUNS not numeric, reset to default (20)"
fi
```

When iterating through E2E test cases:
```bash
while read -r test_case; do
  TEST_RUN_COUNTER=$((TEST_RUN_COUNTER + 1))

  # Numeric validation of counter (K2 strict check)
  if ! echo "$TEST_RUN_COUNTER" | grep -qE '^[0-9]+$'; then
    TEST_RUN_COUNTER=0
    echo "WARN: TEST_RUN_COUNTER corrupted, reset to 0"
  fi

  if [ "$TEST_RUN_COUNTER" -ge "$MAX_TEST_RUNS" ]; then
    echo "WARN: max E2E test runs reached ($TEST_RUN_COUNTER/$MAX_TEST_RUNS)"
    break
  fi
  # ... run test
done
```

### 7.1) E1: Setup

**Co:** Start the live LLMem system in a clean temporary environment with isolated state. This phase creates the sandbox, configures the server, and waits for readiness.

**Jak (detailed):**

1. **Create isolated temporary home directory:**
   ```bash
   export E2E_HOME=$(mktemp -d)
   export E2E_PORT=${E2E_PORT:-8099}
   echo "E2E_HOME=$E2E_HOME, E2E_PORT=$E2E_PORT"
   ```

2. **Check for API keys in .env (fallback to mock):**
   ```bash
   if [ -f .env ]; then
     source .env
   else
     echo "No .env found, using mock provider"
   fi
   # Set backend (default inmemory for E2E)
   export LLMEM_BACKEND=${LLMEM_BACKEND:-inmemory}
   export LLMEM_DATA_DIR="$E2E_HOME"
   ```

3. **Extract server command from config.md or use default:**
   ```bash
   # From config: {COMMANDS.serve} typically:
   # "uvicorn llmem.api.server:app --host 127.0.0.1 --port {PORT}"
   SERVE_CMD="uvicorn llmem.api.server:app --host 127.0.0.1 --port $E2E_PORT --reload"
   ```

4. **Start server in background with output capture:**
   ```bash
   mkdir -p "$E2E_HOME/logs"
   $SERVE_CMD > "$E2E_HOME/logs/server.log" 2>&1 &
   SERVER_PID=$!
   echo "Server PID: $SERVER_PID"
   sleep 1  # Give OS time to start process
   ```

5. **Health check wait loop (max 30s):**
   ```bash
   HEALTH_OK=0
   for i in $(seq 1 30); do
     if curl -sf http://localhost:$E2E_PORT/healthz > /dev/null 2>&1; then
       HEALTH_OK=1
       echo "Server healthy after $i seconds"
       break
     fi
     echo "Waiting for server... ($i/30)"
     sleep 1
   done

   if [ $HEALTH_OK -eq 0 ]; then
     echo "FAILED: Server health check timeout after 30s"
     kill -9 $SERVER_PID 2>/dev/null
     cat "$E2E_HOME/logs/server.log"
     exit 1
   fi
   ```

**Minimum:** Server running, health check `/healthz` returning 200, PID captured, isolated data directory set.

**Anti-patterns:**
- ❌ Don't use production data directory — always use temp (`mktemp -d`)
- ❌ Don't use default port 8080 — use 8099 to avoid conflicts with development servers
- ❌ Don't skip health wait loop — server needs 5-15s to start up
- ❌ Don't forget to capture PID and output — needed for teardown and debugging
- ❌ Don't skip `sleep 1` after `&` — process needs time to fork
- ❌ Don't hardcode backend — use LLMEM_BACKEND from config

### 7.2) E2: Test Execution

**Co:** Run the E2E test suite against the live server. This phase executes all tests, captures results, and determines pass/fail status.

**Jak:**

1. **Set environment for test discovery:**
   ```bash
   export LLMEM_E2E_URL="http://localhost:$E2E_PORT"
   export LLMEM_E2E_HOME="$E2E_HOME"
   cd "$CODE_ROOT"  # cd to project root for test discovery
   ```

2. **Run pytest with timeout and output capture:**
   ```bash
   mkdir -p reports
   LOG_FILE="reports/e2e-$(date +%Y-%m-%d).log"

   timeout 300 pytest tests/e2e/ -v --tb=short 2>&1 | tee "$LOG_FILE"
   E2E_EXIT=$?

   if [ $E2E_EXIT -eq 124 ]; then
     echo "Tests timed out after 300s"
   fi
   ```

3. **Parse and count test results from output:**
   ```bash
   PASSED=$(grep -c "PASSED" "$LOG_FILE" || echo 0)
   FAILED=$(grep -c "FAILED" "$LOG_FILE" || echo 0)
   ERRORS=$(grep -c "ERROR" "$LOG_FILE" || echo 0)
   TOTAL=$((PASSED + FAILED + ERRORS))
   echo "Results: $PASSED passed, $FAILED failed, $ERRORS errors (Total: $TOTAL)"
   ```

4. **If FILTER environment variable is set, run only matching tests:**
   ```bash
   if [ -n "$FILTER" ]; then
     timeout 300 pytest tests/e2e/ -k "$FILTER" -v --tb=short 2>&1 | tee -a "$LOG_FILE"
   fi
   ```

**Target E2E test structure (10 test categories adapted to LLMem):**

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

**Minimum:** All tests run without timeout, at least 8 tests passing, test output logged, results parsed.

**Anti-patterns:**
- ❌ Don't run pytest without timeout — 300s max per test suite
- ❌ Don't swallow test output — always `tee` to log file
- ❌ Don't skip error/edge case tests — they validate robustness
- ❌ Don't hardcode URLs — use LLMEM_E2E_URL environment variable
- ❌ Don't ignore timeout exit code (124) — log it as a failure
- ❌ Don't run tests from the wrong directory — cd to CODE_ROOT first
- ❌ Don't run without `-v --tb=short` — need verbose output for debugging

### 7.3) E3: Capture & Logs

**Co:** Collect all logs, server output, and diagnostic data for the report. This phase gathers evidence of what happened during the test run.

**Jak:**

1. **Capture server stdout/stderr to log file:**
   ```bash
   cp "$E2E_HOME/logs/server.log" "reports/e2e-$(date +%Y-%m-%d)-server.log"
   ```

2. **If available, fetch event/observation log from server:**
   ```bash
   curl -s "http://localhost:$E2E_PORT/memories?limit=100" \
     > "reports/e2e-$(date +%Y-%m-%d)-memories.json" 2>/dev/null || true
   ```

3. **Extract failed test details from pytest output:**
   ```bash
   LOG_FILE="reports/e2e-$(date +%Y-%m-%d).log"
   grep -A 10 "FAILED\|ERROR" "$LOG_FILE" > "reports/e2e-$(date +%Y-%m-%d)-failures.txt" || true
   ```

4. **Capture system diagnostics (optional but useful):**
   ```bash
   {
     echo "=== Test Run Diagnostics ==="
     echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
     echo "Backend: $LLMEM_BACKEND"
     echo "Port: $E2E_PORT"
     echo "Data dir: $E2E_HOME"
     echo "Python: $(python --version)"
     echo "Pytest: $(pytest --version)"
   } >> "$LOG_FILE"
   ```

**Minimum:** Combined log file with server output + test results, failed test details extracted, diagnostics captured.

**Anti-patterns:**
- ❌ Don't discard logs on success — logs are useful for regression analysis and performance tracking
- ❌ Don't lose stderr from server — capture both stdout and stderr
- ❌ Don't run tests without logging output — you'll lose debugging info
- ❌ Don't forget to copy logs before teardown — temp directory will be deleted

### 7.4) E4: Teardown

**Co:** Gracefully stop the server and clean up all resources. This phase ensures no orphan processes or leftover files block the next test run.

**Jak:**

1. **Graceful shutdown with TERM signal:**
   ```bash
   if [ -n "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
     echo "Sending SIGTERM to $SERVER_PID..."
     kill -TERM $SERVER_PID

     # Wait up to 10s for graceful shutdown
     for i in $(seq 1 10); do
       if ! kill -0 $SERVER_PID 2>/dev/null; then
         echo "Server stopped after $i seconds"
         break
       fi
       sleep 1
     done
   fi
   ```

2. **Force kill if necessary:**
   ```bash
   if kill -0 $SERVER_PID 2>/dev/null; then
     echo "Server did not stop gracefully, sending SIGKILL..."
     kill -9 $SERVER_PID 2>/dev/null || true
     sleep 1
   fi
   ```

3. **Clean temporary directory:**
   ```bash
   if [ -d "$E2E_HOME" ]; then
     rm -rf "$E2E_HOME"
     echo "Cleaned $E2E_HOME"
   fi
   ```

4. **Verify port is free:**
   ```bash
   if ! lsof -i :$E2E_PORT > /dev/null 2>&1; then
     echo "Port $E2E_PORT is free"
   else
     echo "WARNING: Port $E2E_PORT still in use after teardown"
     lsof -i :$E2E_PORT
   fi
   ```

**Minimum:** Server process terminated, temp directory deleted, port verified free.

**Anti-patterns:**
- ❌ Don't skip teardown on test failure — ALWAYS teardown, even if tests fail
- ❌ Don't use `kill -9` first — try SIGTERM for clean shutdown
- ❌ Don't leave orphan processes — they will interfere with next test run
- ❌ Don't leave temp directories — they waste disk and cause confusion
- ❌ Don't skip port verification — next test run may fail if port is still bound
- ❌ Don't skip this step even if tests passed — cleanup is mandatory

### 7.5) E5: Report

**Co:** Generate structured E2E report with pass/fail summary, timing, and regression comparison. This phase produces the artifact that documents the test run.

**Jak:**

1. **Compile test results and timing:**
   ```bash
   LOG_FILE="reports/e2e-$(date +%Y-%m-%d).log"
   REPORT_FILE="reports/e2e-$(date +%Y-%m-%d).md"

   PASSED=$(grep -c "passed" "$LOG_FILE" || echo 0)
   FAILED=$(grep -c "failed" "$LOG_FILE" || echo 0)
   ERRORS=$(grep -c "error" "$LOG_FILE" || echo 0)
   TOTAL=$((PASSED + FAILED + ERRORS))
   DURATION=$(grep "in.*s" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+\.[0-9]+" || echo "0")
   ```

2. **Compare with previous e2e report for regression detection:**
   ```bash
   PREV_REPORT=$(ls -t reports/e2e-*.md 2>/dev/null | grep -v "$(date +%Y-%m-%d)" | head -1)
   REGRESSIONS=0

   if [ -n "$PREV_REPORT" ]; then
     PREV_PASSED=$(grep "tests_passed:" "$PREV_REPORT" | grep -oE "[0-9]+")
     if [ "$PREV_PASSED" -gt "$PASSED" ]; then
       REGRESSIONS=$((PREV_PASSED - PASSED))
       echo "WARNING: $REGRESSIONS tests regressed since last run"
     fi
   fi
   ```

3. **Generate report in standard fabric.report.v1 format:**
   ```bash
   cat > "$REPORT_FILE" << EOF
   # E2E Report $(date +%Y-%m-%d)

   **Status:** $([ $FAILED -eq 0 ] && echo "PASS" || echo "FAIL")

   ## Summary
   - **Tests:** $PASSED/$TOTAL passed
   - **Failed:** $FAILED
   - **Errors:** $ERRORS
   - **Duration:** ${DURATION}s
   - **Backend:** $LLMEM_BACKEND
   - **Provider:** $([ -n "$API_KEY" ] && echo "real" || echo "mock")
   - **Regressions:** $REGRESSIONS

   ## Test Categories
   - Health: ✓ (e2e server healthz passing)
   - Capture: $(grep -q "test_capture_live" "$LOG_FILE" && echo "✓" || echo "✗")
   - Triage: $(grep -q "test_triage_live" "$LOG_FILE" && echo "✓" || echo "✗")
   - Recall: $(grep -q "test_recall_live" "$LOG_FILE" && echo "✓" || echo "✗")
   - Memory: $(grep -q "test_memory_live" "$LOG_FILE" && echo "✓" || echo "✗")
   - Batch: $(grep -q "test_batch_live" "$LOG_FILE" && echo "✓" || echo "✗")
   - Error: $(grep -q "test_error_live" "$LOG_FILE" && echo "✓" || echo "✗")
   - Injection: $(grep -q "test_injection_live" "$LOG_FILE" && echo "✓" || echo "✗")

   ## Logs
   - Full test output: \`e2e-$(date +%Y-%m-%d).log\`
   - Server output: \`e2e-$(date +%Y-%m-%d)-server.log\`
   - Failed tests: \`e2e-$(date +%Y-%m-%d)-failures.txt\`

   EOF
   ```

4. **Create intake items for each FAILED test:**
   ```bash
   if [ $FAILED -gt 0 ]; then
     grep "FAILED" "$LOG_FILE" | while read line; do
       TEST_NAME=$(echo "$line" | cut -d' ' -f1)
       echo "Intake: E2E test $TEST_NAME failed in $REPORT_FILE" >> reports/intake.txt
     done
   fi
   ```

**Report template (schema: fabric.report.v1):**

```
kind: e2e
status: {PASS|WARN|FAIL}
timestamp: {ISO8601}
duration_seconds: {N}
tests_total: {N}
tests_passed: {N}
tests_failed: {N}
backend: {inmemory|qdrant}
provider: {mock|real}
regressions: {N}
```

**Minimum:** Report file created with pass/fail counts, duration, provider info, log file reference. Intake items created for failures.

**Anti-patterns:**
- ❌ Don't report PASS if any test failed — report WARN or FAIL
- ❌ Don't skip regression comparison — failing tests that previously passed are critical
- ❌ Don't forget intake items — failures must be tracked for next sprint
- ❌ Don't hardcode paths — use environment variables
- ❌ Don't lose test output — reference log files in report

## §8 Quality Gates

**Gate 1: Server Health** — Health check `/healthz` must pass within 30s
- PASS: Server returns 200 and is responding
- FAIL: Timeout or server error → STOP and capture startup log

**Gate 2: Minimum Tests** — At least 8 E2E tests must exist and run
- PASS: ≥8 tests found in tests/e2e/
- FAIL: <8 tests → intake item "Insufficient E2E test coverage"

**Gate 3: Zero Crashes** — Server must not crash during test execution
- PASS: Server PID is still alive after tests complete
- FAIL: Server crashed → intake item with core dump or error log

**Gate 4: Teardown Complete** — Port must be free and temp dir cleaned
- PASS: `lsof -i :${E2E_PORT}` returns nothing, temp dir deleted
- WARN: Port still in use but tests passed (may indicate slow shutdown)

**Gate 5: Test Success Minimum** — At least 75% of tests must pass
- PASS: `passed >= total * 0.75`
- WARN: 50-75% passing (some issues but not critical)
- FAIL: <50% passing (major integration problem)

## §9 Report

Standard fabric.report.v1 schema:

```yaml
kind: e2e
phase: implementation
step: e2e
status: [PASS|WARN|FAIL]
timestamp: 2026-03-05T14:30:00Z
duration_seconds: 125
tests_total: 18
tests_passed: 18
tests_failed: 0
tests_errors: 0
backend: inmemory
provider: mock
regressions: 0
blockers: []
log_file: reports/e2e-2026-03-05.log
report_file: reports/e2e-2026-03-05.md
```

## §10 Self-check (12 items)

**Existence:**
- [ ] Report exists: `reports/e2e-{YYYY-MM-DD}.md`
- [ ] Log file exists: `reports/e2e-{YYYY-MM-DD}.log`
- [ ] Server process terminated: `! kill -0 $SERVER_PID 2>/dev/null`
- [ ] Temp directory cleaned: `[ ! -d "$E2E_HOME" ]`

**Quality:**
- [ ] All test categories represented (≥5 of 8 categories in output)
- [ ] Each failed test has intake item
- [ ] Regression comparison done (if previous report exists)
- [ ] Report has pass/fail counts, duration, provider info

**Invariants:**
- [ ] Port `${E2E_PORT}` is free: `! lsof -i :${E2E_PORT}`
- [ ] No orphan processes: `ps aux | grep -c "llmem\|uvicorn"` should be baseline
- [ ] Protocol log has START and END: check protocol_log.py
- [ ] No production data directory was used: all state is in temp `$E2E_HOME`

## §11 Failure Handling

| Phase | Error | Action |
|-------|-------|--------|
| Preconditions | Port `${E2E_PORT}` busy | STOP with message: "port ${E2E_PORT} in use; run `lsof -i :${E2E_PORT}` to find process" |
| Preconditions | tests/e2e/ missing | STOP: "No E2E tests found; create tests/e2e/test_*.py files" |
| Preconditions | pip install failed | STOP: "pip install -e '.[dev]' failed; check dependencies" |
| E1 Setup | Server won't start | STOP + capture startup log + intake item "Server failed to start" |
| E1 Setup | Health timeout (30s) | STOP + capture log + intake item "Server health check timeout" |
| E2 Tests | Test timeout (300s) | WARN + kill tests + capture partial results + intake item "E2E tests timeout" |
| E2 Tests | All tests fail | Report FAIL + intake item for each failure |
| E2 Tests | Some tests fail | Report WARN + intake item per failure + continue |
| E3 Logs | Can't read server output | WARN + continue (logs are diagnostic, not blocking) |
| E4 Teardown | Server won't stop (TERM) | Send SIGKILL + WARN in report |
| E4 Teardown | Port still busy after SIGKILL | WARN + print `lsof -i :${E2E_PORT}` output + manual cleanup instruction |
| E5 Report | Can't parse pytest output | WARN + write manual results based on stderr |

**Fallback behaviors:**
- If server won't start: check startup log for "Address already in use" or similar
- If health check times out: increase timeout to 60s and retry once
- If tests timeout: run a subset with FILTER=test_health_live to confirm system is alive
- If teardown hangs: log warning but don't block; next test will fail on port check (early gate)

## §12 Metadata

```yaml
metadata:
  phase: implementation
  step: e2e
  skill_type: fabric-builder
  may_modify_state: false
  may_modify_backlog: false
  may_modify_code: false  # e2e is read-only — only runs tests, doesn't fix
  may_create_intake: true
  depends_on: [fabric-implement, fabric-test]
  feeds_into: [fabric-review, fabric-close]
  timeout_seconds: 600  # 10 min total: setup 2min + tests 5min + teardown 1min + report 2min
  port_required: 8099
  backend_required: inmemory|qdrant
  min_tests_required: 8
  min_tests_pass_percentage: 75
```

---

**Final notes:**
- This skill is **read-only** on the codebase — it runs tests, never modifies code or fixes bugs
- Server startup happens in isolated temp directory; no production data is touched
- All output is logged; logs are preserved for debugging even if tests pass
- Regression detection compares with previous e2e reports automatically
- Failure handling is defensive: phases can fail independently; teardown always happens
- Health gate is non-negotiable: if server doesn't start, stop immediately


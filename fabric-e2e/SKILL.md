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

### K2: E2E Test Run Counter
```bash
# K2: Counter initialization
MAX_E2E_TESTS=${MAX_E2E_TESTS:-50}
E2E_TEST_COUNTER=0

# K2: Numeric validation
if ! echo "$MAX_E2E_TESTS" | grep -qE '^[0-9]+$'; then
  MAX_E2E_TESTS=50
  echo "WARN: MAX_E2E_TESTS not numeric, reset to default (50)"
fi

# K5: Read config
E2E_PORT=$(grep 'E2E.port:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
E2E_PORT=${E2E_PORT:-8099}
E2E_TIMEOUT=$(grep 'E2E.timeout:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
E2E_TIMEOUT=${E2E_TIMEOUT:-120}
```

### K1: Phase validation — e2e runs in implementation
```bash
# K1: Phase validation — e2e runs in implementation
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "implementation" ]; then
  echo "STOP: fabric-e2e requires phase=implementation, current=$CURRENT_PHASE"
  exit 1
fi

# K7: Path traversal guard
for VAR in "{WORK_ROOT}" "{CODE_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in $VAR"
    exit 1
  fi
done

# K6: Dependency enforcement — test report MUST exist
if ! ls "{WORK_ROOT}/reports/test-"*.md 1>/dev/null 2>&1; then
  echo "STOP: No test report found — fabric-test must run before fabric-e2e"
  exit 1
fi
```

### Validation Guards

See `references/guards-and-validation.md` for:
- State Validation (K1: State Machine)
- Path Traversal Guard (K7: Input Validation)
- K2 Fix: E2E Test Run Counter

### 7.1) E1: Setup

**Co:** Start the live LLMem system in a clean temporary environment with isolated state. This phase creates the sandbox, configures the server, and waits for readiness.

**Jak:** See `references/step-e1-setup.md` for full implementation.

**Summary:** Create isolated temp directory, set environment variables, extract server command, start server in background, run health check (max 30s).

**Minimum:** Server running, health check `/healthz` returning 200, PID captured, isolated data directory set.

### 7.2) E2: Test Execution

**Co:** Run the E2E test suite against the live server. This phase executes all tests, captures results, and determines pass/fail status.

**Jak:** See `references/step-e2-tests.md` for full implementation.

**Summary:** Set test environment, run pytest with 300s timeout, parse results, optionally filter tests.

**Test Coverage:** 10 test categories (health, API, capture, triage, recall, memory, batch, error, backend, injection). Minimum 8 tests; target 18.

**Minimum:** All tests run without timeout, at least 8 tests passing, test output logged, results parsed.

### 7.3) E3: Capture & Logs

**Co:** Collect all logs, server output, and diagnostic data for the report. This phase gathers evidence of what happened during the test run.

**Jak:** See `references/step-e3-logs.md` for full implementation.

**Summary:** Copy server logs, fetch observation log from server, extract failed test details, capture system diagnostics.

**Minimum:** Combined log file with server output + test results, failed test details extracted, diagnostics captured.

### 7.4) E4: Teardown

**Co:** Gracefully stop the server and clean up all resources. This phase ensures no orphan processes or leftover files block the next test run.

**Jak:** See `references/step-e4-teardown.md` for full implementation.

**Summary:** Send SIGTERM (graceful), then SIGKILL if needed, remove temp directory, verify port is free.

**Minimum:** Server process terminated, temp directory deleted, port verified free.

### 7.5) E5: Report

**Co:** Generate structured E2E report with pass/fail summary, timing, and regression comparison. This phase produces the artifact that documents the test run.

**Jak:** See `references/step-e5-report.md` for full implementation.

**Summary:** Compile test results and timing, compare with previous reports (regression detection), generate fabric.report.v1 report, create intake items for failures.

**Minimum:** Report file created with pass/fail counts, duration, provider info, log file reference. Intake items created for failures.

### K10: Inline Example — LLMem E2E Test Run

**Input:** Server started on port 8099, 18 E2E tests from tests/e2e/ (health, API, capture, triage, recall, memory, batch, error, backend, injection categories), test execution with 300s timeout.
**Output:** All 18 tests PASS, health check /healthz=200 in 1.2s, capture→triage→recall chain verified (POST /capture/event, verify /recall returns result), injection XML output validated, report e2e-2026-03-06.md shows tests_total: 18, tests_passed: 18, duration: 95s, backend: inmemory, regressions: 0.

### K10: Anti-patterns (s detekcí)
```bash
# A1: Running E2E without server health check — Detection: ! grep -E 'healthz.*200' {e2e-report}
# A2: E2E test suite has <8 tests — Detection: find tests/e2e -name 'test_*.py' | wc -l < 8
# A3: Orphan server process after E2E fails — Detection: lsof -i :{E2E_PORT} still shows uvicorn/llmem after run
# A4: Temp directory not cleaned → disk leaks — Detection: ls -la /tmp | grep e2e_ | wc -l > previous_run_count
```

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

See `references/failure-handling-reference.md` for detailed failure matrix and fallback behaviors.

**Quick reference:**
- Port busy: STOP with diagnostic message
- Missing tests: STOP with action item
- Server won't start: STOP + capture log
- Tests fail: Report FAIL + create intake items
- Teardown hangs: WARN but don't block

## §12 — Metadata (pro fabric-loop orchestraci)

> Read-only skill — runs tests, never modifies code. Timeout 600s. Port 8099. Min 8 tests, 75% pass rate.

```yaml
depends_on: [fabric-implement]
feeds_into: []
phase: implementation
lifecycle_step: e2e
touches_state: false
touches_git: false
estimated_ticks: 1
idempotent: true
fail_mode: fail-open
```

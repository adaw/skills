# E3: Capture & Logs (Detailed Procedure)

**Co:** Collect all logs, server output, and diagnostic data for the report. This phase gathers evidence of what happened during the test run.

## Full Implementation

### 1. Capture server stdout/stderr to log file:
```bash
cp "$E2E_HOME/logs/server.log" "reports/e2e-$(date +%Y-%m-%d)-server.log"
```

### 2. If available, fetch event/observation log from server:
```bash
curl -s "http://localhost:$E2E_PORT/memories?limit=100" \
  > "reports/e2e-$(date +%Y-%m-%d)-memories.json" 2>/dev/null || true
```

### 3. Extract failed test details from pytest output:
```bash
LOG_FILE="reports/e2e-$(date +%Y-%m-%d).log"
grep -A 10 "FAILED\|ERROR" "$LOG_FILE" > "reports/e2e-$(date +%Y-%m-%d)-failures.txt" || true
```

### 4. Capture system diagnostics (optional but useful):
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

## Success Criteria

**Minimum:** Combined log file with server output + test results, failed test details extracted, diagnostics captured.

## Anti-patterns to Avoid

- ❌ Don't discard logs on success — logs are useful for regression analysis and performance tracking
- ❌ Don't lose stderr from server — capture both stdout and stderr
- ❌ Don't run tests without logging output — you'll lose debugging info
- ❌ Don't forget to copy logs before teardown — temp directory will be deleted

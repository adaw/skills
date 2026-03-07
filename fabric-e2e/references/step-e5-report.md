# E5: Report (Detailed Procedure)

**Co:** Generate structured E2E report with pass/fail summary, timing, and regression comparison. This phase produces the artifact that documents the test run.

## Full Implementation

### 1. Compile test results and timing:
```bash
LOG_FILE="reports/e2e-$(date +%Y-%m-%d).log"
REPORT_FILE="reports/e2e-$(date +%Y-%m-%d).md"

PASSED=$(grep -c "passed" "$LOG_FILE" || echo 0)
FAILED=$(grep -c "failed" "$LOG_FILE" || echo 0)
ERRORS=$(grep -c "error" "$LOG_FILE" || echo 0)
TOTAL=$((PASSED + FAILED + ERRORS))
DURATION=$(grep "in.*s" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+\.[0-9]+" || echo "0")
```

### 2. Compare with previous e2e report for regression detection:
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

### 3. Generate report in standard fabric.report.v1 format:
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

### 4. Create intake items for each FAILED test:
```bash
if [ $FAILED -gt 0 ]; then
  grep "FAILED" "$LOG_FILE" | while read line; do
    TEST_NAME=$(echo "$line" | cut -d' ' -f1)
    echo "Intake: E2E test $TEST_NAME failed in $REPORT_FILE" >> reports/intake.txt
  done
fi
```

## Report Template (schema: fabric.report.v1)

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

## Success Criteria

**Minimum:** Report file created with pass/fail counts, duration, provider info, log file reference. Intake items created for failures.

## Anti-patterns to Avoid

- ❌ Don't report PASS if any test failed — report WARN or FAIL
- ❌ Don't skip regression comparison — failing tests that previously passed are critical
- ❌ Don't forget intake items — failures must be tracked for next sprint
- ❌ Don't hardcode paths — use environment variables
- ❌ Don't lose test output — reference log files in report

# Guards and Validation Code

## State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="implementation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-e2e. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

## Path Traversal Guard (K7: Input Validation)

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

## K2 Fix: E2E Test Run Counter

```bash
MAX_TEST_RUNS=${MAX_TEST_RUNS:-20}
TEST_RUN_COUNTER=0

# Validate MAX_TEST_RUNS is numeric (K2 tight validation)
if ! echo "$MAX_TEST_RUNS" | grep -qE '^[0-9]+$'; then
  MAX_TEST_RUNS=20
  echo "WARN: MAX_TEST_RUNS not numeric, reset to default (20)"
fi
```

### Test iteration with counter validation:

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

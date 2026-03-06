# fabric-test — Detailní postup (§7 rozšířeno)

## Analýza výstupu testů — Root Cause Heuristics

Po spuštění `gate-test`, pokud `RESULT=FAIL`, aplikuj tuto heuristiku:

### Heuristic 1: Single Module Failure

```bash
FAILING_MODULES=$(grep -E "FAILED|ERROR" {WORK_ROOT}/reports/test-*.md \
  | grep -oP '(?<=::)\w+' | sort | uniq -c)
UNIQUE_MODULES=$(echo "$FAILING_MODULES" | wc -l)

if [ "$UNIQUE_MODULES" -eq 1 ]; then
  ROOT_CAUSE="Single module failure (likely module-level issue: dependency, config, or import error)"
fi
```

### Heuristic 2: Spanning Failures (Shared Dependency)

```bash
if grep -q "FAILED.*test_capture" {WORK_ROOT}/reports/test-*.md && \
   grep -q "FAILED.*test_triage" {WORK_ROOT}/reports/test-*.md; then
  ROOT_CAUSE="Failures in both capture and triage (likely shared dependency: models.py change or store backend)"
fi
```

### Heuristic 3: Single Isolated Test Failure

```bash
FAILED=$(grep -oP '\d+(?= failed)' {WORK_ROOT}/reports/test-*.md | tail -1)
ERRORS=$(grep -oP '\d+(?= error)' {WORK_ROOT}/reports/test-*.md | tail -1)

if [ "${FAILED:-0}" -eq 1 ] && [ "${ERRORS:-0}" -eq 0 ]; then
  ROOT_CAUSE="Single test failure (isolated bug in feature code)"
fi
```

### Heuristic 4: Timeout

```bash
TEST_OUTPUT=$({COMMANDS.test} 2>&1; echo "EXIT:$?")
TEST_EXIT=$(echo "$TEST_OUTPUT" | grep -oP 'EXIT:\K\d+')

if [ "$TEST_EXIT" -eq 124 ]; then
  ROOT_CAUSE="Test runner timeout after 300s (performance regression or infinite loop)"
  # → intake item pro optimalizaci testů
fi
```

---

## Coverage Enforcement (POVINNÉ)

```bash
# Check coverage s prahem ≥60% pro core modules
pytest --cov=src/llmem --cov-report=term-missing --cov-fail-under=60 -q 2>/dev/null
COV_EXIT=$?

if [ $COV_EXIT -ne 0 ]; then
  echo "WARN: coverage <60% for core modules"
  # → intake item pro napsání testů
fi

# Extrahuj coverage percentage
COVERAGE=$(grep -oP '\d+(?=%)' {TEST_OUTPUT} | tail -1)
echo "Coverage: ${COVERAGE}% (target: ≥60%)"
```

---

## Test Isolation Check (POVINNÉ)

Detekuj shared state — globální modifikace nebo env polluting:

```bash
echo "=== Detecting shared state issues ==="

# Pattern 1: bare global mutations
grep -rn "^global " tests/ --include='*.py' | grep -v "pytest.fixture\|monkeypatch"

# Pattern 2: direct os.environ modifications
grep -rn "os\.environ\[" tests/ --include='*.py' | grep -v "monkeypatch"

# Pattern 3: time/random without seed/mock
grep -rn "time\.sleep\|random\." tests/ --include='*.py' \
  | grep "def test_" -A 10 \
  | grep -v "mock\|patch\|seed"

# Výsledek:
if [ -s /tmp/isolation-issues.txt ]; then
  echo "WARN: potential test isolation issues:"
  cat /tmp/isolation-issues.txt
  # → intake item pro isolation fix
fi
```

---

## Test/Code LOC Ratio (POVINNÉ v reportu)

Trend proxy pro test pokrytí:

```bash
# Count test lines
TEST_LOC=$(find {TEST_ROOT}/ -name '*.py' -not -name '__init__.py' \
  | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')

# Count code lines
CODE_LOC=$(find {CODE_ROOT}/ -name '*.py' -not -path '*/test*' -not -name '__init__.py' \
  | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')

if [ "$CODE_LOC" -gt 0 ]; then
  RATIO=$((TEST_LOC * 100 / CODE_LOC))
  echo "Test/Code LOC: ${TEST_LOC}/${CODE_LOC} (${RATIO}%)"

  if [ "$RATIO" -lt 30 ]; then
    echo "CRITICAL: ratio ${RATIO}% very low (<30%) — insufficient test coverage"
  elif [ "$RATIO" -lt 50 ]; then
    echo "WARN: ratio ${RATIO}% low (<50%)"
  fi
fi
```

Target pro LLMem: ≥50% (viz fabric-test příklad, 65% achieved).

---

## Timeout Handling (POVINNÉ)

Timeout (exit code 124) ≠ assertion failure. Andere mitigation:

```bash
timeout 300 {COMMANDS.test}
TEST_EXIT=$?

case $TEST_EXIT in
  0)   RESULT="PASS" ;;
  124) RESULT="TIMEOUT"
       ROOT_CAUSE="Test runner timeout after 300s"
       # → intake item pro slow test analysis
       # → report WARN (ne FAIL — different root cause)
       ;;
  *)   RESULT="FAIL"
       # → standardní FAIL handling
       ;;
esac
```

E2E (pokud existuje):
```bash
if [ -n "{COMMANDS.test_e2e}" ] && [ "{COMMANDS.test_e2e}" != "TBD" ]; then
  timeout 600 {COMMANDS.test_e2e}
  E2E_EXIT=$?

  if [ $E2E_EXIT -eq 124 ]; then
    E2E_RESULT="TIMEOUT"
    # → intake item pro E2E optimization
  elif [ $E2E_EXIT -ne 0 ]; then
    E2E_RESULT="FAIL"
  else
    E2E_RESULT="PASS"
  fi
fi
```

---

## Pytest Output Parsing (strukturované)

Extrahuj pass/fail/error counts z testu:

```bash
TEST_OUTPUT=$({COMMANDS.test} 2>&1)

# Parsuj summary line
PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' | tail -1)
FAILED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= failed)' | tail -1)
ERRORS=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= error)' | tail -1)
SKIPPED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= skipped)' | tail -1)

# Default to 0
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}
ERRORS=${ERRORS:-0}
SKIPPED=${SKIPPED:-0}

echo "Test Summary: $PASSED passed, $FAILED failed, $ERRORS errors, $SKIPPED skipped"

# Detekuj failing test names
if [ "$FAILED" -gt 0 ] || [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "Failing tests (top 10):"
  grep -E "FAILED|ERROR" <<< "$TEST_OUTPUT" | head -10 | while read line; do
    # Extract test_name::file:line
    test_name=$(echo "$line" | grep -oP '(?<=FAILED )\S+|(?<=ERROR )\S+')
    file_line=$(echo "$line" | grep -oP '\S+\.py:\d+')
    error_type=$(echo "$line" | grep -oP '(?<=\[).*(?=\])' | head -1)

    echo "  - $test_name ($file_line, $error_type)"
  done

  if [ "$FAILED" -gt 10 ] || [ "$ERRORS" -gt 10 ]; then
    echo "  ... and $((FAILED + ERRORS - 10)) more"
  fi
fi
```

---

## Flakiness Detection (POVINNÉ pokud PASS)

Ověř, že testy nejsou flaky — spusť 3× a porovnej:

```bash
echo "=== Flakiness Detection (3 reruns) ==="

RESULTS=()
for RUN in 1 2 3; do
  echo "Run $RUN..."
  timeout 300 {COMMANDS.test} > /tmp/test_run_${RUN}.log 2>&1
  EXIT_CODE=$?

  PASSED=$(grep -oP '\d+(?= passed)' /tmp/test_run_${RUN}.log | tail -1)
  FAILED=$(grep -oP '\d+(?= failed)' /tmp/test_run_${RUN}.log | tail -1)

  RESULTS+=("Run $RUN: ${PASSED:-0} passed, ${FAILED:-0} failed")
done

# Check consistency
if [ "${RESULTS[0]}" = "${RESULTS[1]}" ] && [ "${RESULTS[1]}" = "${RESULTS[2]}" ]; then
  echo "✓ Consistent across 3 runs (no flakiness detected)"
  FLAKY_TESTS=""
else
  echo "⚠ Inconsistent results across runs — investigating flaky tests"
  FLAKY_TESTS=$(diff /tmp/test_run_1.log /tmp/test_run_2.log | grep -E "FAILED|PASSED" | head -5)
fi
```

---

## Anti-Patterns Catalog (Detection & Fix)

### A1: Flaky Tests — Time-Dependent Randomness

**Detection:**
```bash
grep -rn "import random\|from random\|random\." {TEST_ROOT} --include='*.py' \
  | grep -v "mock\|patch" | head -10
grep -rn "datetime\|time\.time\|time\.sleep" {TEST_ROOT} --include='*.py' \
  | grep "def test_" -B 5 | head -10
```

**Fix:**
1. Replace `random.choice()` with `random.seed(42)` at test start
2. Replace `time.sleep()` with `pytest-freezegun` or `unittest.mock.patch('time.time')`
3. Add `@pytest.mark.flaky(reruns=3)` only to genuinely non-deterministic tests

### A2: Hardcoded Sleep Delays

**Detection:**
```bash
grep -rn "sleep\|time\.sleep" {TEST_ROOT} --include='*.py' \
  | grep -v "pytest.mark.timeout\|patch.*sleep"
```

**Fix:**
1. Replace `time.sleep(N)` with polling loop: `wait_for(condition, timeout=10)`
2. Add `@pytest.mark.timeout(30)` to prevent hanging
3. Use `pytest-asyncio` for async waits

### A3: Unmocked External Dependencies

**Detection:**
```bash
grep -rn "requests\|urllib\|socket\|open(\|db\." {TEST_ROOT} --include='*.py' \
  | grep "def test_" -A 10 | grep -v "mock\|patch\|fixture"
```

**Fix:**
1. Identify external call (requests.get, open, DB query)
2. Wrap with `@patch('module.requests.get')`
3. Verify mock via `mock_requests.get.assert_called_once_with(...)`
4. Mark as `@pytest.mark.integration` if truly needed

### A4: Missing Assertions

**Detection:**
```bash
grep -rn "def test_" {TEST_ROOT} --include='*.py' | while read test; do
  FILE=$(echo "$test" | cut -d: -f1)
  FUNC=$(echo "$test" | grep -oP 'def \K[^(]+')
  ASSERT_COUNT=$(awk "/def $FUNC/,/^def |^class / {print}" "$FILE" | grep -c "assert " || echo 0)
  if [ "$ASSERT_COUNT" -lt 1 ]; then
    echo "WEAK: $FUNC has no assertions"
  fi
done
```

**Fix:**
1. Ensure ≥2 assertions per test (happy path + edge/error)
2. Replace vague `assert result` with `assert result is not None`
3. Use `pytest.raises(ValueError)` for expected exceptions

### A5: Broad try/except

**Detection:**
```bash
grep -rn "except:" {TEST_ROOT} --include='*.py'
grep -rn "except Exception:" {TEST_ROOT} --include='*.py' | head -10
```

**Fix:**
1. Replace bare `except:` with `except ValidationError:`
2. Replace broad `except Exception:` with `except (ValueError, TypeError):`
3. Use `pytest.raises()` for expected exceptions

---

## Downstream Contract (fabric-review)

The test report MUST include:

- `version` (string) — report version/date
- `test_passed` (bool) — True if all tests PASS
- `coverage_pct` (float) — overall coverage (0-100)
- `test_count` (int) — total tests executed
- `passed_count`, `failed_count`, `error_count` (ints)
- `failure_details[]` — per failure: test_name, file_line, error_type, message
- `root_cause` (string) — analysis if FAIL
- `notes` (string) — summary of test execution
- `flaky_tests[]` — list of flaky tests detected

See references/examples.md for complete example.

---
name: fabric-test
description: "Run the configured test suites for the current WIP task (state.wip_item) and write an evidence report. Uses COMMANDS.test (and optionally COMMANDS.test_e2e). Does not modify code. Fails fast on missing config commands."
---

# TEST — Spuštění testů (evidence)

## Účel

Spustit testy definované v `{WORK_ROOT}/config.md` a vytvořit report s evidencí pro další kroky (review/close).

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-test" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-test" --event end --status OK --report "{WORK_ROOT}/reports/test-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy

- `{WORK_ROOT}/config.md` (COMMANDS.test, volitelně test_e2e)
- `{WORK_ROOT}/state.md` (wip_item)
- `{WORK_ROOT}/backlog/{wip_item}.md`
- repo working tree (aktuální branch je `{state.wip_branch}`)

---

## Výstupy

- `{WORK_ROOT}/reports/test-*.md` *(vytváří deterministicky `fabric.py gate-test`; ty jen doplňuješ interpretaci)*

---

## Preconditions

- `state.wip_item` musí být vyplněné
- `COMMANDS.test` musí být vyplněné a nesmí být `TBD`
- `state.wip_branch` musí existovat jako git branch

Pokud není splněno:
- vytvoř intake item `intake/test-missing-wip-or-commands.md`
- FAIL

### File & branch existence checks (povinné)

```bash
WIP_ITEM=$(python skills/fabric-init/tools/fabric.py state-get --field wip_item 2>/dev/null)
WIP_BRANCH=$(python skills/fabric-init/tools/fabric.py state-get --field wip_branch 2>/dev/null)

# 1. wip_item musí mít backlog soubor
if [ ! -f "{WORK_ROOT}/backlog/${WIP_ITEM}.md" ]; then
  echo "STOP: backlog file missing for wip_item=$WIP_ITEM"
  python skills/fabric-init/tools/fabric.py intake-new --source "test" --slug "missing-backlog-file" \
    --title "Backlog file not found: backlog/${WIP_ITEM}.md"
  exit 1
fi

# 2. wip_branch musí existovat v git
if ! git rev-parse --verify "$WIP_BRANCH" >/dev/null 2>&1; then
  echo "STOP: branch $WIP_BRANCH does not exist in git"
  python skills/fabric-init/tools/fabric.py intake-new --source "test" --slug "missing-branch" \
    --title "Git branch not found: $WIP_BRANCH"
  exit 1
fi
```

> `COMMANDS.test_e2e` je volitelné:
> - `""` nebo `TBD` = nespouštěj
> - cokoliv jiného = spusť po unit/integration testech

---


## FAST PATH (doporučeno) — testy deterministicky + log capture

Místo ručního spouštění příkazů používej deterministický gate `gate-test`, který:

- vezme `COMMANDS.test` z configu,
- uloží plný log do `{WORK_ROOT}/logs/commands/`,
- vytvoří **parsovatelný** test report (povinné pro `tick` gating),
- a vrátí JSON shrnutí (Result + cesty).

```bash
python skills/fabric-init/tools/fabric.py gate-test --tail 200
```

Volitelně E2E (pokud má projekt `COMMANDS.test_e2e`):
```bash
python skills/fabric-init/tools/fabric.py run test_e2e --tail 200
```

---

## Příklad vyplněného test reportu

```markdown
---
title: "Test Report - T-101 (Add Pydantic Validation)"
version: "1.0"
date: "2026-03-10"
wip_item: "T-101"
test_status: "PASS"
---

## Summary

**Result:** PASS

| Metric | Value |
|--------|-------|
| Tests Passed | 87 |
| Tests Failed | 0 |
| Tests Errored | 0 |
| Tests Skipped | 5 |
| Total Tests | 92 |
| Coverage | 78.3% |
| Test/Code LOC Ratio | 65% |

## Test Execution Details

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
- `src/llmem/api/routes/capture.py`: 92% (was 45% before T-101)
- `src/llmem/models.py`: 85% (unchanged, used by capture)
- `src/llmem/api/validation.py`: 95% (new module for validation schema)

**Overall Project Coverage:** 78.3% (target: ≥60% for core modules, 78.3% achieved: PASS)

## Modules Tested

| Module | Tests | Assertions | Coverage |
|--------|-------|-----------|----------|
| api/routes/capture.py | 12 | 24 | 92% |
| api/validation.py | 8 | 16 | 95% |
| models.py | 15 | 30 | 85% |
| triage/heuristics.py | 28 | 56 | 81% |
| storage/backends/inmemory.py | 18 | 36 | 76% |
| recall/pipeline.py | 9 | 18 | 68% |

## No Failures — Pass Summary

87 tests passed. Key coverage areas:
- **Capture validation:** All Pydantic validations trigger on invalid input (T-101 requirement)
- **Edge cases:** Empty JSON, missing fields, null values, oversized payloads all handled
- **Triage flow:** Validation error messages propagate correctly without data corruption
- **Backward compatibility:** Existing endpoints unaffected

## Test Execution Notes

**Duration:** 12.4 seconds (all tests ran in parallel, no timeouts)

**Test Isolation:** Verified no cross-test state pollution:
- No global state modifications detected
- pytest fixtures used correctly (not hardcoded)
- Database mock reset between tests

**Performance:** No test slowness detected. Slowest tests (all <100ms):
- test_triage_deterministic_ids: 87ms (hashing heavy, acceptable)
- test_capture_with_invalid_json: 45ms (validation overhead, acceptable)

## Flakiness Detection

Re-ran all 87 tests 3 times:
- **Run 1:** 87 PASS
- **Run 2:** 87 PASS
- **Run 3:** 87 PASS

**Flaky tests:** 0 (no inconsistent failures)

## Test/Code LOC Ratio

- **Test LOC:** 3,240 lines (tests/)
- **Code LOC:** 5,000 lines (src/llmem, excluding __pycache__)
- **Ratio:** 65% (healthy; >30% indicates good test coverage)

Target for LLMem: ≥50% (65% achieved: PASS)

## Acceptance Criteria Validation

T-101 AC checklist:
- [x] POST /capture/event validates input with Pydantic
- [x] Invalid JSON rejected with 400 status
- [x] Missing required fields rejected with clear error message
- [x] Rate limiting validation (delegated to T-102, skipped in T-101 tests)
- [x] No data corruption on validation error

**All AC met:** PASS
```

---

## Postup

1. Načti `state.md` → `id = wip_item`, `branch = wip_branch`
2. Checkoutni branch (bez změn):
   ```bash
   git status --porcelain
   git checkout "${branch}"
   ```
   Pokud working tree není čistý → FAIL (testy musí běžet na čistém stavu)
3. Spusť testy deterministicky:

   ```bash
   python skills/fabric-init/tools/fabric.py gate-test --tail 200
   ```

   Tím vznikne report v `{WORK_ROOT}/reports/` s řádkem `Result: PASS` nebo `Result: FAIL` (BEZ leading dash — kanonický formát pro fabric-loop verdict parsing).
4. Pokud `COMMANDS.test_e2e` není prázdné **a zároveň není `TBD`**, spusť i E2E (volitelně):
   ```bash
   {COMMANDS.test_e2e}
   ```
5. **Pytest output parsing (POVINNÉ)** — extrahuj strukturované výsledky:
   ```bash
   # Spusť testy a zachyť výstup
   TEST_OUTPUT=$(timeout 300 {COMMANDS.test} 2>&1)
   TEST_EXIT=$?

   # Extrahuj pass/fail/error counts
   PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' | tail -1)
   FAILED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= failed)' | tail -1)
   ERRORS=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= error)' | tail -1)
   SKIPPED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= skipped)' | tail -1)

   PASSED=${PASSED:-0}
   FAILED=${FAILED:-0}
   ERRORS=${ERRORS:-0}
   SKIPPED=${SKIPPED:-0}

   echo "Test Summary: $PASSED passed, $FAILED failed, $ERRORS errors, $SKIPPED skipped"
   ```

6. **Root cause heuristics (POVINNÉ pro FAIL)**:
   ```bash
   if [ "$FAILED" -gt 0 ] || [ "$ERRORS" -gt 0 ]; then
     # Heuristic 1: Check if all failures are in same module
     FAILING_MODULES=$(echo "$TEST_OUTPUT" | grep -E "FAILED|ERROR" | grep -oP '(?<=::)\w+' | sort | uniq -c)
     UNIQUE_MODULES=$(echo "$FAILING_MODULES" | wc -l)

     if [ "$UNIQUE_MODULES" -eq 1 ]; then
       ROOT_CAUSE="Single module failure (likely module-level issue: dependency, config, or import error)"
     else
       # Heuristic 2: Check if failures span capture + triage → shared dependency
       if echo "$TEST_OUTPUT" | grep -qE "FAILED.*test_capture" && echo "$TEST_OUTPUT" | grep -qE "FAILED.*test_triage"; then
         ROOT_CAUSE="Failures in both capture and triage (likely shared dependency: models.py change or store backend)"
       # Heuristic 3: Single isolated test failure
       elif [ "$FAILED" -eq 1 ] && [ "$ERRORS" -eq 0 ]; then
         ROOT_CAUSE="Single test failure (isolated bug in feature code)"
       # Heuristic 4: Timeout
       elif [ "$TEST_EXIT" -eq 124 ]; then
         ROOT_CAUSE="Test runner timeout (performance regression or infinite loop)"
       else
         ROOT_CAUSE="Multiple failures across modules (requires detailed analysis)"
       fi
     fi
     echo "ROOT_CAUSE: $ROOT_CAUSE"
   fi
   ```

7. Analyzuj výstup (structured failure analysis):
   - Parsuj stderr/stdout pro klíčové signály:
     - test runner summary (např. `X passed, Y failed, Z errors`) — **nyní strukturované**
     - konkrétní failing test names + assertion message
     - stack trace → identifikuj soubor a řádek
   - Pokud test runner generuje structured output (JUnit XML, pytest JSON), parsuj ho přednostně
   - Pro každý failing test zapiš:
     - `test_name`, `file:line`, `error_type`, zkrácený `message` (max 3 řádky)
   - Pokud FAIL count > 20, zapiš jen top 10 + „… and {N} more"
8. **Coverage enforcement (POVINNÉ)**:
   ```bash
   # Coverage check s prahem
   pytest --cov=src/llmem --cov-report=term-missing --cov-fail-under=60 -q 2>/dev/null
   COV_EXIT=$?
   if [ $COV_EXIT -ne 0 ]; then
     echo "WARN: coverage <60% for core modules"
   fi
   ```

9. **Test isolation check (POVINNÉ)** — detekuj shared state:
   ```bash
   # Check pro global state modifikaci
   grep -rn "global\|os.environ\[" tests/ --include="*.py" | grep -v "monkeypatch\|pytest.fixture" | head -5 > /tmp/isolation-issues.txt
   if [ -s /tmp/isolation-issues.txt ]; then
     echo "WARN: potential test isolation issues detected:"
     cat /tmp/isolation-issues.txt
   fi
   ```

10. Doplň report (**povinné** — NESMÍ zůstat prázdné):
    - přidej structured failures (viz krok 7)
    - pokud FAIL: napiš *nejpravděpodobnější root cause* (z heuristics) + *next action*
    - pokud PASS: napiš **minimálně 1–2 věty** shrnutí: kolik testů, co pokrývají, jaké moduly/soubory byly testovány
    - **Notes sekce NESMÍ být prázdná** — `gate-test` vytvoří skeleton, ale ty MUSÍŠ doplnit interpretaci
    - **GOOD notes example:** "Tests: 87 passed, 0 failed. Coverage: 78%. Modules tested: capture_service (92%), recall_service (71%), triage (85%). No regressions from baseline."

> **Poznámka:** `gate-test` report vytvoří automaticky. Ty **musíš** doplnit interpretaci — prázdný Notes/Failures je skill violation.

11. **LOC ratio tracking (POVINNÉ v reportu):**
    ```bash
    # Test-to-code LOC ratio
    CODE_LOC=$(find {CODE_ROOT}/ -name '*.py' -not -path '*/test*' -not -name '__init__.py' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
    TEST_LOC=$(find {TEST_ROOT}/ -name '*.py' -not -name '__init__.py' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
    if [ "$CODE_LOC" -gt 0 ]; then
      RATIO=$((TEST_LOC * 100 / CODE_LOC))
      echo "Test/Code LOC ratio: ${RATIO}% ($TEST_LOC test / $CODE_LOC code)"

      # Enforcement: warn if ratio too low
      if [ "$RATIO" -lt 30 ]; then
        echo "CRITICAL: Test/Code LOC ratio ${RATIO}% is very low (<30%) — insufficient test coverage"
      elif [ "$RATIO" -lt 50 ]; then
        echo "WARN: Test/Code LOC ratio ${RATIO}% is low (<50%)"
      fi
    fi
    ```
    Zapiš do test reportu: `Test/Code LOC: {TEST_LOC}/{CODE_LOC} ({RATIO}%)`. Trend proxy pro test pokrytí.

---

## Report template

Použij `{WORK_ROOT}/templates/test-report.md` (vytvořeno přes `report-new`).

---

### Timeout a hanging testy

Spouštěj s timeoutem a **vždy kontroluj exit code**:

```bash
timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then
  RESULT="TIMEOUT"
  ROOT_CAUSE="Test runner timeout after 300s"
elif [ $TEST_EXIT -ne 0 ]; then
  RESULT="FAIL"
else
  RESULT="PASS"
fi
```

Pro `test_e2e` (explicitně):
```bash
if [ -n "{COMMANDS.test_e2e}" ] && [ "{COMMANDS.test_e2e}" != "TBD" ]; then
  timeout 600 {COMMANDS.test_e2e}
  E2E_EXIT=$?
  if [ $E2E_EXIT -eq 124 ]; then
    E2E_RESULT="TIMEOUT"
    E2E_ROOT_CAUSE="E2E test runner timeout after 600s"
  elif [ $E2E_EXIT -ne 0 ]; then
    E2E_RESULT="FAIL"
  else
    E2E_RESULT="PASS"
  fi
fi
```

- TIMEOUT se hodnotí jako FAIL s `root_cause: "Test runner timeout after {N}s"`.
- TIMEOUT NESMÍ být zaměněn za normální FAIL (jiný root cause, jiná remediace).
- Vytvoř intake item `intake/test-timeout-{date}.md` s doporučením: identifikovat pomalé testy, zvážit paralelizaci nebo test split.

---

## Catalog of Common Test Anti-Patterns (with detection)

**WQ4 Fix: ALL anti-patterns have (a) detection bash command, (b) concrete fix procedure**

### A1: Flaky Tests — Time-Dependent Randomness

**Detection:**
```bash
echo "=== Detecting Time-Dependent & Random Tests ==="
grep -rn "import random\|from random\|random\." {TEST_ROOT} --include='*.py' | grep -v "mock\|patch" | head -10
grep -rn "datetime\|time.time\|time.sleep\|sleep(" {TEST_ROOT} --include='*.py' | grep "def test_" -B 5 | head -10
```

**Fix Procedure:**
1. Replace all `random.choice()` / `random.randint()` with deterministic fixtures or seed: `random.seed(42)` at test start
2. Replace `time.sleep()` with mock clock (pytest-freezegun or unittest.mock.patch('time.time'))
3. Replace time-dependent assertions like `assert time.time() > X` with mock clock verification
4. Add `@pytest.mark.flaky(reruns=3)` only to genuinely non-deterministic tests (and investigate why)

### A2: Hardcoded Sleep Delays

**Detection:**
```bash
echo "=== Detecting Hardcoded sleep() in Tests ==="
grep -rn "sleep\|time\.sleep" {TEST_ROOT} --include='*.py' | grep -v "pytest.mark.timeout\|patch.*sleep"
```

**Fix Procedure:**
1. Replace `time.sleep(N)` with:
   - If waiting for async task: Use `pytest.mark.asyncio` + `await asyncio.sleep()`
   - If waiting for state change: Use polling loop with timeout: `wait_for(condition, timeout=10)`
   - If testing timeout behavior: Use `pytest-timeout` + mock clock
2. Add timeout marker: `@pytest.mark.timeout(30)` to prevent hanging tests

### A3: External Dependency Calls (Network, Files, DB)

**Detection:**
```bash
echo "=== Detecting Unmocked External Dependencies ==="
grep -rn "http\|requests\|urllib\|socket\|open(\|read(\|write(\|db\." {TEST_ROOT} --include='*.py' | grep "def test_" -A 10 | grep -v "mock\|patch\|fixture"
```

**Fix Procedure:**
1. Identify external call: `requests.get()`, `open()`, database query, etc.
2. Wrap with mock: `@patch('module.requests.get')` or use pytest fixture with MagicMock
3. Verify mock is used: Add assertion `mock_requests.get.assert_called_once_with(...)`
4. Document why external dependency needed (integration test) and mark: `@pytest.mark.integration`

### A4: Missing Assertions or Weak Assertions

**Detection:**
```bash
echo "=== Detecting Weak/Missing Assertions ==="
grep -rn "def test_" {TEST_ROOT} --include='*.py' | while read test; do
  FILE=$(echo "$test" | cut -d: -f1)
  FUNC=$(echo "$test" | grep -oP 'def \K[^(]+')
  ASSERT_COUNT=$(awk "/def $FUNC/,/^def |^class / {print}" "$FILE" | grep -c "assert " || echo 0)
  if [ "$ASSERT_COUNT" -lt 1 ]; then
    echo "WEAK: $FUNC has <1 assertion"
  fi
done | head -10
```

**Fix Procedure:**
1. Ensure each test has ≥2 assertions (one for happy path, one for edge case or error)
2. Replace vague assertions: `assert result` → `assert result is not None`, `assert len(result) == 3`
3. Use specific assertion helpers: `pytest.raises(ValueError)`, `assert_called_with()`, `assert_equals()`
4. Add assertion message for clarity: `assert x > 0, f"Expected positive, got {x}"`

### A5: Overly Broad try/except in Tests

**Detection:**
```bash
echo "=== Detecting Bare except: in Tests ==="
grep -rn "except:" {TEST_ROOT} --include='*.py' | grep -v "except .*Error\|except .*Exception"
grep -rn "except Exception:" {TEST_ROOT} --include='*.py' | head -10
```

**Fix Procedure:**
1. Replace bare `except:` with specific exception: `except ValidationError:`, `except TimeoutError:`
2. Replace broad `except Exception:` with domain-specific: `except (ValueError, TypeError):`
3. Use `pytest.raises()` for expected exceptions: `with pytest.raises(ValidationError): function_call()`
4. Log/re-raise unexpected exceptions: `except Exception as e: print(f"Unexpected error: {e}"); raise`

---

## Downstream Contract

**fabric-review** reads the following from test report:
- `version` (string) — report version/date
- `test_passed` (bool) — True if all tests PASS, False if any FAIL/ERROR
- `coverage_pct` (float) — overall code coverage percentage (0-100)
- `test_count` (int) — total number of tests executed
- `passed_count` (int) — number of tests that passed
- `failed_count` (int) — number of tests that failed
- `error_count` (int) — number of tests with runtime errors
- `failure_details[]` (list) — for each failure:
  - `test_name` (string)
  - `file_line` (string, e.g. "test_capture.py:45")
  - `error_type` (string, e.g. "AssertionError")
  - `message` (string, truncated to <200 chars)
- `root_cause` (string) — analysis of why tests failed (if FAIL)
- `notes` (string) — summary of test execution and coverage story
- `flaky_tests[]` (list) — tests that inconsistently pass/fail across reruns

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/`
- **Notes sekce je neprázdná** (alespoň 1 věta)
- pokud FAIL, report obsahuje aspoň 1 jasný root cause nebo next action
- pokud PASS, report říká kolik testů prošlo a co pokrývaly
- **version field present** in YAML frontmatter

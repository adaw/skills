# H3: Quality Gates — Detailní procedura

## Cíl
Spusť lint + testy, oprav problémy.

## Postup (detailní instrukce)

### 1. Lint (pokud nakonfigurován)
```bash
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint}
  LINT_EXIT=$?
  if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint"; fi
  if [ $LINT_EXIT -ne 0 ] && [ -n "{COMMANDS.lint_fix}" ]; then
    echo "Auto-fixing lint..."
    LINT_RETRY_COUNT=0
    LINT_MAX_RETRIES=3
    # K2 guard: Validate counter is numeric
    if ! [[ "$LINT_RETRY_COUNT" =~ ^[0-9]+$ ]] || ! [[ "$LINT_MAX_RETRIES" =~ ^[0-9]+$ ]]; then
      echo "STOP: Invalid retry counter (must be numeric)"
      exit 1
    fi
    timeout 120 {COMMANDS.lint_fix}
    LINT_RETRY_COUNT=$((LINT_RETRY_COUNT + 1))
    timeout 120 {COMMANDS.lint}
    LINT_RETRY_EXIT=$?
    # K2 guard: Termination check
    if [ $LINT_RETRY_EXIT -ne 0 ]; then
      if [ $LINT_RETRY_COUNT -ge $LINT_MAX_RETRIES ]; then
        echo "STOP: lint auto-fix exceeded max retries ($LINT_MAX_RETRIES) — fix manually"
        exit 1
      else
        echo "FAIL: lint still failing — fix manually"
      fi
    fi
  fi
fi
```

### 2. Format Check (pokud nakonfigurován)
```bash
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check}
  if [ $? -ne 0 ] && [ -n "{COMMANDS.format}" ]; then
    echo "Auto-fixing format..."
    FORMAT_RETRY_COUNT=0
    FORMAT_MAX_RETRIES=3
    # K2 guard: Validate counter is numeric
    if ! [[ "$FORMAT_RETRY_COUNT" =~ ^[0-9]+$ ]] || ! [[ "$FORMAT_MAX_RETRIES" =~ ^[0-9]+$ ]]; then
      echo "STOP: Invalid retry counter (must be numeric)"
      exit 1
    fi
    timeout 120 {COMMANDS.format}
    FORMAT_RETRY_COUNT=$((FORMAT_RETRY_COUNT + 1))
    timeout 120 {COMMANDS.format_check}
    FORMAT_RETRY_EXIT=$?
    # K2 guard: Termination check
    if [ $FORMAT_RETRY_EXIT -ne 0 ]; then
      if [ $FORMAT_RETRY_COUNT -ge $FORMAT_MAX_RETRIES ]; then
        echo "STOP: format auto-fix exceeded max retries ($FORMAT_MAX_RETRIES) — fix manually"
        exit 1
      fi
    fi
  fi
fi
```

### 3. Tests (POVINNÉ)
```bash
timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then echo "TIMEOUT: tests exceeded 300s"; fi
if [ $TEST_EXIT -ne 0 ]; then echo "FAIL: tests not passing — fix before continuing"; fi
```

## Minimum (výstup)
- Lint PASS (nebo SKIPPED pokud není nakonfigurován)
- Tests PASS (POVINNÉ — hotfix NESMÍ mergovat s failing testy)

## Anti-patterns (zakázáno)
- Mergovat hotfix s failing testy „protože je to urgent" — **NIKDY**
- Ignorovat lint warnings — oprav nebo zaloguj

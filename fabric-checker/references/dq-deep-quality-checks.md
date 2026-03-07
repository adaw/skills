# DQ1-DQ6: Deep Quality Checks

Tyto kontroly jdou HLOUBĚJI než runtime gates (lint/test). Ověřují strukturální konzistenci kódu.

## Check Overview

| ID | Check | Co ověřit | Severity |
|----|-------|-----------|----------|
| DQ1 | API konzistence | Všechny endpointy v `api/routes/` mají odpovídající spec v `specs/` | HIGH |
| DQ2 | Model field coverage | Každý Pydantic model v `models.py` má: type hints, Optional/default, docstring | MEDIUM |
| DQ3 | Config schema validace | Všechny `LLMEM_*` env vars v `config.py` mají: default, description, type | MEDIUM |
| DQ4 | Import konzistence | Žádné cirkulární importy, žádné wildcard importy | HIGH |
| DQ5 | Test-to-code mapping | Každý modul v `src/llmem/` má odpovídající test v `tests/` | MEDIUM |
| DQ6 | Error message quality | Chybové zprávy obsahují kontext (ne jen "Error occurred") | LOW |

## Postup pro DQ checks

```bash
# DQ1: API route vs spec check
ROUTES=$(grep -rn '@app\.\(get\|post\|put\|delete\)' {CODE_ROOT}/api/ 2>/dev/null | wc -l)
SPEC_ENDPOINTS=$(grep -c 'endpoint:' {WORK_ROOT}/specs/LLMEM_API_V1*.md 2>/dev/null || echo 0)
echo "DQ1: $ROUTES routes in code, $SPEC_ENDPOINTS in spec"
if [ "$ROUTES" -gt "$SPEC_ENDPOINTS" ]; then
  echo "WARN: code has more routes than spec documents ($ROUTES vs $SPEC_ENDPOINTS)"
fi

# DQ2: Model docstring coverage
MODELS=$(grep -c 'class.*BaseModel' {CODE_ROOT}/models.py 2>/dev/null || echo 0)
MODELS_WITH_DOC=$(grep -A1 'class.*BaseModel' {CODE_ROOT}/models.py 2>/dev/null | grep -c '"""' || echo 0)
echo "DQ2: $MODELS models, $MODELS_WITH_DOC with docstrings"

# DQ3: Config field validation
CONFIG_FIELDS=$(grep -c 'Field(' {CODE_ROOT}/config.py 2>/dev/null || echo 0)
CONFIG_WITH_DESC=$(grep 'Field(' {CODE_ROOT}/config.py 2>/dev/null | grep -c 'description=' || echo 0)
echo "DQ3: $CONFIG_FIELDS config fields, $CONFIG_WITH_DESC with description"

# DQ4: No wildcard imports
WILDCARDS=$(grep -rn 'from .* import \*' {CODE_ROOT}/ 2>/dev/null | grep -v __init__ | wc -l)
if [ "$WILDCARDS" -gt 0 ]; then
  echo "WARN: $WILDCARDS wildcard imports found (excluding __init__)"
fi

# DQ5: Test mapping
MISSING_TESTS=0
for SRC_FILE in {CODE_ROOT}/*.py {CODE_ROOT}/**/*.py; do
  [ -f "$SRC_FILE" ] || continue
  MODULE=$(basename "$SRC_FILE" .py)
  [ "$MODULE" = "__init__" ] && continue
  if [ ! -f "tests/test_${MODULE}.py" ]; then
    echo "DQ5: missing test file for $MODULE"
    MISSING_TESTS=$((MISSING_TESTS + 1))
  fi
done
echo "DQ5: $MISSING_TESTS modules without tests"

# DQ6: Error message quality
BARE_ERRORS=$(grep -rn 'raise.*Error(.*["\047]Error' {CODE_ROOT}/ 2>/dev/null | grep -v '{' | wc -l)
echo "DQ6: $BARE_ERRORS bare error messages (should contain context)"
```

## Výstupní formát

```md
## Deep Quality Checks

| ID | Check | Stav | Detail |
|----|-------|------|--------|
| DQ1 | API konzistence | PASS/WARN | {routes} routes, {spec_endpoints} in spec |
| DQ2 | Model field coverage | PASS/WARN | {models} models, {with_doc} with docstrings |
| DQ3 | Config schema | PASS/WARN | {vars} env vars, {with_defaults} with defaults |
| DQ4 | Import konzistence | PASS/FAIL | {wildcards} wildcard imports |
| DQ5 | Test mapping | PASS/WARN | {missing} modules without tests |
| DQ6 | Error messages | PASS/WARN | {bare_errors} bare error messages |
```

## Anti-patterns

- ❌ Přeskočit DQ checks protože lint/test prošly
- ❌ Reportovat jen PASS/FAIL bez konkrétních čísel
- ✅ Vždy uvést konkrétní počty a identifikovat chybějící položky

## Context pro DQ checks

- `CODE_ROOT` = obvykle `src/llmem/` nebo ekvivalent
- `WORK_ROOT` = workspace root s `specs/`, `config.md`, atd.
- Čítej DQ checks POUZE v `scope=deep`
- Každý check vrací konkrétní metriku (počet vs slibovaný)

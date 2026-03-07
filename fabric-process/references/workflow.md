# Detailed Workflow Procedures — fabric-process

This file contains the detailed procedural steps for §7 (Postup) from the main SKILL.md.

## State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-process. Expected: $EXPECTED_PHASES"
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
# validate_path "$PROCESS_FILE"
# validate_path "$MAP_PATH"
```

## K2 Fix: External Process Extraction with Counter

```bash
MAX_PROCESSES=${MAX_PROCESSES:-200}
PROCESS_COUNTER=0
```

When iterating over routes/commands found during extraction:
```bash
while read -r route; do
  PROCESS_COUNTER=$((PROCESS_COUNTER + 1))
  if [ "$PROCESS_COUNTER" -ge "$MAX_PROCESSES" ]; then
    echo "WARN: max process extraction iterations reached ($PROCESS_COUNTER/$MAX_PROCESSES)"
    break
  fi
  # ... extract process details
done
```

## Route Inventory — FAST PATH Detection

```bash
# 3. Route inventory (strojový sken)
echo "=== Route Inventory ==="
ROUTE_FILES=$(find "${CODE_ROOT}" -path "*/api/routes/*.py" -type f 2>/dev/null)
ROUTE_COUNT=0
for rf in $ROUTE_FILES; do
  COUNT=$(grep -cE '@router\.(get|post|put|delete|patch)' "$rf" 2>/dev/null || echo 0)
  ROUTE_COUNT=$((ROUTE_COUNT + COUNT))
  echo "  $rf: $COUNT routes"
done
echo "Total routes found: $ROUTE_COUNT"
```

## Service Inventory — FAST PATH Detection

```bash
# 4. Service inventory (strojový sken)
echo "=== Service Inventory ==="
grep -rn "^class.*Service" "${CODE_ROOT}" --include="*.py" 2>/dev/null | while read line; do
  echo "  $line"
done
```

## CLI Command Inventory — FAST PATH Detection

```bash
# 5. CLI command inventory
echo "=== CLI Inventory ==="
grep -rn "def.*command\|@app.command\|@click.command\|add_parser" "${CODE_ROOT}" --include="*.py" 2>/dev/null | head -20
```

## Model Inventory — FAST PATH Detection

```bash
# 6. Model inventory
echo "=== Model Inventory ==="
grep -rn "^class.*BaseModel\|^class.*Base)\|^class.*Enum" "${CODE_ROOT}" --include="*.py" 2>/dev/null | while read line; do
  echo "  $line"
done
```

## Previous Process Map Delta Detection

```bash
# 7. Předchozí process map (pokud existuje)
PREV_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if [ -f "$PREV_MAP" ]; then
  PREV_EXT=$(grep -c "^| ext-" "$PREV_MAP" 2>/dev/null || echo 0)
  PREV_INT=$(grep -c "^| int-" "$PREV_MAP" 2>/dev/null || echo 0)
  PREV_UPDATED=$(grep "^updated:" "$PREV_MAP" | cut -d' ' -f2)
  echo "Previous map: $PREV_EXT external, $PREV_INT internal (updated: $PREV_UPDATED)"
else
  echo "No previous process map found (first run)"
fi
```

## P1: External Process Detection — Anti-patterns

### Anti-pattern A: Endpoint not in process-map

```bash
grep -rE '@router\.(get|post|put|delete|patch)' ${CODE_ROOT}/api/routes/ --include="*.py" | \
grep -oP '(?<=['\''"])/[^'\''"]*(?\([\'\''"])' | \
sort -u | \
while read r; do
  grep -q "ext-.*$r" {WORK_ROOT}/fabric/processes/process-map.md || echo "UNMAPPED: $r"
done
```

Fix: Add missing routes as ext-{domain}-{action} rows to process-map.md

### Anti-pattern B: CLI command undocumented

```bash
grep -rE '@click\.command|@app\.command' ${CODE_ROOT}/ --include="*.py" -A1 | \
grep "def " | \
sed 's/def //' | \
sed 's/(.*/:/' | \
while read cmd; do
  grep -q "ext-cli-$cmd" {WORK_ROOT}/fabric/processes/process-map.md || echo "UNDOCUMENTED_CLI: $cmd"
done
```

Fix: Add ext-cli-{cmd} rows with actor, trigger, entry point

### Anti-pattern C: Internal process missing contract_modules

```bash
find {WORK_ROOT}/fabric/processes/ -name "int-*.md" -exec grep -L 'contract_modules:' {} \;
```

Fix: For each file, trace code flow and list all .py files in the chain

## P1: Process Count Validation (WQ3)

```bash
# Po vytvoření process-map.md ověř pokrytí (WQ3 fix)
MAP_EXT=$(grep -c "^| ext-" {WORK_ROOT}/fabric/processes/process-map.md 2>/dev/null || echo 0)
CODE_ROUTES=$(grep -rE '@router\.(get|post|put|delete|patch)' ${CODE_ROOT}/api/routes/ --include="*.py" 2>/dev/null | wc -l)
CODE_CLI=$(grep -rE '@(click\.command|app\.command|click\.option)' ${CODE_ROOT}/ --include="*.py" 2>/dev/null | grep -c '@\(click\|app\)\.command' || echo 0)
EXPECTED=$((CODE_ROUTES + CODE_CLI))

if [ "$MAP_EXT" -ge "$EXPECTED" ]; then
  echo "PASS: External processes ($MAP_EXT) match code routes ($CODE_ROUTES) + CLI ($CODE_CLI)"
else
  echo "WARN: Process map ($MAP_EXT external) may be incomplete vs code ($EXPECTED expected)"
fi
```

## P2: Internal Chain Tracing — Deterministic Classification (WQ5)

```bash
# Parametr: FUNCTION_NAME (e.g. "score_importance")

# Krok 1: Zjisti, zda se funkce volá z NĚČEHO
CALLERS=$(grep -rn "${FUNCTION_NAME}(" "${CODE_ROOT}" --include="*.py" | grep -v "^[^:]*def ${FUNCTION_NAME}")

if [ -z "$CALLERS" ]; then
  # Nikdo to nevolá → DEAD_CODE
  CLASSIFICATION="DEAD_CODE"
  INTAKE_TYPE="Chore"
  ACTION="Remove or document why exists"
else
  # Krok 2: Zjisti, zda je volající z test souborů POUZE
  TEST_ONLY=$(echo "$CALLERS" | grep -E "(tests/|test_|_test\.py)" | wc -l)
  TOTAL=$(echo "$CALLERS" | wc -l)

  if [ "$TEST_ONLY" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    # Volá se jen z testů → INTERNAL_ONLY (test helper)
    CLASSIFICATION="INTERNAL_ONLY"
    ACTION="Correct — test helper, no intake item needed"
  else
    # Krok 3: Zjisti, zda všechny callery jsou v process-map contract_modules
    UNDOCUMENTED=0
    while IFS= read -r caller_line; do
      CALLER_FILE=$(echo "$caller_line" | cut -d: -f1)
      # Normalizuj cestu (odstran CODE_ROOT prefix)
      CALLER_FILE=$(echo "$CALLER_FILE" | sed "s|${CODE_ROOT}/||")

      # Najdi, zda je soubor v contract_modules nějakého procesu
      if ! grep -q "$CALLER_FILE" "${WORK_ROOT}/fabric/processes/process-map.md" 2>/dev/null; then
        UNDOCUMENTED=$((UNDOCUMENTED + 1))
      fi
    done <<< "$CALLERS"

    if [ "$UNDOCUMENTED" -gt 0 ]; then
      CLASSIFICATION="UNDOCUMENTED"
      ACTION="Extend process-map (add calling chain), or reclassify as INTERNAL_ONLY if helper"
    else
      CLASSIFICATION="DOCUMENTED"
      ACTION="Function is properly in process chain — no action"
    fi
  fi
fi

echo "Function: ${FUNCTION_NAME} → Classification: ${CLASSIFICATION}"
echo "  Callers: $(echo "$CALLERS" | wc -l) found"
echo "  Action: ${ACTION}"
```

## P4: Runtime Validation — Test Coverage Check

```bash
# Test command from config
COMMANDS_TEST=$(grep 'test:' "{WORK_ROOT}/config.md" | head -1 | awk '{$1=""; print $0}' | xargs)
if [ -n "$COMMANDS_TEST" ] && [ "$COMMANDS_TEST" != "TBD" ]; then
  timeout 300 $COMMANDS_TEST -x --tb=line -q 2>&1 | tail -20
  TEST_EXIT=$?
  echo "Test exit code: $TEST_EXIT"
else
  echo "WARN: No test command configured — skip runtime validation"
fi
```

## P4: Test Coverage Verification Per Process

```bash
for MODULE in ${CONTRACT_MODULES}; do
  TEST_FILE=$(echo "$MODULE" | sed 's|/|_|g' | sed 's|\.py$||')
  if find "${TEST_ROOT}" -name "*${TEST_FILE}*" -o -name "test_${TEST_FILE}*" 2>/dev/null | grep -q .; then
    echo "✓ Process module $MODULE has tests"
  else
    echo "⚠ Process module $MODULE — no matching test file found"
  fi
done
```

## P4: Stub Detection in Contract Modules

```bash
for MODULE in ${CONTRACT_MODULES}; do
  STUBS=$(grep -cnE '^\s*(pass|raise NotImplementedError|# TODO|# FIXME)' "${CODE_ROOT}/${MODULE}" 2>/dev/null || echo 0)
  if [ "$STUBS" -gt 0 ]; then
    echo "⚠ Process module $MODULE contains $STUBS stubs/TODOs"
  fi
done
```

## P5: Intake Item Creation

```bash
# Pro každý orphan/gap:
python skills/fabric-init/tools/fabric.py intake-new \
  --source "process" \
  --slug "{type}-{process-id}" \
  --title "{Popis problému}"
```

## Quality Gate 2: Route Coverage Calculation (WQ10)

```bash
# Počet routes v kódu vs. počet external processes v mapě
CODE_ROUTES=$(grep -rE '@router\.(get|post|put|delete|patch)' "${CODE_ROOT}/api/routes/" --include="*.py" 2>/dev/null | wc -l)
MAP_EXTERNALS=$(grep -c "^| ext-" "$PROCESS_MAP" 2>/dev/null || echo 0)
COVERAGE=$((MAP_EXTERNALS * 100 / CODE_ROUTES))

if [ "$COVERAGE" -ge 80 ]; then
  echo "PASS: $COVERAGE% routes documented ($MAP_EXTERNALS / $CODE_ROUTES)"
else
  echo "FAIL: $COVERAGE% routes covered (<80% threshold) — create intake item + return FAIL"
fi
```

## Quality Gate 3: Duplicate Process ID Detection

```bash
DUPES=$(grep "^id:" {WORK_ROOT}/fabric/processes/*.md 2>/dev/null | awk '{print $2}' | sort | uniq -d)
if [ -z "$DUPES" ]; then
  echo "PASS: No duplicate process IDs"
else
  echo "FAIL: Duplicate IDs: $DUPES"
fi
```

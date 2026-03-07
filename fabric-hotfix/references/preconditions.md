# Preconditions Detailed Check

## Temporal Causality Guards

```bash
# --- Precondition 1: Config existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: State existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 3: COMMANDS.test je nakonfigurovaný ---
TEST_CMD=$(grep 'test:' "{WORK_ROOT}/config.md" | head -1 | sed 's/.*test:\s*//')
if [ -z "$TEST_CMD" ] || [ "$TEST_CMD" = "TBD" ]; then
  echo "STOP: COMMANDS.test not configured — hotfix needs tests"
  exit 1
fi

# --- Precondition 4: Git working tree čistý ---
if [ -n "$(git status --porcelain)" ]; then
  echo "STOP: dirty working tree — commit or stash first"
  exit 1
fi

# --- Precondition 5: Effort guard (user input) ---
# Pokud user nedal explicitní effort, zeptej se.
# Akceptuj jen XS nebo S. Pokud M+ → STOP s doporučením sprint.
EFFORT="${HOTFIX_EFFORT:-XS}"
case "$EFFORT" in
  XS|S) echo "Effort: $EFFORT — OK for hotfix" ;;
  M|L|XL) echo "STOP: effort $EFFORT is too large for hotfix — use fabric-sprint"; exit 1 ;;
  *) echo "WARN: unknown effort '$EFFORT', assuming XS" ; EFFORT="XS" ;;
esac
```

## Dependency Chain

```
fabric-init → [fabric-hotfix] (bez dalších prereqs)
```

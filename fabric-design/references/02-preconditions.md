# §3 Preconditions — Detailed Validation

## Precondition 1: Config existuje

```bash
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi
```

## Precondition 2: State existuje

```bash
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi
```

## Precondition 3: Backlog item existuje

```bash
TASK_ID="${1:?STOP: task ID required — usage: fabric-design <TASK_ID>}"
SAFE_ID=$(echo "${TASK_ID}" | sed 's/[^a-zA-Z0-9_-]//g')
if [ "$SAFE_ID" != "${TASK_ID}" ]; then
  echo "WARN: task ID sanitized: '${TASK_ID}' → '$SAFE_ID'"
  TASK_ID="$SAFE_ID"
fi

if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  echo "STOP: backlog file not found: backlog/${TASK_ID}.md — run fabric-intake first"
  exit 1
fi
```

## Precondition 4: Task status je DESIGN nebo READY

```bash
ITEM_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | head -1 | awk '{print $2}')
case "$ITEM_STATUS" in
  DESIGN|READY|IDEA) echo "Status: $ITEM_STATUS — OK for design" ;;
  IN_PROGRESS|IN_REVIEW|DONE)
    echo "STOP: task ${TASK_ID} has status ${ITEM_STATUS} — design phase already passed"
    exit 1
    ;;
  *) echo "WARN: unknown status '$ITEM_STATUS', proceeding" ;;
esac
```

## Precondition 5: Zdrojový kód existuje

```bash
if [ ! -d "{CODE_ROOT}" ]; then
  echo "WARN: {CODE_ROOT}/ not found — design will be theoretical (no code to inspect)"
fi
```

## Precondition 6: Governance artefakty

```bash
if [ ! -f "{WORK_ROOT}/decisions/INDEX.md" ]; then
  echo "WARN: decisions/INDEX.md not found — governance check will be skipped"
fi
```

## Dependency Chain

```
fabric-init → fabric-intake → fabric-prio → [fabric-design] → fabric-analyze → fabric-implement
```

All preconditions must pass before proceeding to design work. Fail-fast on mandatory checks (1–3), fail-open on optional checks (5–6).

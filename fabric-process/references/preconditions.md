# Preconditions & Configuration — fabric-process

This file contains detailed precondition checks and configuration steps from §2–§6 of the main SKILL.md.

## Protocol Logging (§2 — povinné)

### START Event
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "process" \
  --event start
```

### END Event (OK/WARN/ERROR)
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "process" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md"
```

### ERROR Event (pokud STOP/CRITICAL)
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "process" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

## Precondition Checks (§3)

### Precondition 1: Config File Exists
```bash
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi
```

### Precondition 2: State File Exists
```bash
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi
```

### Precondition 3: CODE_ROOT Exists with Python Files
```bash
CODE_ROOT=$(grep 'CODE_ROOT:' "{WORK_ROOT}/config.md" | awk '{print $2}' | tr -d '"')
if [ ! -d "${CODE_ROOT}" ]; then
  echo "STOP: CODE_ROOT '${CODE_ROOT}' not found"
  exit 1
fi

PYTHON_COUNT=$(find "${CODE_ROOT}" -name "*.py" -type f 2>/dev/null | wc -l)
if [ "$PYTHON_COUNT" -eq 0 ]; then
  echo "STOP: No Python files found in CODE_ROOT"
  exit 1
fi
```

### Precondition 4: Create Processes Directory
```bash
mkdir -p "{WORK_ROOT}/fabric/processes"
```

### Precondition 5: Vision File (Optional with Warning)
```bash
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "WARN: vision.md missing — process extraction will be codebase-only (no vision cross-reference)"
fi
```

## Dependency Chain

```
fabric-init → fabric-architect → [fabric-process] → fabric-gap
```

## Required Inputs (§4)

### Mandatory
- `{WORK_ROOT}/config.md` — cesty, schémata, příkazy
- `{WORK_ROOT}/state.md` — aktuální fáze/krok
- `{CODE_ROOT}/` — zdrojový kód (Python soubory: routes, services, models, storage)

### Optional (enrich output)
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` — reference pro vnější procesy (plánované features)
- `{WORK_ROOT}/fabric/processes/process-map.md` — předchozí verze (pro delta detekci)
- `{DECISIONS_ROOT}/*.md` — ADR odkazující na procesy
- `{SPECS_ROOT}/*.md` — specifikace (zejména LLMEM_API_V1, LLMEM_RECALL_PIPELINE_V1)
- `{TEST_ROOT}/` — testovací soubory (pro validaci pokrytí procesů testy)
- `{WORK_ROOT}/intake/` — pending items se source=implement (korekční mechanismus)

## Output Artifacts (§5)

### Primary (always)
- `{WORK_ROOT}/fabric/processes/process-map.md` (schema: `fabric.process-map.v1`) — Master dokument
- Report: `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Secondary (conditional)
- `{WORK_ROOT}/fabric/processes/{process-id}.md` (schema: `fabric.process.v1`) — Individuální procesy (1 soubor per proces)
- Intake items: `{WORK_ROOT}/intake/process-{slug}.md` (schema: `fabric.intake_item.v1`) — pro nalezené orphany/gapy

## Process Map Contract Schema

```yaml
schema: fabric.process-map.v1
version: "1.0"
created: YYYY-MM-DD
updated: YYYY-MM-DD
validation_status: VALID | STALE
external_count: int
internal_count: int
external_processes: [{id, actor, trigger, entry_point, output, status}]
internal_processes: [{id, trigger, call_chain, dependencies, side_effects}]
orphans: [{type, name, classification, action}]
```

## FAST PATH: Deterministic Index Sync (§6)

### 1. Backlog Index Sync
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```

### 2. Governance Index Sync
```bash
python skills/fabric-init/tools/fabric.py governance-index
```

These commands populate indices used for downstream analysis and cross-referencing.

# §2 Protocol — Detailed Implementation

## START Protocol

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "design" \
  --event start
```

## END Protocol (OK/WARN/ERROR)

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "design" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md"
```

## ERROR Protocol (if STOP/CRITICAL)

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "design" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

Protocol logging is MANDATORY and must not be shortened. Every design run must have START and END entries logged.

---
id: migration-{YYYY-MM-DD}-{NN}
schema: fabric.report.v1
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "init"
step: "init"
run_id: "{RUN_ID}"
source_path: "{LEGACY_ROOT}"
target_path: "{WORK_ROOT}"
mode: "bootstrap|upgrade|consolidation"
summary: "{1-3 sentences}"

counts:
  intake_created: 0
  backlog_created: 0
  backlog_updated: 0
  archived: 0

integrity:
  schema: "PASS|FAIL"
  references: "PASS|FAIL"
  duplicates: "PASS|FAIL"

notes: ""
---

# Migration Report

Tento report je výstup `fabric-init` při migraci z legacy.  
Cíl: auditovatelný záznam **co se převedlo**, **co se přeskočilo** a **co vyžaduje follow-up**.

## Provenance mapping

| New ID | Legacy ref | Action | Notes |
|--------|------------|--------|-------|
| {new_id} | {LEGACY_ROOT}/{path} | created|updated|archived| {reason} |

## Follow-ups (next actions)

- [ ] {action} (prio: {P0..P3})
- [ ] {action} (prio: {P0..P3})

## Exceptions / warnings

- {warning}

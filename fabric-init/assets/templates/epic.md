---
id: epic-{slug}
schema: fabric.backlog_item.v1
title: "{EPIC_TITLE}"
type: Epic
tier: T0 | T1 | T2 | T3
status: IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE
effort: XL
created: "{YYYY-MM-DD}"
updated: "{YYYY-MM-DD}"
source: manual | generate | gap | arch | review | check | intake
prio: 0
depends_on: []
blocked_by: []
branch: null
review_report: null
merge_commit: null
---

## Příkaz odemykující
{WHY_IN_ONE_SENTENCE}

## Popis
{WHAT_AND_CONTEXT}

## Success / Outcome
{BUSINESS_OR_TECH_OUTCOME}

## Acceptance Criteria
- [ ] {AC_1}
- [ ] {AC_2}
- [ ] {AC_3}

## Scope
### In scope
- {IN_SCOPE}

### Out of scope
- {OUT_OF_SCOPE}

## Breakdown
> Epik je kontejner. Implementace probíhá přes Stories/Tasks (WIP=1).

### Stories
- [ ] {story-id} — {title}

### Tasks
- [ ] {task-id} — {title}

## Závislosti
- Depends on: {IDs}
- Blocked by: {IDs}

## Poznámky
{NOTES}

## Provenance (volitelné)
- Legacy ID: {LEGACY_ID_OR_EMPTY}
- Migrated at: {YYYY-MM-DD}

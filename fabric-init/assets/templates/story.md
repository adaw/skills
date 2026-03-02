---
id: story-{slug}
schema: fabric.backlog_item.v1
title: "{STORY_TITLE}"
type: Story
tier: T0 | T1 | T2 | T3
status: IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE
effort: L
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

## Uživatelský příběh
Jako **{ROLE}** chci **{NEED}**, aby **{BENEFIT}**.

## Kontext
{CONTEXT}

## Acceptance Criteria
- [ ] {AC_1}
- [ ] {AC_2}
- [ ] {AC_3}

## Task breakdown (doplní se v analyze)
- [ ] {task-id} — {title}

## Dotčené oblasti
- `{CODE_ROOT}/...`
- `{TEST_ROOT}/...`
- `{DOCS_ROOT}/...`

## Závislosti
- Depends on: {IDs}
- Blocked by: {IDs}

## Poznámky k designu
{DESIGN_NOTES}

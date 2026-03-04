---
id: task-{slug}
schema: fabric.backlog_item.v1
title: "{TASK_TITLE}"
type: Task
tier: T0 | T1 | T2 | T3
status: IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE
effort: M
created: "{YYYY-MM-DD}"
updated: "{YYYY-MM-DD}"
source: manual | generate | gap | arch | review | check | intake
prio: 0
depends_on: []
blocked_by: []
linked_vision_goal: ""
branch: null
review_report: null
merge_commit: null
---

## Příkaz odemykující
{WHY_IN_ONE_SENTENCE}

## Popis
{WHAT_NEEDS_TO_CHANGE}

## Acceptance Criteria
- [ ] {AC_1}
- [ ] {AC_2}
- [ ] {AC_3}
- [ ] Testy PASS (COMMANDS.test)
- [ ] Lint + format check PASS (COMMANDS.lint + COMMANDS.format_check)

## Dotčené soubory
- `{CODE_ROOT}/...` — {CHANGE}
- `{TEST_ROOT}/...` — {TESTS}
- `{DOCS_ROOT}/...` — {DOCS}

## Test plan
- Unit: {WHAT}
- Integration: {WHAT}
- Edge cases: {WHAT}

## Implementační poznámky
{CONSTRAINTS_AND_HINTS}

## Závislosti
- Depends on: {IDs}
- Blocked by: {IDs}

## Evidence (doplní se v close)
- Review report: {reports/...}
- Merge commit: {sha}

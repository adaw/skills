---
id: SPRINT-{YYYY}-{NNN}
schema: fabric.sprint_plan.v1
sprint: "{N}"
title: "{SPRINT_TITLE}"
goal: "{SPRINT_GOAL}"
start: "{YYYY-MM-DD}"
end: "{YYYY-MM-DD}"
created: "{YYYY-MM-DD}"
max_tasks: "{MAX_TASKS}"
wip_limit: "{WIP_LIMIT}"
---

# Sprint {N} — {SPRINT_TITLE}

**Goal:** {SPRINT_GOAL}  
**Start:** {YYYY-MM-DD}  
**End:** {YYYY-MM-DD}

## Sprint Targets
> Vybrané backlog položky. Může obsahovat Epic/Story/Task.
>
> `fabric-analyze` může podle potřeby rozpadnout cíle na konkrétní tasks a doplnit/aktualizovat `Task Queue`.

| ID | Title | Type | Tier | Effort | PRIO | Status |
|----|-------|------|------|--------|------|--------|
| {id} | {title} | {type} | {tier} | {effort} | {prio} | {status} |

## Task Queue
> **Autoritativní seznam pro implementaci (WIP=1, pořadí = Order).**
> Po analýze zde musí být pouze: `Task | Bug | Chore | Spike`.
>
> Implementace (`fabric-implement`) bere vždy první item, který není `DONE`.

| Order | ID | Title | Type | Effort | Status | Depends on |
|------:|----|-------|------|--------|--------|------------|
| 1 | {task-id} | {task-title} | Task | M | READY | {ids or empty} |

## Notes
{NOTES}

## Risks
- {RISK_1}
- {RISK_2}

## Definition of Done (Sprint)
- [ ] Všechny merged tasks mají PASS testy a CLEAN review
- [ ] Docs sync proběhl (DOCS step)
- [ ] CHECK report nemá CRITICAL findings

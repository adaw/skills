---
id: CLOSE-{YYYY}-{SPRINT_NUMBER}
schema: fabric.report.v1
sprint: "{SPRINT_NUMBER}"  # string-safe
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "close"
step: "close"
run_id: "{RUN_ID}"
close_by: "{AGENT_OR_OWNER}"
---

# Sprint Close Report — Sprint {SPRINT_NUMBER} ({YYYY-MM-DD})

## Sprint meta
- Goal: {SPRINT_GOAL}
- Start: {YYYY-MM-DD}
- End: {YYYY-MM-DD}

## Summary
{EXECUTIVE_SUMMARY}

## Completed & merged (DONE)
> Položky, které byly squash-merged do `main` a mají evidenci (tests + review).

| ID | Title | Type | Effort | Merge commit | Review report |
|----|-------|------|--------|-------------|--------------|
| {id} | {title} | {type} | {effort} | {sha} | {reports/review-...} |

## Carry-over (not merged)
> Položky, které byly ve sprint plánu, ale nejsou mergnuté (zůstávají aktivní).

| ID | Title | Status | Reason | Next action |
|----|-------|--------|--------|------------|
| {id} | {title} | IN_REVIEW | Tests fail on main | Rework + rerun COMMANDS.test |

## Not started
| ID | Title | Status | Reason |
|----|-------|--------|--------|
| {id} | {title} | READY | Capacity |

## Blocked
| ID | Title | Blocked by | Notes |
|----|-------|------------|-------|
| {id} | {title} | {blocked_by} | {notes} |

## Quality evidence
- Tests command: `{COMMANDS.test}`
- Lint command: `{COMMANDS.lint}`
- Format check: `{COMMANDS.format_check}`

### Test status
- Result: {PASS/FAIL}
- Evidence: {reports/test-...}

### Lint/format status
- Lint: {PASS/FAIL}
- Format check: {PASS/FAIL}

## Velocity
- Planned tasks: {N}
- Merged tasks: {N}
- Carry-over: {N}

## Lessons learned
- {LESSON_1}
- {LESSON_2}

## Action items for next sprint
- [ ] {ACTION_1}
- [ ] {ACTION_2}

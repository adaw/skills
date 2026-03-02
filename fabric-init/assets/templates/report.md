---
id: REPORT-{YYYY}-{NNN}
schema: fabric.report.v1
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "{KIND}"           # logical report kind (usually matches STEP)
skill: "{SKILL_NAME}"
run_id: "{RUN_ID}"
phase: "{PHASE}"
step: "{STEP}"
sprint: "{SPRINT_NUMBER}"   # string-safe (tools mohou převést na int)
status: "{STATUS}"          # OK | WARN | ERROR
wip_item: "{WIP_ITEM}"
wip_branch: "{WIP_BRANCH}"
links:
  state: "{WORK_ROOT}/state.md"
  config: "{WORK_ROOT}/config.md"
  backlog: "{WORK_ROOT}/backlog/"
  reports: "{WORK_ROOT}/reports/"
---

# {SKILL_NAME} — Report ({YYYY-MM-DD})

## Summary

- **Outcome:** {one-line outcome}
- **Key decision:** {what was decided}
- **Confidence:** {HIGH|MED|LOW}

## Inputs

- {inputs read: files, commands, assumptions}

## Actions

1) {what was done}

## Outputs

- {files written/updated}

## Evidence

- {test results, metrics, links}

## Risks & Follow-ups

- {risk}
- {follow-up}

## Next

- **Next step:** {NEXT_STEP}

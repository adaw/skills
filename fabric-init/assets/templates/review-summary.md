---
id: REVIEW-{YYYY}-{NNN}
schema: fabric.report.v1
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "review"
step: "review"
run_id: "{RUN_ID}"
item_id: "{WIP_ITEM}"
branch: "{WIP_BRANCH}"
reviewed_by: "{AGENT_OR_REVIEWER}"
lint: "PASS|FAIL|SKIPPED"
format_check: "PASS|FAIL|SKIPPED"
verdict: "CLEAN|REWORK|REDESIGN"
---

# Review Report — {WIP_ITEM} ({YYYY-MM-DD})

## Gates
- Lint: {PASS/FAIL/SKIPPED}
- Format check: {PASS/FAIL/SKIPPED}

## Verdict
**{CLEAN|REWORK|REDESIGN}**

- CLEAN = ready for CLOSE (merge)
- REWORK = go back to IMPLEMENT
- REDESIGN = escalate to ANALYZE (arch change needed)

## Diff summary
- Files changed: {N}
- Tests touched: {YES/NO}
- Docs touched: {YES/NO}

## R1–R8 scores (0–5)

| Dim | Name | Score | Notes |
|-----|------|------:|-------|
| R1 | Correctness | {0-5} | ... |
| R2 | Security | {0-5} | ... |
| R3 | Performance | {0-5} | ... |
| R4 | Reliability | {0-5} | ... |
| R5 | Testability | {0-5} | ... |
| R6 | Maintainability | {0-5} | ... |
| R7 | Documentation | {0-5} | ... |
| R8 | Compliance | {0-5} | ... |

## Findings

### CRITICAL (must fix)
- {finding}

### HIGH
- {finding}

### MEDIUM
- {finding}

### LOW
- {finding}

## Systemic improvements (intake items)
- {WORK_ROOT}/intake/review-...md

## Suggested next step
- {NEXT_STEP}

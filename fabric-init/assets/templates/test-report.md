---
# Test report (used by fabric-test)
# Required for deterministic gating: must contain a single line:
#   - Result: PASS | FAIL
#
# NOTE: Use {RESULT} placeholder to keep this file usable for both
# deterministic tooling (fabric.py gate-test) and manual completion.
id: TEST-{YYYY}-{NNN}
schema: fabric.report.v1
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "test"
step: "test"
skill: "{SKILL_NAME}"
run_id: "{RUN_ID}"
wip_item: "{WIP_ITEM}"
wip_branch: "{WIP_BRANCH}"
status: "{STATUS}"
---

# Test Report — {WIP_ITEM} ({YYYY-MM-DD})

- Result: {RESULT}
- Command: "{TEST_COMMAND}"
- Log: "{LOG_PATH}"
- Duration_s: {DURATION_S}
- Scope: unit|integration|lint|format|other

## Notes

## Failures (if any)

## Next
- If PASS: proceed to review
- If FAIL: proceed to implement (fix)

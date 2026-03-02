---
id: AUDIT-{YYYY}-{NNN}
schema: fabric.report.v1
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "check"
step: "check"
run_id: "{RUN_ID}"
audit_type: scheduled | on_demand | targeted
audited_by: "{AGENT_OR_OWNER}"
duration_minutes: "{N}"
items_checked: "{N}"
---

# Consistency Audit Report — {YYYY-MM-DD}

## Scope
- Work root: `{WORK_ROOT}/`
- Code root: `{CODE_ROOT}/`
- Docs root: `{DOCS_ROOT}/`
- Tests root: `{TEST_ROOT}/`

## Summary
- Overall score: {0-100}
- CRITICAL findings: {N}
- WARNING findings: {N}
- Auto-fixes applied: {N}
- Intake items created: {N}

## Status distribution (backlog)
| Status | Count | Note |
|--------|------:|------|
| IDEA | {N} | |
| DESIGN | {N} | |
| READY | {N} | |
| IN_PROGRESS | {N} | |
| IN_REVIEW | {N} | |
| BLOCKED | {N} | |
| DONE | {N} | |

## Findings

### CRITICAL
| # | Area | Evidence | Why it matters | Suggested fix |
|---:|------|----------|----------------|---------------|
| 1 | Backlog index | backlog.md missing rows | Orchestrator can’t plan reliably | Rebuild backlog.md |

### WARNING
| # | Area | Evidence | Suggested fix |
|---:|------|----------|---------------|
| 1 | Docs drift | {DOCS_ROOT}/foo.md outdated | Run fabric-docs |

### NOTE
- {NOTE}

## Auto-fixes
- {AUTO_FIX_1}

## Intake items created
- {WORK_ROOT}/intake/check-{YYYY-MM-DD}-{slug}.md

## Appendix
- Commands used (if any)
- Sampling strategy

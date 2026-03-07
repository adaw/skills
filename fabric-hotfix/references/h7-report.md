# H7: Report — Detailní procedura

## Cíl
Hotfix report se souhrnem evidence.

## Report Template

```md
---
schema: fabric.report.v1
kind: hotfix
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
task_id: "{TASK_ID}"
effort: "{XS|S}"
merge_commit: "{SHA}"
---

# Hotfix Report — {YYYY-MM-DD}

## Souhrn
{1–3 věty co hotfix udělal}

## Evidence
| Gate | Výsledek |
|------|----------|
| Lint | {PASS/FAIL/SKIPPED} |
| Format | {PASS/FAIL/SKIPPED} |
| Tests (pre-merge) | {PASS/FAIL} |
| Tests (post-merge) | {PASS/FAIL} |
| Self-review | {4/4 dimenze OK} |

## Změněné soubory
{git diff --stat output}

## Backlog
- ID: {TASK_ID}
- Status: DONE
- Merge commit: {SHA}

## Warnings
{Seznam nebo "žádné"}
```

## Report Location
`{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md`

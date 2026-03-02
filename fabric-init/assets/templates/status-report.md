---
schema: fabric.report.v1
template: status-report
version: 1.0
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "status"
step: "status"
run_id: "{RUN_ID}"
---

# Project Health Report — {YYYY-MM-DD}

## Overall Health Score: {score}/10

**Status:** {HEALTHY|CAUTION|AT_RISK} — **Trend:** {delta} {↑|→|↓}

score = (test_health × 0.25) + (code_quality × 0.25) + (backlog_shape × 0.25) + (velocity_trend × 0.25)

---

## Metrics Dashboard

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Python files | {N} | growing | {OK/WARN} |
| Total LOC | {K} | managed | {OK/WARN} |
| Type hints | {X}% | >80% | {OK/WARN} |
| Lint issues | {N} | <10 | {OK/WARN} |
| Test files | {N} | trending | {OK/WARN} |
| Test count | {M} | trending | {OK/WARN} |
| Pass rate | {X}% | >95% | {OK/WARN} |
| Coverage | {Y}% | >80% | {OK/WARN} |
| Backlog items | {N} | managed | {OK/WARN} |
| Actionable | {X}% | >50% | {OK/WARN} |
| T0 items | {count} | 10-20% | {OK/WARN} |
| Velocity | {Z}/sprint | stable | {OK/WARN} |

---

## Trends (Last 3 sprints)

```
Test pass rate:     [{A}%, {B}%, {C}%] → {IMPROVING|STABLE|DECLINING}
Backlog actionable: [{A}%, {B}%, {C}%] → {IMPROVING|STABLE|DECLINING}
Velocity:           [{A}, {B}, {C}]    → {IMPROVING|STABLE|DECLINING}
Type hints:         [{A}%, {B}%, {C}%] → {IMPROVING|STABLE|DECLINING}
Lint issues:        [{A}, {B}, {C}]    → {IMPROVING|STABLE|DECLINING}
```

---

## Risk Radar

| Risk | Count | Severity | Action |
|------|-------|----------|--------|
| Blocked items | {N} | {HIGH/MED/LOW} | Resolve blockers |
| Test gaps | {N} | {HIGH/MED/LOW} | Add test plans |
| Unassigned READY | {N} | {HIGH/MED/LOW} | Assign to sprint |
| Dependencies | {N} | {MANAGEABLE/COMPLEX} | Map & resolve |

---

## Key Insights & Actions

1. {Top issue}: {current} → {target}. **Action:** {recommendation}
2. {Strong area}: {metric} improving. **Keep:** {what's working}

---

## Immediate Actions (before next sprint)

- {if test_pass < 90%} Debug failing tests
- {if blocked > 0} Resolve blockers
- {if lint > 10} Clean lint violations

---

**Data Sources:** Code: {CODE_ROOT}/ | Tests: {TEST_ROOT}/ | Backlog: {WORK_ROOT}/backlog/ | Docs: {DOCS_ROOT}/
**Generated:** {TODAY} | **Next run:** Daily

# §9 Report — Complete Template

Create this report after design completes: `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md`

## Report Template

```markdown
---
schema: fabric.report.v1
kind: design
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
task_id: "{TASK_ID}"
design_spec: "{ANALYSES_ROOT}/{TASK_ID}-design.md"
---

# Design Report — {TASK_ID}

## Summary

{1–3 sentences: What was designed? What is the outcome? Any blockers?}

Example:
> Designed database schema for audit log feature with 4 new tables and migration strategy.
> Design is complete and ready for implementation. Two risks identified: performance at scale
> and data retention policy (intake item created).

## Design Specification

**Path:** `{ANALYSES_ROOT}/{TASK_ID}-design.md`

**Completeness:** {N}/8 sections (D1–D8)

**Quality gates status:**
- [ ] ✓ Gate 1: All 8 sections present
- [ ] ✓ Gate 2: Pseudokód present for complex logic
- [ ] ✓ Gate 3: Test cases concrete (≥3 per component)
- [ ] ✓ Gate 4: Alternatives documented (≥2)
- [ ] ✓ Gate 5: Governance aligned

## Governance

### Applied Constraints

**ADR constraints:**
- {ADR-001}: {constraint and how design respects it}
- {ADR-NNN}: {constraint}
- Or: "None found"

**SPEC constraints:**
- {SPEC-001}: {constraint}
- Or: "None found"

### Conflicts Identified

- {Conflict 1}: Design {does/does not respect} {constraint reason}. {Resolution or intake item created}
- Or: "None"

## Risks

### Top 2 Risks (from D7)

1. **{Risk title}** — {HIGH/MEDIUM/LOW} impact
   - Mitigation: {action to prevent or detect}

2. **{Risk title}** — {HIGH/MEDIUM/LOW} impact
   - Mitigation: {action}

See design spec D7 for complete risk analysis.

## Design Summary (Key Sections)

### Data Model (D2)
- {N} new entities: {list}
- {M} modified entities: {list}
- Migration strategy: {simple/complex/requires downtime}

### Components (D3)
- {N} new classes/services: {list}
- {M} new endpoints: {list}

### Integration (D4)
- Integration points: {count}
- Side effects: {count} (cache invalidation, event publishing, etc.)

### Testing Strategy (D6)
- Estimated test cases: {N}
- Coverage estimate: {%}

## Recommended Next Steps

**If design PASS:**
- Run `fabric-analyze` to break down into sprint-sized tasks
- Or run `fabric-implement` to code directly (if single task)

**If design WARN:**
- Address warnings before implementation
- Create intake items for clarifications
- Keep task in DESIGN status until resolved

**If design FAIL:**
- Fix critical issues (missing sections, conflicts, etc.)
- Re-run quality gates
- Return to DESIGN status

## Intake Items Created

{List of new intake items, or "None"}

Example:
- `intake/design-clarification-{id}.md` — Ambiguity in {field}: {description}
- `intake/design-adr-amendment.md` — Governance conflict with ADR-001

## Warnings/Notes

{List of warnings, or "None"}

Example:
- ⚠ Code not found at {CODE_ROOT} — design is theoretical
- ⚠ Performance impact identified for {operation}: {description}
- ⚠ Dependency on {task_id} not yet started

---

## Metadata

- **Skill:** fabric-design
- **Run ID:** {run_id}
- **Created:** {timestamp}
- **Task ID:** {TASK_ID}
- **Status:** {PASS|WARN|FAIL}
```

## Report Quality Checklist

- [ ] All metadata present (schema, kind, run_id, created_at, status)
- [ ] Summary is 1–3 sentences and answers: what, outcome, blockers
- [ ] Design spec path and completeness clearly stated
- [ ] All 5 quality gates referenced
- [ ] Governance section lists all ADRs/SPECs (or explicitly "none")
- [ ] Top 2 risks from D7 listed with mitigation
- [ ] Recommended next step is clear (analyze or implement)
- [ ] All intake items created are listed
- [ ] All warnings documented

## Report Examples

### PASS Report

```markdown
---
schema: fabric.report.v1
kind: design
run_id: "design-20260307-abc123"
created_at: "2026-03-07T14:30:00Z"
status: PASS
task_id: "FEAT-42"
design_spec: "analyses/FEAT-42-design.md"
---

# Design Report — FEAT-42

## Summary

Designed distributed caching layer with Redis integration and fallback to in-memory cache.
All 8 design sections complete. Ready for implementation immediately.

## Quality Gates Status

- ✓ Gate 1: All 8 sections (D1–D8) present and substantive
- ✓ Gate 2: Pseudokód present for 3 complex algorithms
- ✓ Gate 3: 15 test cases specified (5 per component)
- ✓ Gate 4: 2 alternatives analyzed (Redis + in-memory vs. pure Redis)
- ✓ Gate 5: No governance conflicts identified

## Design Summary

**Data Model:** 1 new Config model, 0 modified
**Components:** 2 new classes (CacheLayer, FallbackStore)
**Integration:** 5 integration points with existing services
**Tests:** 15 test cases covering happy path, edge cases, error handling
```

### WARN Report

```markdown
---
status: WARN
---

# Design Report — FEAT-43

## Summary

Design mostly complete but 1 clarification needed on encryption key rotation policy.
Created intake item for governance team. Recommend review before implementation.

## Warnings

- ⚠ Encryption key rotation policy not defined in design — depends on ADR-15 amendment (in progress)
- ⚠ Performance impact of {operation} under high load not fully analyzed — recommend load testing phase

## Recommended Next Steps

1. ADR-15 amendment approved by governance
2. Create intake item: `intake/design-clarification-crypto-rotation.md`
3. Then proceed to implementation
```

See main SKILL.md for integration with §10 Self-Check and §11 Failure Handling.

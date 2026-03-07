# §11 Failure Handling — Decision Tree

Use this table to diagnose and resolve design failures. Find your error, then follow the action.

## Failure Decision Matrix

### Precondition Failures (Phase: Prerequisites)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| Preconditions | Backlog item file not found | Task ID doesn't exist in backlog/ | **STOP.** Run `fabric-intake` first to add task to backlog. |
| Preconditions | Status is IN_PROGRESS or DONE | Design phase already passed | **STOP.** Design cannot work on in-progress tasks. Ask project manager to move task back to READY/IDEA if revert needed. |
| Preconditions | Status is IDEA | Task not yet prioritized | **WARN.** Design can proceed, but implement after task gets priority score. Document in report. |
| Preconditions | Config file missing | fabric-init not run | **STOP.** Run `fabric-init {PROJECT_ID}` first to initialize workspace. |
| Preconditions | State file missing | Workspace not initialized | **STOP.** Run `fabric-init {PROJECT_ID}` to create state.md and config.md. |

### Context Phase Failures (D1: Understand Context)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D1 Kontext | Source code directory not found | {CODE_ROOT}/ doesn't exist | **WARN.** Design proceeds as theoretical (no code inspection). Document in report that design should be verified against actual code. Continue with caution. |
| D1 Kontext | Governance index not found | decisions/INDEX.md missing | **WARN.** Governance checks skipped. Document: "No governance constraints checked." Continue. May revisit after ADRs are created. |
| D1 Kontext | Test framework unclear | Multiple test patterns found | **WARN.** Pick dominant pattern (most files use this test style). Document choice in D6. Or create intake item for standardization. |
| D1 Kontext | Unclear acceptance criteria | AC in backlog is vague | **ACTION:** Create intake item `intake/design-clarification-{id}.md` describing ambiguity. Keep task in DESIGN status (not READY) until AC clarified. |

### Data Model Failures (D2: Design Data)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D2 Model | Entity types unclear | No clear data boundaries | **ACTION:** Create intake item describing ambiguity (e.g., "Is audit_log a separate entity or field in Transaction?"). Design best-guess approach but mark as tentative. Keep DESIGN status. |
| D2 Model | Migration path unclear | Modifying existing model but unclear how to migrate data | **ACTION:** Document assumption in D2: "Assumes {scenario}. If actual data doesn't match, backward compatibility {will break / requires migration script}." Create intake item if complex migration. |
| D2 Model | Too many entities | >10 new entities for 1 task | **ACTION:** This is scope creep. Create intake items to break into sub-tasks. Recommend: split task into {A: core model, B: related features}. Keep this task to core only. |

### Component Failures (D3: Design Components)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D3 Component | Pseudokód too vague | "Process data" without steps | **ACTION:** Expand pseudokód with numbered steps. Include: input, validation, transform, output, error cases. See references/06-procedure-d3-d4.md for template. |
| D3 Component | Logic too complex for 1 task | 500+ lines of pseudokód needed | **ACTION:** This is scope creep. Design can proceed but recommend breaking into sub-tasks: {A: core algorithm, B: integration, C: optimization}. Create intake item. |
| D3 Component | API contract conflicts with existing | Endpoint {method path} already exists | **ACTION:** Choose: (a) modify existing endpoint (breaking change?), or (b) design new endpoint with different path/version. Document choice and impact. If breaking change, create intake item for deprecation plan. |

### Integration Failures (D4: Design Integration)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D4 Integration | Integration points > 5 | Too many dependencies | **ACTION:** List all points. Assess risk: each point = integration complexity. Design mitigations (API contracts, versioning, fallbacks). Or recommend task split. |
| D4 Integration | Circular dependency detected | A calls B, B calls A | **STOP.** Circular dependencies are design errors. Re-architect to break cycle (e.g., via event queue, shared service, inversion of control). Do not proceed until resolved. |
| D4 Integration | Side effects unclear | "Cache will be invalidated somehow" | **ACTION:** For each side effect, document: (a) what changes, (b) when, (c) impact if not done. Create explicit action in pseudokód. E.g., "Cache.invalidate(key=user_id)" not "invalidate cache." |

### Configuration Failures (D5: Design Config)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D5 Config | Config key already exists | new_key name duplicates existing | **ACTION:** Use existing key if definition is compatible. If not compatible, rename new key to avoid collision (e.g., `{SECTION}_V2_{KEY}`). Or create intake item to deprecate old key. |
| D5 Config | Environment variable conflicts | Multiple keys map to same env var | **ACTION:** Ensure 1:1 mapping. Rename vars if needed. Document in D5. Test that config loading doesn't have collisions. |

### Testing Failures (D6: Design Tests)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D6 Test | Test is too generic | "test_works" with no specifics | **ACTION:** Rewrite test with concrete input/output. Template: `test_{component}_{scenario}` with "Input: {X}", "Expected: {Y}". See references/07-procedure-d5-d8.md. |
| D6 Test | Edge case coverage insufficient | Only happy path tested | **ACTION:** Add edge cases: empty inputs, boundary values, unicode, null, max length. Add error cases: invalid input, timeout, missing resource. |
| D6 Test | Fixture complex or missing | Test requires setup but unclear how | **ACTION:** Document fixture in test design. Specify: what data created, how, cleanup. Or use existing fixtures if available. Create intake item if new fixture needed. |
| D6 Test | Coverage estimate unrealistic | 5 new methods but only 3 tests | **ACTION:** For each method, add: happy path + 1 edge case + 1 error case (3 minimum). Revise coverage estimate. |

### Alternatives/Risk Failures (D7)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D7 Alternatives | Only 1 approach documented | "This is the only way" | **ACTION:** Brainstorm alternatives (see references/07-procedure-d5-d8.md for prompts). Find at least 2 other approaches. Compare trade-offs. If truly only 1 approach, justify exhaustively. |
| D7 Alternatives | Both alternatives have dealbreakers | A is slow, B is complex | **ACTION:** This signals design problem. Either (a) rethink from scratch, or (b) accept trade-off and document trade-off rationale explicitly. If unsolvable, create intake item and keep DESIGN status (not READY). |
| D7 Alternatives | Pro/con too vague | "Good", "Bad" without metrics | **ACTION:** Attach metrics: "Approach A saves 200ms vs Approach B" or "Approach A requires 3x code." See references/07-procedure-d5-d8.md for examples. |
| D7 Risk | No mitigations identified | Risks listed but no plans to address | **ACTION:** For each risk, add mitigation: (a) prevent it, (b) detect it, (c) recover from it. Example: Risk="cache miss", Mitigation="log miss rate; auto-warm cache on startup; fallback to DB query". |

### Dependency Failures (D8: Design Dependencies)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| D8 Dependencies | External library version wrong | Version too old/new or not available | **ACTION:** Check actual version available. Use `pip search {lib}` or pypi.org. Specify exact version that works. Test if possible. |
| D8 Dependencies | Internal task dependency not ready | Task B not done but task A depends on it | **ACTION:** Check {WORK_ROOT}/backlog status of dependency. If not DONE, implement anyway and create integration tests for when B finishes. Or create intake item to prioritize B. |
| D8 Dependencies | Implementation order creates deadlock | Task must be done before work on task, but task depends on task | **STOP.** Circular dependency is design error. Re-architect. Or split task to avoid cycle. |
| D8 Dependencies | Too many dependencies | > 5 external libraries needed | **ACTION:** List all. Assess: critical vs. optional vs. already-available. For optional ones, consider building vs. buy trade-off. Document rationale. |

### Governance Failures (Gate 5)

| Phase | Error | Root Cause | Action |
|-------|-------|-----------|--------|
| Gate 5 Governance | Design conflicts with accepted ADR | ADR-001 says "all APIs REST" but design uses GraphQL | **ACTION:** Create intake item: "ADR-001 amendment request: Allow GraphQL for {reason}". Keep task DESIGN status (not READY). Once ADR approved, mark READY. |
| Gate 5 Governance | Design violates active SPEC | SPEC-DataModel says "all IDs are UUID" but design uses int | **ACTION:** Either (a) align design with SPEC, or (b) create intake item to amend SPEC. If conflict fundamental, keep DESIGN status until resolved. |
| Gate 5 Governance | No ADR exists but design establishes precedent | Design introduces new architectural pattern | **ACTION:** Consider creating ADR draft to document decision (optional but good practice). Recommend in report: "Consider formalizing this pattern as ADR-NNN." Not a blocker. |

---

## General Rules

### Fail-Open vs Fail-Fast

- **FAIL-FAST (STOP immediately):**
  - Backlog item doesn't exist
  - Status is IN_PROGRESS or DONE
  - Circular dependencies
  - Critical governance conflict (violates law/security)

- **FAIL-OPEN (WARN, continue with caution):**
  - Source code not found (design proceeds theoretically)
  - Governance index not found (governance checks skipped)
  - Optional config missing
  - Vague requirements (create intake item, proceed)

### When to Create Intake Items

Create `intake/design-{slug}.md` for:
- Clarification needed on AC or requirements
- Governance conflict requiring ADR amendment
- Scope creep (task should be split)
- Data ambiguity (unclear entity boundaries)
- Complex migration strategy (needs DBA input)

### When to Keep DESIGN Status (not READY)

Keep task in DESIGN status (don't mark READY) if:
- Governance conflict exists (waiting for ADR approval)
- Critical clarification outstanding
- Major risk identified with no mitigation
- Alternative approaches equally valid (needs stakeholder decision)

### When to Proceed to READY

Mark READY only if:
- All 5 quality gates PASS
- No governance conflicts
- Self-check passes
- Intake items created for non-blocking issues

See main SKILL.md for integration with §2 Protocol and §10 Self-Check.

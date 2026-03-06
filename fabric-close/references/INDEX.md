# FABRIC-CLOSE REFERENCES INDEX

Quick navigation to detailed documentation.

## For Different Use Cases

### I need to run close for a sprint right now
1. Read `../SKILL.md` §1-§6 (what, protocol, preconditions, inputs, outputs, fast path)
2. Check `../SKILL.md` §7 POSTUP (7-step overview)
3. Jump to `workflow.md` for detailed step procedures as needed

### I'm learning how close works
1. Start with `../SKILL.md` §1-§6 (foundation)
2. Read `examples.md` Example 1 (successful T-TRI-02 merge)
3. Read `examples.md` Example 2-4 (carry-over scenarios)
4. Deep dive into `workflow.md` sections

### I hit a failure or error
1. Check `../SKILL.md` §11 FAILURE HANDLING (5 failure types)
2. See `workflow.md` "Error Recovery Checklist"
3. Find matching scenario in `examples.md`

### I need to implement close logic
1. Study `workflow.md` "Sequential Merge Loop" (10 steps)
2. Use `examples.md` as concrete reference for each step
3. Reference `workflow.md` safety guards (K1, K2, K7, etc.)

### I'm reviewing close code
1. Check `../SKILL.md` §3 PRECONDITIONS (validation logic)
2. Check `../SKILL.md` §8 QUALITY GATES (post-merge validation)
3. Check `workflow.md` "Task Classification" (MERGEABLE vs CARRY-OVER)

---

## Document Map

### SKILL.md (Main Orchestration)
- **Size:** 356 lines
- **Purpose:** Executive summary with §1-§12 structure
- **Key Sections:**
  - §1 ÚČEL: Purpose and invariants
  - §2 PROTOKOL: Protocol logging (bash)
  - §3 PRECONDITIONS: Validation checks (bash)
  - §4 VSTUPY: Required inputs
  - §5 VÝSTUPY: Expected outputs
  - §6 FAST PATH: Quick execution path
  - §7 POSTUP: Workflow overview (→ references)
  - §8 QUALITY GATES: Post-merge validation
  - §9 REPORT TEMPLATE: Output format
  - §10 SELF-CHECK: Verification steps
  - §11 FAILURE HANDLING: Error scenarios
  - §12 METADATA: Skill reference table

### workflow.md (Detailed Procedures)
- **Size:** 632 lines
- **Purpose:** Implementation reference for all procedures
- **Main Sections:**

#### Task Classification
- MERGEABLE criteria (6 conditions)
- CARRY-OVER reasons (11 types)
- Bash classification logic

#### Pre-Merge Security Scan
- Injection pattern detection (8 patterns)
- Intake item creation
- Patterns reference table

#### Sequential Merge Loop (10 Steps)
1. Prepare main branch (fetch, checkout, pull)
2. Verify branch accessibility (local/remote)
3. Pre-merge divergence check (rebase if needed)
4. Stub verification (pass, TODO, NotImplementedError)
5. Security pre-scan (before merge)
6. Squash merge (conflict detection & recovery)
7. Commit with WQ8 message validation
8. Quality gates (test, lint, format_check)
9. Update backlog item (status: DONE, merge_commit)
10. Write per-task close report

#### Additional Procedures
- Carry-Over Documentation
- Burndown Tracking
- Sprint Summary Report Structure
- Path Traversal Guard
- Max Tasks Guard (K2 Fix)
- Error Recovery Checklist
- Dedup Guard for Sprint Summary

### examples.md (Concrete K10 Examples)
- **Size:** 751 lines
- **Purpose:** Real scenarios with LLMem project data
- **10 Examples:**

1. **Successful Task Merge (T-TRI-02)**
   - Backlog state, review verdict, merge steps, gates passing
   - Close report with full YAML frontmatter

2. **Carry-Over — Stubs Found (T-EMB-01)**
   - Stub detection in 3 files
   - Intake item created, marked CARRY-OVER

3. **Carry-Over — Merge Conflict (T-STO-03)**
   - Branch divergence, rebase failure
   - Carry-over marked REBASE_CONFLICT

4. **Security Scan Detects Injection (T-API-04)**
   - eval() pattern detected
   - Critical intake item, SECURITY_SCAN_ISSUE

5. **Sprint 2 Close Summary**
   - Full sprint close report (5 tasks, 40% burn)
   - Task Status table, next sprint actions, retrospective

6. **Depends-On Blocking (T-REC-02)**
   - Task blocked by dependency CARRY-OVER
   - Marked BLOCKED

7. **Review REWORK Verdict (T-INJ-01)**
   - Review detected security issue (CDATA wrapping)
   - Marked CARRY-OVER: REWORK

8. **Idempotence Guard**
   - Re-run close for same sprint
   - Skips already-merged task (idempotence preserved)

9. **Max Tasks Guard (K2 Fix)**
   - 47 tasks in run 1, 50-task limit reached
   - Remaining 3 tasks in run 2

10. **State Reset After Close (WQ9)**
    - Before close: wip_item, wip_branch set
    - After close: reset to null

---

## Cross-Reference Map

### By Concern

#### Task Merge Procedure
- Start: `workflow.md` "Sequential Merge Loop" (10 steps)
- Reference: `examples.md` Example 1 (successful merge)
- Validation: `SKILL.md` §8 QUALITY GATES

#### Carry-Over Classification
- Start: `workflow.md` "Task Classification: MERGEABLE vs CARRY-OVER"
- Examples: `examples.md` Examples 2-7 (various carry-over reasons)
- Reference: `SKILL.md` §11 FAILURE HANDLING

#### Conflict Recovery
- Merge conflict: `workflow.md` Step 6, `examples.md` Example 3
- Rebase conflict: `workflow.md` "Sequential Merge Loop" Step 3
- Error recovery: `workflow.md` "Error Recovery Checklist"

#### Security
- Pre-scan: `workflow.md` "Pre-Merge Security Scan"
- Example: `examples.md` Example 4 (eval injection)
- Failure handling: `SKILL.md` §11 (security scan detection)

#### Idempotence & Guards
- K1 State Machine: `SKILL.md` §3 PRECONDITIONS
- K2 Max Tasks: `workflow.md` "Max Tasks Guard", `examples.md` Example 9
- K7 Path Traversal: `workflow.md` "Path Traversal Guard"
- Per-task guard: `SKILL.md` §5 VÝSTUPY
- Dedup guard: `workflow.md` "Dedup Guard for Sprint Summary"

#### Quality Gates
- Post-merge gates: `SKILL.md` §8 QUALITY GATES
- Failure semantics: `SKILL.md` §8 (warnings, not fatal, fail-open)
- Implementation: `workflow.md` Step 8 (test, lint, format_check)

#### Reporting
- Report template: `SKILL.md` §9 REPORT TEMPLATE
- Concrete example: `examples.md` Example 1 (close report), Example 5 (sprint summary)
- Output spec: `SKILL.md` §5 VÝSTUPY

#### State Management
- Preconditions: `SKILL.md` §3 PRECONDITIONS
- Self-check: `SKILL.md` §10 SELF-CHECK
- State reset: `examples.md` Example 10 (WQ9), `SKILL.md` §10 (verification)

### By Skill Reference (K/P/WQ Fixes)

#### K1: State Machine
Location: `SKILL.md` §3 PRECONDITIONS (phase validation)

#### K2: Max Tasks Guard
Location: `workflow.md` "Max Tasks Guard", `examples.md` Example 9

#### K7: Path Traversal Guard
Location: `workflow.md` "Path Traversal Guard"

#### P2 #37: Reviews Index Governance
Location: `SKILL.md` §3 PRECONDITIONS (rework count check)

#### P2 #26: Review Verdict Schema Validation
Location: `SKILL.md` §3 PRECONDITIONS

#### WQ8: Commit Message Validation
Location: `workflow.md` Step 7 (format pattern, no lazy verbs)

#### WQ9: State Reset Verification
Location: `SKILL.md` §10 SELF-CHECK, `examples.md` Example 10

---

## Quick Reference

### To find procedure for X:

| Need | Location |
|------|----------|
| Merge a task | `workflow.md` Steps 1-10, `examples.md` Example 1 |
| Detect carry-over reason | `workflow.md` "Task Classification" |
| Handle merge conflict | `workflow.md` Step 6, `examples.md` Example 3 |
| Handle rebase conflict | `workflow.md` Step 3, Error Recovery Checklist |
| Validate commit message | `workflow.md` Step 7 (WQ8 pattern) |
| Run quality gates | `workflow.md` Step 8, `SKILL.md` §8 |
| Update backlog | `workflow.md` Step 9 |
| Write close report | `workflow.md` Step 10, `examples.md` Examples 1, 5 |
| Create sprint summary | `examples.md` Example 5 |
| Security scanning | `workflow.md` "Pre-Merge Security Scan" |
| Stub verification | `workflow.md` Step 4, `examples.md` Example 2 |
| State validation | `SKILL.md` §3 PRECONDITIONS |
| Failure recovery | `workflow.md` "Error Recovery Checklist" |
| Idempotence check | `SKILL.md` §5 (guards), `examples.md` Example 8 |

---

## File Sizes

- `../SKILL.md` — 356 lines, 13 KB
- `workflow.md` — 632 lines, 19 KB
- `examples.md` — 751 lines, 18 KB
- **Total** — 1739 lines, 50 KB

---

## Reading Paths

### Path 1: Quick Execution (15 min)
1. `../SKILL.md` §1-§6 (foundation)
2. `../SKILL.md` §7 POSTUP (overview)
3. `workflow.md` relevant steps as needed

### Path 2: Learning (45 min)
1. `../SKILL.md` §1-§12 (complete)
2. `examples.md` Examples 1-5 (scenarios)
3. `workflow.md` sections of interest

### Path 3: Implementation (90 min)
1. `../SKILL.md` §1-§5 (context)
2. `workflow.md` "Sequential Merge Loop" (main logic)
3. `workflow.md` all safety guards and error recovery
4. `examples.md` all 10 examples (edge cases)

### Path 4: Troubleshooting (30 min)
1. `../SKILL.md` §11 FAILURE HANDLING
2. `workflow.md` "Error Recovery Checklist"
3. `examples.md` matching scenario

---

## Last Updated

Migration date: 2026-03-06
Format: Builder-template §1-§12 with progressive disclosure

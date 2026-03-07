# D1: Pochop Kontext — Detailed Procedure

**Goal:** Understand WHAT needs to be done and WHY by reading backlog, existing code, and governance.

## Detailed Steps

### Step 1: Read backlog item

```bash
cat "{WORK_ROOT}/backlog/${TASK_ID}.md"
```

Extract and document:
- **Title** — what is this feature/bug/epic called?
- **Description** — what's the business goal?
- **Acceptance Criteria (AC)** — how do we know it's done?
- **Effort estimate** — story points or time estimate
- **Dependencies** — what other tasks must be done first?
- **Linked vision goal** — which strategic goal does this serve?

### Step 2: Read relevant source code

```bash
# Identify affected modules from AC or description
grep -r "MODULE_NAME" "{CODE_ROOT}/" | head -20

# Read key files
cat "{CODE_ROOT}/{path1}.py"
cat "{CODE_ROOT}/{path2}.py"
```

For each affected module, understand:
- **Existing classes and methods** — what's already there?
- **Design patterns used** — singletons, factories, middleware, decorators?
- **Naming conventions** — snake_case vs camelCase, prefixes, suffixes?
- **What already exists** — prevent proposing duplicates
- **Architecture constraints** — layered, modular, monolithic?

**Minimum:** Read ≥3 relevant source files to understand affected areas.

### Step 3: Read test patterns

```bash
cat "{TEST_ROOT}/test_*.py" | head -50
cat "{TEST_ROOT}/fixtures.py"
```

Understand:
- **Test framework** — pytest, unittest, nose?
- **Fixture patterns** — how are test data created?
- **Mocking strategy** — mocks, fixtures, factories?
- **Test naming** — `test_feature_happy_path`, `test_feature_error`?
- **Coverage expectations** — what % of code is tested?

### Step 4: Governance cross-check

```bash
# Find relevant ADRs and SPECs mentioning the task or related concepts
grep -rl "${TASK_ID}" "{WORK_ROOT}/decisions/" "{WORK_ROOT}/specs/" 2>/dev/null | head -10

# Or search by main concept from the backlog title
CONCEPT=$(grep 'title:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | head -1 | sed 's/title:\s*//' | cut -d' ' -f1-3)
grep -rl "$CONCEPT" "{WORK_ROOT}/decisions/" "{WORK_ROOT}/specs/" 2>/dev/null | head -10
```

Document any found constraints:
- ADR constraints (decisions already made)
- SPEC constraints (technical standards to follow)
- Conflicting decisions (which ones, why?)

## Quality Checklist

- [ ] Backlog item fully understood: title, description, AC, effort, dependencies, vision
- [ ] ≥3 relevant source files read and summarized
- [ ] Existing architecture documented (patterns, conventions, components)
- [ ] Test patterns documented (framework, fixtures, naming)
- [ ] Governance constraints found and listed (or "none found")
- [ ] No duplicates identified in existing codebase

## Anti-patterns to avoid

- **Designing without reading code** — results in inconsistent architecture
- **Ignoring governance constraints** — violates ADRs, causes rework
- **Assuming code exists** — verify in actual source files
- **Missing edge cases** — caused by not understanding existing patterns

See main SKILL.md for integration context.

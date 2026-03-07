# §10 Self-Check — Detailed Verification Procedures

Self-check is MANDATORY and runs EVERY TIME before marking design READY. Use this checklist.

## Existence Checks

### ✓ Design spec file exists

```bash
ls -la "{ANALYSES_ROOT}/{TASK_ID}-design.md"
# Should output: file exists and is readable
```

**Action if missing:**
1. Create the file with all 8 sections (D1–D8)
2. Run design procedures again
3. Return to self-check

### ✓ Report file exists

```bash
ls -la "{WORK_ROOT}/reports/design-{TASK_ID}-$(date +%Y-%m-%d).md"
# Should output: file exists
```

**Action if missing:**
1. Create report using template (see references/09-report-template.md)
2. Fill in all metadata and sections
3. Return to self-check

### ✓ Backlog item updated to READY

```bash
grep "status:" "{WORK_ROOT}/backlog/${TASK_ID}.md" | head -1
# Should output: "status: READY"
# Or: "status: DESIGN" if not yet complete
```

**Action if not READY:**
1. Check if all quality gates pass (see references/08-quality-gates.md)
2. If gates fail, fix issues and re-run gates
3. If gates pass, update backlog item:
   ```bash
   sed -i 's/status: DESIGN/status: READY/' "{WORK_ROOT}/backlog/${TASK_ID}.md"
   ```
4. Return to self-check

---

## Quality Checks

### ✓ Design spec has ALL 8 sections (D1–D8)

```bash
# Count sections
grep "^## D[1-8]" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | wc -l
# Should output: 8
```

**What each section must contain:**

| Section | Required Content | Min Content |
|---------|------------------|------------|
| D1 | Context understanding | Backlog summary, code review, governance check |
| D2 | Data models | Field definitions, types, validators, relationships |
| D3 | Components & APIs | Class signatures, endpoint specs, pseudokód |
| D4 | Integration | Integration points, flow diagram, side effects |
| D5 | Configuration | New config keys with types, defaults, validation |
| D6 | Test strategy | ≥3 test cases per component (happy/edge/error) |
| D7 | Alternatives & risks | ≥2 alternatives with pro/con, ≥2 risks with mitigation |
| D8 | Dependencies | External deps, internal deps, implementation order |

**Action if missing section:**
1. Identify which section(s) are missing
2. Follow detailed procedure in corresponding reference file (04–07)
3. Add section to design spec
4. Return to self-check

### ✓ D2: Data model has complete definitions

```bash
# Check for field definitions with types
grep -A1 "class.*BaseModel\|class.*:" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | head -30
# Should show: field_name: Type = default
```

**Verification points:**
- [ ] Each field has explicit type (not `Any`)
- [ ] Field descriptions included
- [ ] Default values or Optional specified
- [ ] Validators present for user-facing fields
- [ ] Relationship to existing models documented

**Action if incomplete:**
1. Read D2 detailed procedure (references/05-procedure-d2.md)
2. Add missing field definitions or validators
3. Return to self-check

### ✓ D3: Pseudokód present for complex logic

```bash
# Find methods with logic >5 lines
grep -n "def \|async def" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | head -20

# For each method, check for pseudokód
grep -B1 -A5 "def method_name" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | grep -i "pseudokód\|# 1\.\|# 2\."
```

**Verification points:**
- [ ] Every method with >5 lines has pseudokód
- [ ] Pseudokód uses numbered steps (1. 2. 3. ...)
- [ ] Pseudokód mentions input, transformation, output
- [ ] Error handling cases covered in pseudokód
- [ ] Complexity noted (O(n), O(n²), etc. if relevant)

**Action if missing:**
1. Identify complex methods without pseudokód
2. Write pseudokód with steps, inputs, outputs, errors
3. Return to self-check

### ✓ D6: Test cases are concrete and specific

```bash
# Find test case definitions
grep -c "test_.*happy_path\|test_.*edge_case\|test_.*error\|test_.*integration" \
  "{ANALYSES_ROOT}/{TASK_ID}-design.md"
# Should be ≥3 per new component
```

**Verification points for EACH test:**
- [ ] Test name describes what is tested (not `test_works`)
- [ ] Specific input values given (not "some data")
- [ ] Specific output/assertion expected (not "correct behavior")
- [ ] 3+ test types per component: happy path, edge case, error handling
- [ ] Integration tests specify fixtures and setup

**Example of GOOD test case:**
```
test_cache_fetch_found
  Input: key="user:123", cache has {"user:123": "cached_data"}
  Output: returns "cached_data" immediately
  Assertion: assert result == "cached_data"
```

**Example of BAD test case:**
```
test_cache_works
  Input: some data
  Output: works correctly
```

**Action if vague:**
1. Re-read D6 procedure (references/07-procedure-d5-d8.md)
2. For each test, specify concrete input and expected output
3. Use template from procedure
4. Return to self-check

### ✓ D7: Alternatives and pro/con analysis

```bash
# Find alternatives section
grep -n "Alternativ\|Alternative\|^| [ABC] |" "{ANALYSES_ROOT}/{TASK_ID}-design.md"
# Should show table with ≥2 alternatives
```

**Verification points:**
- [ ] ≥2 alternatives documented
- [ ] Pro/con table with specific pros (not "good") and cons (not "bad")
- [ ] Each pro/con explains concrete impact
- [ ] Chosen alternative marked with "ZVOLEN" or similar
- [ ] Rejected alternatives explain why
- [ ] ≥2 risks identified with probability + severity
- [ ] Each risk has mitigation strategy and owner

**Examples of GOOD pro/con:**
```
Pro: Caching reduces DB load by 80% in typical scenario
Con: Cache invalidation requires synchronization (adds 15ms latency)
```

**Examples of BAD pro/con:**
```
Pro: Good
Con: Bad
```

**Action if insufficient:**
1. Identify design decision needing alternatives
2. Brainstorm ≥2 approaches
3. For each, list concrete pros/cons (with numbers/metrics)
4. Return to self-check

### ✓ Governance constraints explicitly listed (D1)

```bash
# Check for governance section in D1
grep -i "governance\|adr\|constraint" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | head -20
```

**Verification points:**
- [ ] D1 section explicitly lists applicable ADRs (or "none found")
- [ ] D1 section lists applicable SPECs (or "none found")
- [ ] Any conflicts explained and resolved
- [ ] Design respects all listed constraints

**Action if missing:**
1. Search `{WORK_ROOT}/decisions/` for relevant ADRs
2. Search `{WORK_ROOT}/specs/` for relevant SPECs
3. List all in D1 section
4. For each constraint, verify design respects it
5. Return to self-check

---

## Invariants (Must-NOT checks)

### ✗ Design spec does NOT contain implementation code

```bash
# Search for actual code (not pseudokód)
grep -E "^\s+(if|for|while|try|import|function|class) " \
  "{ANALYSES_ROOT}/{TASK_ID}-design.md" | wc -l
# Should output: 0 (or very few for pseudokód examples)
```

**Action if code found:**
1. Remove all real code
2. Replace with pseudokód/specification
3. Design is specification, not implementation
4. Return to self-check

### ✗ NO files in {CODE_ROOT}/ were modified

```bash
# Check git status (if repo)
cd "{CODE_ROOT}" && git status | grep "modified:"
# Should output: (nothing)

# Or check file timestamps
find "{CODE_ROOT}/" -mmin -60  # Files modified in last hour
# Should not include project files
```

**Action if code modified:**
1. This is a DESIGN skill, not IMPLEMENT skill
2. Revert all changes: `git checkout .`
3. Move implementation work to fabric-implement skill
4. Return to self-check

### ✗ Protocol log has START and END entries

```bash
# Check protocol log
grep "fabric-design" "{WORK_ROOT}/protocol.log" | grep -E "event: start|event: end"
# Should show 1 START and 1 END entry
```

**Action if missing:**
1. Missing START: Run protocol_log.py with --event start
2. Missing END: Run protocol_log.py with --event end
3. Return to self-check

### ✗ Backlog item NOT deleted or moved

```bash
# Check backlog item still exists
ls -la "{WORK_ROOT}/backlog/${TASK_ID}.md"
# Should output: file exists
```

**Action if missing:**
1. Restore from git or backup
2. Do not modify backlog structure during design
3. Return to self-check

---

## Self-Check Execution Checklist

Print this checklist and work through it:

```markdown
# Self-Check for {TASK_ID}

## Existence Checks
- [ ] Design spec file exists: {ANALYSES_ROOT}/{TASK_ID}-design.md
- [ ] Report file exists: {WORK_ROOT}/reports/design-{TASK_ID}-{date}.md
- [ ] Backlog item status: READY (or DESIGN if incomplete)

## Quality Checks
- [ ] ALL 8 sections (D1–D8) present in design spec
- [ ] D2: Data models have complete definitions with types
- [ ] D3: Pseudokód present for all complex logic (>5 lines)
- [ ] D6: ≥3 test cases per component (happy/edge/error)
- [ ] D7: ≥2 alternatives with pro/con analysis
- [ ] D7: ≥2 risks with probability, impact, mitigation
- [ ] D1: Governance constraints explicitly listed

## Invariants
- [ ] Design spec contains NO real code (only pseudokód/specification)
- [ ] NO files in {CODE_ROOT}/ were modified
- [ ] Protocol log has START and END entries
- [ ] Backlog item {TASK_ID}.md still exists and is intact

## Gate Status
- [ ] Gate 1 PASS: All sections complete
- [ ] Gate 2 PASS: Pseudokód present
- [ ] Gate 3 PASS: Test cases concrete
- [ ] Gate 4 PASS: Alternatives documented
- [ ] Gate 5 PASS: Governance aligned

## Final Status

Design is: [ ] READY  [ ] NEEDS WORK

If NEEDS WORK, which items failed?
{list}

Actions to fix:
{list}

Retry self-check: Yes / No
```

See main SKILL.md for integration with §9 Report and §11 Failure Handling.

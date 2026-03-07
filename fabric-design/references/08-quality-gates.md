# §8 Quality Gates — Detailed Checklist

Quality gates are MANDATORY checkpoints. Design cannot proceed to READY status without passing all gates.

## Gate 1: Completeness of Design Spec

**Requirement:** All 8 sections (D1–D8) must be present and substantive.

**Verification:**
```bash
# Check for all sections in design spec
grep -c "^## D[1-8]" "{ANALYSES_ROOT}/{TASK_ID}-design.md"
# Should output: 8
```

**PASS Criteria:**
- Design spec has explicit "## D1" through "## D8" sections
- Each section has content (not just "TODO" or empty)
- Sections follow the order D1–D8

**FAIL Criteria:**
- Missing any section → add it
- Section contains only "TODO" → develop the content
- Wrong order → reorder sections

**What to do if failing:**
1. Identify missing sections
2. For each missing section, follow detailed procedure (see references/)
3. Re-check gate

---

## Gate 2: Pseudokód Present

**Requirement:** Every non-trivial logic has pseudokód (≥5 lines of actual code).

**Verification:**
```bash
# Find all function/method definitions
grep -n "def \|async def " "{ANALYSES_ROOT}/{TASK_ID}-design.md"

# For each, verify pseudokód exists nearby
grep -A5 "def method_name" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | grep -i "pseudokód\|# 1\.\|# 2\."
```

**PASS Criteria:**
- Every method with complex logic has pseudokód in docstring or comment
- Pseudokód describes algorithm in steps (1. 2. 3. ...)
- Pseudokód mentions inputs, outputs, and key transforms

**FAIL Criteria:**
- Complex logic with only English description (no pseudokód)
- Pseudokód too vague ("process the data") without steps
- Pseudokód missing error handling

**What to do if failing:**
1. Identify methods without pseudokód
2. For each, write pseudokód with numbered steps
3. Include error cases in pseudokód

---

## Gate 3: Test Cases Are Concrete

**Requirement:** ≥3 test cases per component with specific inputs and outputs.

**Verification:**
```bash
# Count test case definitions
grep -c "test_.*happy_path\|test_.*edge_case\|test_.*error" "{ANALYSES_ROOT}/{TASK_ID}-design.md"
# Should be ≥3 per component

# Verify each test has inputs and outputs
grep -A3 "Vstup:" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | grep -E "^\s*[-•]"
```

**PASS Criteria:**
- ≥3 tests per new component (happy/edge/error minimum)
- Each test: specific input values (not "some data")
- Each test: specific output/assertion (not "works correctly")
- Test name describes what it tests

**FAIL Criteria:**
- Generic test names: `test_it_works`, `test_feature`
- Vague inputs: "valid input", "some data"
- Vague assertions: "should work", "correct behavior"
- Single test covering whole feature (instead of multiple focused tests)

**What to do if failing:**
1. For each component, write 3+ concrete test cases
2. Use template from references/07-procedure-d5-d8.md
3. Specify exact input values and expected outputs

---

## Gate 4: Alternatives Present

**Requirement:** ≥2 alternatives with pro/con analysis for major design decisions.

**Verification:**
```bash
# Find alternatives section
grep -n "## .*Alternativ\|^| [ABC] |" "{ANALYSES_ROOT}/{TASK_ID}-design.md"

# Count alternatives
grep -c "^| [ABC] |" "{ANALYSES_ROOT}/{TASK_ID}-design.md"
# Should be ≥2
```

**PASS Criteria:**
- ≥2 alternatives documented for main design choice
- Pro/con table with ≥2 pros and ≥2 cons per alternative
- Chosen alternative marked and justified
- Rejected alternatives explain why

**FAIL Criteria:**
- Single approach without considering alternatives
- "This is obvious" without justification
- Alternatives without pro/con analysis
- Pro/con too vague ("good", "bad")

**What to do if failing:**
1. Identify major design decision (data model choice, API design, etc.)
2. Brainstorm ≥2 alternatives
3. For each, list concrete pros/cons (not "good" but "allows X, prevents Y")
4. Justify chosen approach explicitly

---

## Gate 5: Governance Alignment

**Requirement:** Design does not conflict with accepted ADRs or active SPECs.

**Verification:**
```bash
# Extract decisions/constraints from D1
grep -i "constraint\|adr\|spec\|governance" "{ANALYSES_ROOT}/{TASK_ID}-design.md" | head -20

# Check against actual ADR/SPEC files
ls -la "{WORK_ROOT}/decisions/*.md" | head -10
ls -la "{WORK_ROOT}/specs/*.md" | head -10
```

**PASS Criteria:**
- Design spec explicitly lists governance constraints (D1)
- No conflicts with accepted ADRs
- No violations of active SPECs
- If constraint applies, design respects it

**FAIL Criteria:**
- Design does not mention governance (assumed "none")
- Design violates existing ADR (e.g., "all APIs must use REST" but design uses GraphQL)
- Design changes already-accepted SPEC (without approved amendment)

**What to do if failing:**
1. Read relevant ADRs/SPECs from `{WORK_ROOT}/decisions/` and `{WORK_ROOT}/specs/`
2. List all applicable constraints in D1
3. If design conflicts with accepted ADR:
   - Create intake item to request ADR amendment
   - Keep task in DESIGN status (not READY)
   - Document conflict and justification in intake item

---

## Gate Execution

Run gates in order. If any fails, fix the issue and re-run from that gate.

```bash
# Automated gate check (pseudo-code)
for gate in 1 2 3 4 5; do
  echo "Checking Gate $gate..."
  if check_gate_$gate; then
    echo "✓ Gate $gate PASS"
  else
    echo "✗ Gate $gate FAIL — fix and re-run"
    exit 1
  fi
done
echo "All gates passed — design is READY"
```

See main SKILL.md for integration with §9 Report and §10 Self-Check.

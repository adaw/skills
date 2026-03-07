# Architectural Scanning Workflow: Procedures 7.1 – 7.6

This document details the step-by-step procedures for executing the architectural analysis.

---

## 7.1) A0: Pre-flight (Context Load)

**Objective:** Load vision.md principles, scan backlog epics, inventory code structure.

**Procedure:**

1. Read `vision.md` and extract all 8 design principles with exact quotes
2. Create principle→dimension mapping table (per the reference architecture):
   - "Everything is X" principle → which dimensions does it map to?
3. Scan backlog/ for all T1/T2/T3 epics (grep `^# T[1-3]:`)
4. Count .py files and total LOC using FAST PATH commands
5. List all modules in src/llmem/ with imports (create module inventory)

**Minimum Outputs:**
- 8 principles listed with source quotes from vision.md
- Principle→dimension mapping table
- Epic list (T1/T2/T3 count + top-5 by date/priority)
- Module inventory table (module name, file count, LOC, primary responsibility)
- Total codebase stats (LOC, file count, import density)

**Anti-patterns:**
- ❌ Don't skip vision.md reading — architect MUST ground scoring against actual principles
- ❌ Don't assume principles without quoting them from vision.md
- ❌ Don't ignore optional files (decisions/, specs/) — they feed into A19 + A3
- ❌ Don't count only src/ — include tests/, API routes, etc.

---

## 7.2) A1: Principle Alignment (per principle scoring)

**Objective:** For EACH of the 8 principles from vision.md, assess codebase adherence and list violations.

**Procedure:** For each principle:

1. Define detection heuristics (what grep/code patterns indicate violation)
2. Scan entire CODE_ROOT with those heuristics
3. Collect violations with file:line references
4. Calculate adherence % = (fully-compliant files / total scanned) × 100
5. Assign score 0-100 based on adherence % + severity weighting using interpolation

(See `references/dimensions.md § GROUP 0: PRINCIPLES – A0` for numeric anchors and example scanning commands.)

**Minimum Outputs:**
- Per-principle score 0-100 with exact violations listed
- Evidence: file:line references (not vague)
- Confidence level per principle (HIGH/MEDIUM/LOW)
- A0 overall score = average of all 8 principle scores

**Anti-patterns:**
- ❌ Don't score without evidence — always cite file:line
- ❌ Don't give 100% without verifying every public function/async call
- ❌ Don't skip any principle — even if "perfect", score it as such with evidence
- ❌ Don't make up violations — only cite what you actually found

---

## 7.3) A2: Architectural Scanning (A1-A19 dimensions)

**Objective:** Evaluate all 19 remaining dimensions across 4 groups (Coherence, Modularity, Scalability, Evolution).

**Procedure:** For each dimension (A1-A19):

1. Reference the dimension definition in `references/dimensions.md`
2. Apply the **WHAT** (definition) and **HOW** (procedure) steps
3. Scan the **WHERE** (specified files/paths)
4. Score 0-100 using the **Scoring Criteria** and numeric anchors
5. Collect **Evidence** with file:line citations
6. Assign severity emoji (🟢 EXCELLENT/GOOD, 🟡 NEEDS ATTENTION, 🔴 CRITICAL)
7. Record Confidence level (HIGH/MEDIUM/LOW)

**Output Template for All Dimensions (A1-A19):**

| Dimension | Group | Score | Severity | Confidence | Key Findings | Evidence |
|-----------|-------|-------|----------|------------|--------------|----------|
| A1: Layer Isolation | KOHERENCE | 88 | 🟢 GOOD | HIGH | API routes don't access DB directly; one util import crossing layers | src/llmem/api/routes/capture.py:12 imports storage util; fix: move to service layer |
| A2: Message Flow | KOHERENCE | 92 | 🟢 EXCELLENT | HIGH | JSONL log + idempotent upserts; event replay tested | src/llmem/storage/log_jsonl.py, tests/test_triage_and_recall.py |
| A3: Pattern Consistency | KOHERENCE | 78 | 🟡 NEEDS ATTENTION | MEDIUM | CaptureService and RecallService differ in error handling; one uses logger, one prints | src/llmem/services/capture.py vs recall.py |
| ... | ... | ... | ... | ... | ... | ... |
| A19: ADR Coverage | EVOLUCE | 72 | 🟡 NEEDS ATTENTION | HIGH | 6 ADRs present; missing docs for "distributed instance coordination" and "embedding provider versioning" | fabric/decisions/ listing |

**Minimum Outputs:**
- All 20 dimensions scored (0-100)
- Per-dimension severity emoji
- Confidence level (HIGH/MEDIUM/LOW)
- Specific evidence (file:line, not vague)
- Key findings per dimension

---

## Anti-patterns with detection bash & fix procedures (WQ4)

### Anti-pattern A: God Class

**Detection bash:**
```bash
find $CODE_ROOT -name "*.py" -exec grep -l "^class " {} \; | \
while read f; do
  METHODS=$(grep -c "^\s*def " "$f")
  if [ $METHODS -gt 10 ]; then
    echo "$f: $METHODS methods"
  fi
done
```

**Fix procedure:**
1. Identify the god class and its distinct responsibilities
2. Extract each responsibility to separate class
3. Original class becomes coordinator/factory
4. Update imports throughout codebase

### Anti-pattern B: Circular dependencies

**Detection bash:**
```bash
for f in $CODE_ROOT/**/*.py; do
  grep "^from\|^import" "$f" | while read imp; do
    TARGET=$(echo "$imp" | sed 's/from //; s/ import.*//')
    if grep -l "from.*$(basename $f .py)\|import.*$(basename $f .py)" \
       "$CODE_ROOT/**/$TARGET.py" 2>/dev/null; then
      echo "CIRCULAR: $f <-> $TARGET"
    fi
  done
done | sort | uniq
```

**Fix procedure:**
1. Introduce abstraction layer or intermediate module
2. Move shared code to common module
3. Break import cycle by one party delegating

### Anti-pattern C: Missing abstraction layer

**Detection bash:**
```bash
grep -rn "InMemoryBackend\|QdrantBackend" $CODE_ROOT/services/ --include="*.py"
```

**Fix procedure (if results non-empty):**
1. Define backend interface (if not exists)
2. Inject backend via dependency injection
3. Update service constructors to accept backend parameter

### Anti-pattern D: Hardcoded config values

**Detection bash:**
```bash
grep -rn 'localhost:6333\|port.*=.*80\|host.*=.*"' $CODE_ROOT \
  --include="*.py" | grep -v "#.*\|test\|comment" | head -20
```

**Fix procedure:**
1. Extract to config.py using pydantic-settings
2. Replace all occurrences with config.<field>
3. Verify all values can be overridden via env vars

### Anti-pattern E: Undocumented API surface

**Detection bash:**
```bash
grep -rn "@router\|@app" $CODE_ROOT/api/routes/ --include="*.py" -A2 | \
grep -B2 "^def " | grep -v '"""' | grep "def "
```

**Fix procedure:**
1. Add docstring to each route handler with description, params, responses
2. Ensure all request/response models are documented
3. Validate against OpenAPI spec

---

## 7.4) A3: Backlog Cross-Check

**Objective:** For each T1/T2/T3 epic in backlog/, assess if current architecture supports building it.

**Procedure:**

1. Extract title + description from each epic file
2. Identify what new abstractions or changes are needed
3. Check if prerequisites exist in codebase (e.g., "add semantic embeddings" needs embeddings interface — does it exist?)
4. Estimate refactoring effort as % of feature effort (10% = needs small fix; 40% = major prep work)
5. Mark blockers (unmet prerequisites that must be fixed first)

**Output Template:**

| Epic | T | Architectural Readiness | Blockers | Refactoring % | Notes |
|------|---|------------------------|----------|--------------|-------|
| Semantic Embeddings | T1 | 85% ready | None | 15% | Just create impl + register |
| Distributed Recall | T1 | 40% ready | No cross-instance API | 40% | Must add routing layer |
| Admin Dashboard | T2 | 95% ready | None | 5% | Frontend only; API stable |

**Minimum Outputs:**
- Per-epic readiness % (estimate: ready to start with ≥80%)
- Blocker list per epic (what must be fixed first)
- Refactoring estimate as % of feature effort
- Confidence (can we commit to this timeline?)

**Anti-patterns:**
- ❌ Don't assess without reading epic description AND relevant code
- ❌ Don't ignore T3 epics (future features still inform architecture)
- ❌ Don't assume blockers — verify they're not already resolved

---

## 7.5) A4: Synthesis & Scoring

**Objective:** Calculate weighted overall score, determine verdict, identify cross-dimensional insights.

### Scoring Formula

```
Overall = (A0×2 + A1×2 + A2 + A3 + A4 + A5×1.5 + A6 + A7×1.5 + A8 + A9
         + A10×1.5 + A11×2 + A12×1.5 + A13×2 + A14 + A15×2 + A16×1.5
         + A17×2 + A18 + A19) / 28

Verdict:
- ≥80: SOLID (architecture supports current + near-term roadmap)
- 60-79: NEEDS ATTENTION (refactoring recommended in next cycle)
- 40-59: REFACTOR FIRST (major work before next feature sprint)
- <40: REDESIGN (fundamental issues; consider architectural overhaul)
```

### Weight Justification Table

| Dimension | Weight | Category | Rationale |
|-----------|--------|----------|-----------|
| A0: Principle Alignment | 2.0 | FOUNDATION | All other dimensions rest on principles; 40% score variance from A0 ripples across entire system |
| A1: Layer Isolation | 2.0 | COHERENCE | Core to modularity + testability; violations cause tangling across all features |
| A2: Message Flow | 1.0 | COHERENCE | Important but secondary to A1; affects data correctness |
| A3: Pattern Consistency | 1.0 | COHERENCE | Enables team velocity; violations increase maintenance cost by 30% |
| A4: API Surface | 1.0 | COHERENCE | Affects user experience + contract stability |
| A5: Module Cohesion | 1.5 | MODULARITY | Directly impacts testability + change velocity; tight cohesion = 50% faster sprints |
| A6: Extractable Components | 1.0 | MODULARITY | Flexibility + reuse; single-responsibility modules enable independent scaling |
| A7: Testability | 1.5 | MODULARITY | DI + mocks = faster feedback loops; 60%+ gap in coverage signals cascading bugs |
| A8: State Management | 1.0 | MODULARITY | Race conditions are critical bugs; bounded state prevents silent data corruption |
| A9: Configuration | 1.0 | MODULARITY | Operational flexibility; hardcoded config blocks cloud deployments |
| A10: Tool Ecosystem | 1.5 | MODULARITY | Mature tooling (make, pytest, ruff) prevents > 40% of integration bugs |
| A11: Memory Architecture | 2.0 | SCALABILITY | CRITICAL for production; O(n) search kills system at 100K+ memories |
| A12: Persistence | 1.5 | SCALABILITY | Data loss events are catastrophic; event sourcing is architectural requirement |
| A13: Distribution Readiness | 2.0 | SCALABILITY | Multi-instance support unlocks enterprise use; single-instance assumption → redesign needed |
| A14: LLM Provider Flexibility | 1.0 | SCALABILITY | Embeddings abstraction enables semantic evolution; hardcoded provider = future debt |
| A15: Tool Sandboxing | 2.0 | SCALABILITY | Security + reliability; unsandboxed tool execution = production risk |
| A16: Observability | 1.5 | SCALABILITY | 80% of production issues resolved by structured logs + tracing; sparse logging = support tax |
| A17: Backlog Alignment | 2.0 | EVOLUTION | Strategic fit determines feature velocity; misaligned architecture = blocked epics = product delay |
| A18: Complexity Hotspots | 1.0 | EVOLUTION | High complexity → high bug rate + slow iteration; >15 cyclomatic = testing nightmare |
| A19: ADR Coverage | 1.0 | EVOLUTION | Undocumented decisions = rework + team confusion; 1 ADR/decision saves 10+ hours in rework |

**Sum of weights:** 28 (verified: 2+2+1+1+1+1.5+1+1.5+1+1+1.5+2+1.5+2+1+2+1.5+2+1+1 = 28)

### WQ5 enforcement

All scoring dimensions must have explicit measurable methods (not subjective judgment):

Each scoring method must include:
- **WHAT:** Clear definition (not vague goal)
- **HOW:** Bash command or code review step (reproducible)
- **WHERE:** Specific files/paths (not "the codebase")
- **Scoring anchors:** Numeric thresholds mapped to 0-100 scale (not "good/bad" opinions)
- **Evidence requirement:** File:line citations (not assertions)

**Verification check:**
```bash
# Verify scoring is not subjective opinion
grep -n "seems\|appears\|probably\|likely\|might\|complex-ish" architect-report.md
# Should be 0 results; any hits = rewrite with measurable criteria
```

### Synthesis Procedure

1. Compile all 20 dimension scores (A0-A19)
2. Apply weights per formula above
3. Calculate sum and divide by sum of weights (28)
4. Determine verdict based on thresholds
5. Identify top-5 CRITICAL findings (🔴 score <40 or blocking T1 epic)
6. Identify top-5 hotspots (complex, low-coverage, high-churn modules)
7. Create cross-dimensional insight table (e.g., "Poor observability (A16) explains test gaps (A7)")

**Cross-Dimensional Insights Table Example:**

| Finding | Dimensions Involved | Impact | Recommendation |
|---------|-------------------|--------|-----------------|
| Sparse logging in capture hot path limits debugging | A16, A7, A3 | Hard to test async race conditions; production issues opaque | Add structured logging to capture_event; use request IDs |
| InMemory backend not tested at scale; Qdrant untested in CI | A11, A7, A10 | Risk of silent data loss; scale unknown | Add integration tests for both backends; scale tests in CI |
| ADRs missing for distributed recall design | A13, A19 | Risk of misaligned implementation; future work will redo | Add ADR for instance routing; document early |

**Minimum Outputs:**
- Overall score with formula applied
- Verdict (SOLID/NEEDS ATTENTION/REFACTOR FIRST/REDESIGN)
- Top-5 CRITICAL findings with severity emoji
- Top-5 hotspots with complexity/coverage/churn metrics
- Cross-dimensional insight table (3-5 insights)
- Weighted score breakdown (show weight application per dimension)

**Anti-patterns:**
- ❌ Don't just average scores — MUST use weighted formula
- ❌ Don't skip cross-dimensional analysis — that's where insights live
- ❌ Don't call something SOLID without checking all T1/T2 epics are ready
- ❌ Don't forget to explain why you chose each verdict threshold

---

## 7.6) A5: Mutations (default mode only – skip if --no-fix)

**Objective:** Generate concrete backlog changes based on findings. Only in default mode.

### Mutation Validation (REQUIRED)

Before creating any backlog mutation, VALIDATE:

```bash
MUTATION_VALIDATION() {
  local dim_name=$1
  local dim_score=$2
  local evidence=$3
  local ac=$4

  # Check 1: Score below threshold (40 for CRITICAL, 70 for others)
  if [ "$dim_score" -ge 70 ]; then
    echo "SKIP: Dimension $dim_name already ≥70 (score: $dim_score)"
    return 1
  fi

  # Check 2: Evidence is concrete (contains file:line)
  if ! echo "$evidence" | grep -qE "[a-zA-Z_/]+\.py:[0-9]+" ; then
    echo "SKIP: Evidence for $dim_name not concrete (must be file:line format)"
    return 1
  fi

  # Check 3: AC targets measurable improvement
  if ! echo "$ac" | grep -qE "≥[0-9]+|[0-9]+%|zero|none" ; then
    echo "SKIP: AC for $dim_name not measurable (must include numeric target)"
    return 1
  fi

  echo "PASS: Mutation for $dim_name validated"
  return 0
}
```

**Only create mutation if validation PASS.**

### Mutation Creation Procedure

1. **For each 🔴 CRITICAL dimension (score <40):**
   - VALIDATE mutation per above
   - Create new `backlog/T0-architect-{name}.md` refactoring task
   - Title: Concrete action (e.g., "T0: Refactor capture service for async/await compliance")
   - Acceptance criteria: Dimension must reach ≥70 after fix (MUST be measurable)
   - Estimate: T0 = ≤ 1 day
   - Blocking: Any T1 feature that depends on this dimension

2. **For each 🟠 IMPORTANT finding blocking T1/T2 epics:**
   - Create new `backlog/T1-architect-{name}.md` task
   - Title: Feature-enabling work (e.g., "T1: Extract embeddings abstraction for semantic impl")
   - Acceptance criteria: Dimension ≥70, feature now buildable
   - Estimate: T1 = 1-3 days
   - Unblocks: List of features

3. **For undocumented decisions found in A19 (ADR coverage < 80%):**
   - Generate new ADR file in `reports/adr/{ADR_ID}.md`
   - Format: Title, Status, Context, Decision, Consequences, Alternatives
   - Use existing ADR template from fabric/decisions/ if present
   - Link from main architect report

4. **Priority shifts in backlog:**
   - If an existing backlog item conflicts with a CRITICAL finding, raise its priority (mark with 🔴 URGENT)
   - If T0 blocker created, add dependency link: T1 epic → T0 task
   - Re-save backlog index with new ordering

5. **Update backlog index:**
   - Add new T0/T1 items to index
   - Update counts (total T0/T1/T2/T3)
   - Recompute dependency graph

### Mutation Specification Template

```markdown
# T0: Refactor capture service for async compliance

**Epic:** Architect Findings — CRITICAL: Layer Isolation (A1: 45/100)

**Problem:** `capture_event()` makes blocking `requests.post()` call to external service, violating "Everything is Async" principle. Blocks `Semantic Embeddings` feature.

**Solution:**
- Replace `requests.` with `aiohttp.ClientSession` or similar async client
- Update signature: `async def capture_event(...)`
- Propagate async up the call stack (API route → service)

**Acceptance Criteria:**
- No `requests.`, `time.sleep()`, or blocking I/O in capture path
- All tests pass; 0 async warnings
- A1 score ≥70 (from 45)
- Takes <1 day

**Files Changed:**
- src/llmem/services/capture.py (main work)
- src/llmem/api/routes/capture.py (route signature)
- tests/test_capture.py (update mocks)

**Estimate:** T0 (1 day)
```

**Minimum Outputs:**
- At least 1 mutation per CRITICAL (🔴) finding
- Each mutation has: Problem, Solution, Acceptance Criteria, Files, Estimate
- All new backlog items written to `backlog/` directory
- All undocumented decisions → ADR files in `reports/adr/`
- Backlog index updated with new counts + dependencies
- Mutations count in final report

**Anti-patterns:**
- ❌ Don't create vague tasks ("Fix architecture") — be specific (files, what, why, AC)
- ❌ Don't mutate backlog in --no-fix mode — that violates the contract
- ❌ Don't forget acceptance criteria — don't know when fix is done otherwise
- ❌ Don't forget dependency links (T1 → T0 blocker)

---

End of workflow.md

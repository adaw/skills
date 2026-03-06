---
name: "fabric-architect"
title: "fabric-architect"
type: "skill"
---
<!-- built from: builder-template -->

# fabric-architect

Deep architectural analysis of the LLMem codebase across 20 dimensions spanning 4 groups: Coherence (A0-A4), Modularity (A5-A10), Scalability (A11-A16), and Evolution (A17-A19). Produces weighted architectural health score with evidence-based findings and backlog mutations.

---

## §1 Účel

**Primary Goal:** Perform comprehensive architectural assessment of the codebase against design vision, identifying structural debt, principle violations, and roadmap blockers.

**Why It Matters:** Without systematic architectural review, technical debt accumulates silently. Decisions become fragmented. Future features face unexpected coupling issues. The codebase drifts from its stated vision.

**Scope:** All 20 dimensions across 4 groups with weighted scoring (0-100 overall). Generates evidence-based backlog mutations.

**Variants:**
- **default** (with backlog mutations): Full analysis + concrete T0/T1 refactoring tasks
- **--no-fix** (read-only): Analysis only, zero mutations created
- **--focus={area}**: Deep dive on single group (KOHERENCE|MODULARITA|ŠKÁLOVATELNOST|EVOLUCE)
- **--strategy={mode}**: FAST (breadth-first scanning) | DEEP (line-by-line audit) | RISK (focus on > 40-score areas)

---

## Downstream Contract

**Kdo konzumuje výstupy fabric-architect a jaká pole čte:**

- **fabric-process** reads:
  - Architectural health score (0-100) → context for process-level risk assessment
  - Module dependency findings → identifies tightly-coupled modules where process changes are risky
  - Backlog mutations → new T0/T1 refactoring tasks to plan around

- **fabric-gap** reads:
  - Per-dimension scores (A0-A19) → dimensions scoring <50 indicate architectural gaps
  - Evidence-based findings → cross-reference with vision goals to detect structural gaps
  - `reports/architect-*.md` field: `overall_score`, `critical_findings[]`, `mutations[]`

- **fabric-sprint** reads:
  - Backlog mutations from architect → include in sprint target selection
  - Dimension priority → dimensions with lowest scores get sprint attention first

- **fabric-implement** reads:
  - Module dependency map → knows which modules are tightly coupled before making changes
  - Anti-pattern findings → avoids introducing patterns architect flagged

**Contract fields in report:**
```yaml
overall_score: float        # 0-100 weighted score
dimensions: [{id, name, score, evidence}]  # A0-A19
critical_findings: [{file, line, dimension, severity, description}]
mutations: [{slug, type, tier, effort, description}]
```

---

## §2 Protokol

```bash
# START
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "architect" --event start

# ... architectural analysis (A0-A19) ...

# END
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "architect" --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/architect-{YYYY-MM-DD}.md"
```

Outputs:
- START timestamp
- Per-phase progress markers (A0-A5)
- Quality gate results
- END timestamp + overall verdict

---

## §3 Preconditions (bash code)

All preconditions MUST be met. Skill STOPs at first missing dependency.

```bash
# 1. config.md exists (stores LLMEM-specific configuration)
test -f config.md || { echo "STOP: config.md missing"; exit 1; }

# 2. state.md exists (tracks architectural state from prior runs)
test -f state.md || { echo "STOP: state.md missing"; exit 1; }

# 3. vision.md exists (CRITICAL — architect scores against principles)
test -f vision.md || {
  echo "STOP: vision.md missing — architect cannot score without vision principles"
  exit 1
}

# 4. backlog/ directory exists (for mutations + cross-reference)
test -d backlog/ || { echo "STOP: backlog/ directory missing"; exit 1; }

# 5. CODE_ROOT exists and has .py files
CODE_ROOT="${CODE_ROOT:-.}"
test -d "$CODE_ROOT" || { echo "STOP: CODE_ROOT not found"; exit 1; }
find "$CODE_ROOT" -name "*.py" -type f | head -1 > /dev/null || {
  echo "STOP: No .py files found in CODE_ROOT";
  exit 1;
}

echo "✓ All preconditions met"
```

**Dependency Chain:**
```
fabric-init → [fabric-intake →] fabric-architect
```

Architect can run after init alone, but intake may feed intake items for A3 cross-check.

---

## §4 Vstupy

**Povinné (Required):**
- `config.md` — LLMem configuration and build context
- `state.md` — Prior architectural state (for drift detection)
- `vision.md` — 8 design principles + roadmap (CRITICAL)
- `CODE_ROOT` — All .py files (src/llmem/, tests/, etc.)
- `backlog/` — Directory with task hierarchy

**Volitelné (Optional):**
- `fabric/decisions/` — ADR files (scored in A19)
- `fabric/specs/` — Specification documents (scored in A3)
- `reports/` — Previous architect reports (for trend analysis)

---

## §5 Výstupy

**Primární (Primary):**
- `reports/architect-{YYYY-MM-DD}.md` — Full report (schema: `fabric.report.v1`)
  - Includes: all dimension scores, evidence, findings, verdict
  - Dimensions: 20 (A0-A19)
  - Mutations count + details

**Vedlejší (Secondary):**
- `reports/adr/{ADR_ID}.md` — Generated ADR files for undocumented decisions (A19)
- Backlog mutations (in default mode only):
  - New `backlog/T0-architect-*.md` refactoring tasks
  - New `backlog/T1-architect-*.md` blocking features
  - Priority shifts + dependency marks

**No code files modified** — architect is analysis-only.

---

## §6 FAST PATH

**Quick Context Gathering (< 2 min):**

1. **Backlog Index:**
   ```bash
   find backlog/ -name "*.md" | xargs grep -l "^# T[0-3]:" | wc -l
   ```
   Output: Count of T0-T3 epics

2. **Governance Index:**
   ```bash
   find fabric/decisions/ -name "*.md" 2>/dev/null | wc -l
   find fabric/specs/ -name "*.md" 2>/dev/null | wc -l
   ```
   Output: Count of ADRs and specs

3. **Module Inventory:**
   ```bash
   find $CODE_ROOT -name "*.py" -type f | wc -l
   find $CODE_ROOT -name "*.py" -type f -exec wc -l {} + | tail -1
   ```
   Output: File count + total LOC

4. **Import Graph (sample):**
   ```bash
   grep -rn "^from\|^import" $CODE_ROOT/ --include="*.py" | head -20
   ```
   Output: Import patterns for quick dependency scan

---

## §7 Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-architect. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### Path Traversal Guard (K7: Input Validation)

```bash
# Path traversal guard — reject any input containing ".."
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic path inputs:
# validate_path "$BACKLOG_FILE"
# validate_path "$REPORT_PATH"
```

### 7.1) A0: Pre-flight (Context Load)

**Co:** Load vision.md principles, scan backlog epics, inventory code structure.

**Jak:**
1. Read `vision.md` and extract all 8 design principles with exact quotes
2. Create principle→dimension mapping table (per the reference architecture):
   - "Everything is X" principle → which dimensions does it map to?
3. Scan backlog/ for all T1/T2/T3 epics (grep `^# T[1-3]:`)
4. Count .py files and total LOC using FAST PATH commands
5. List all modules in src/llmem/ with imports (create module inventory)

**Minimum:**
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

### 7.2) A1: Principle Alignment (per principle scoring)

**Co:** For EACH of the 8 principles from vision.md, assess codebase adherence and list violations.

**Jak:** For each principle:
1. Define detection heuristics (what grep/code patterns indicate violation)
2. Scan entire CODE_ROOT with those heuristics
3. Collect violations with file:line references
4. Calculate adherence % = (fully-compliant files / total scanned) × 100
5. Assign score 0-100 based on adherence % + severity weighting using interpolation

**NUMERIC ANCHORS & INTERPOLATION:**

For all principle scoring, use this interpolation formula to convert metrics to 0-100 scale:
```
score = lower_threshold + (metric - lower_bound) / (upper_bound - lower_bound) × (upper_threshold - lower_threshold)
```

Examples of numeric anchors per principle:

**Principle: "Everything is Async"** (Metrics: % blocking I/O in codebase)
- **0%** blocking → Score 95-100 (EXCELLENT)
- **5-10%** blocking → Score 80-90 (GOOD)
- **15-20%** blocking → Score 65-75 (NEEDS ATTENTION)
- **>25%** blocking → Score <50 (CRITICAL)

**Principle: "Everything is Documented"** (Metrics: docstring coverage %)
- **≥95%** public functions documented → Score 95-100
- **80-94%** documented → Score 80-94
- **60-79%** documented → Score 60-79
- **<60%** documented → Score <60

**Principle: "Everything is Replaceable"** (Metrics: DI pattern coverage + backend swappability)
- All services use DI, 2+ backends implemented, swappable → Score 90-100
- 80% DI coverage, 1 backend + mockable interface → Score 75-89
- 50% DI coverage, hardcoded deps in 2-3 places → Score 60-74
- Monolithic, no DI, single backend hard-wired → Score <50

**Principle: "Everything is Observable"** (Metrics: log lines per KLOC + request correlation)
- >5 log/KLOC + structured (JSON) + request IDs → Score 90-100
- 3-5 log/KLOC + some context → Score 75-89
- 1-3 log/KLOC + unstructured → Score 60-74
- <1 log/KLOC or no logging → Score <50

**Principle: "Everything is Tested"** (Metrics: test:code LOC ratio + coverage)
- Ratio >0.8 + coverage ≥80% → Score 90-100
- Ratio 0.5-0.8 + coverage 60-79% → Score 75-89
- Ratio 0.3-0.5 + coverage 40-59% → Score 60-74
- Ratio <0.3 + coverage <40% → Score <50

**Principle: "Everything is Versioned"** (Metrics: API version endpoints + schema versioning)
- All endpoints /v1+ prefix + model schema.v1 + migration ready → Score 90-100
- Most endpoints versioned, schemas present → Score 75-89
- Partial versioning (some endpoints, no schema version) → Score 60-74
- No versioning anywhere → Score <40

**Principle: "Everything is Recoverable"** (Metrics: event sourcing + idempotency + retry)
- JSONL event log + content_hash dedup + idempotent keys → Score 90-100
- Event log exists, replay tested, 1-2 idempotent gaps → Score 75-89
- Retry logic present, no clear recovery path → Score 60-74
- No recovery strategy evident → Score <40

**Principle: "Everything is Secure"** (Metrics: secret masking + PII hashing + input validation)
- All secrets masked in logs + PII hashed + all endpoints validated → Score 90-100
- Secrets masked + PII mostly hashed + 80% endpoints validated → Score 75-89
- Partial masking + incomplete hashing + 50% validation → Score 60-74
- No security controls evident → Score <40

**Example principle scanning:**

**Principle: "Everything is Async"**
- Check for: `time.sleep()`, `requests.` (sync), blocking subprocess, `threading.Thread`, `BlockingIO`
- Command: `grep -rn "time.sleep\|requests\.\|BlockingIO\|threading\.Thread" $CODE_ROOT --include="*.py"`
- Calculate: blocking_lines / total_io_lines, map to numeric anchor via interpolation
- Example LLMem: If src/llmem/ has 2 blocking calls in 45 total I/O ops (4.4% blocking) → Score 85-88 (GOOD)

**Principle: "Everything is Documented"**
- Check for: public functions with docstrings
- Command: `grep -n "^def \|^class " $CODE_ROOT/**/*.py | xargs -I{} sh -c 'grep -A1 "{}" | grep "\"\"\"" || echo "MISSING"'`
- Calculate: (functions with docstrings / total public functions) × 100
- Example LLMem: If 42 of 48 public functions documented (87.5%) → Score 87 (GOOD)

**Principle: "Everything is Replaceable"**
- Check for: dependency injection patterns, registry pattern, pluggable providers
- Command: `grep -rn "@dataclass\|@injectable\|Registry\|Provider\|factory\|__init__" $CODE_ROOT --include="*.py" | wc -l`
- Assess module boundaries: can backend be swapped (InMemory ↔ Qdrant)?
- Example LLMem: Backend interface in storage/backends/ + both InMemory & Qdrant + DI in api/server.py:20-30 → Score 92 (EXCELLENT)

**Principle: "Everything is Observable"**
- Check for: logging calls, error handling, metrics instrumentation
- Command: `grep -rn "logger\.\|log\.\|metric\.\|trace\.\|error\|exception" $CODE_ROOT --include="*.py" | wc -l`
- Measure: log lines per KLOC (kilo-lines-of-code)
- Example LLMem: If src/llmem has ~3 log/KLOC + structured JSON logs + request ID correlation → Score 78 (GOOD)

**Principle: "Everything is Tested"**
- Check for: test-to-code ratio, coverage hints, test patterns
- Command: `find tests/ -name "test_*.py" | xargs wc -l | tail -1`
- Calculate: (test LOC / code LOC) ratio
- Example LLMem: If test LOC = 8200, code LOC = 13000 (ratio 0.63) + coverage 72% → Score 80 (GOOD)

**Principle: "Everything is Versioned"**
- Check for: API versioning, schema versioning, migration markers
- Command: `grep -rn "v[0-9]\|version\|schema\.v" $CODE_ROOT --include="*.py" | wc -l`
- Example LLMem: All routes have /v1/ prefix + models.py has schema.v1 + structured versioning → Score 92 (EXCELLENT)

**Principle: "Everything is Recoverable"**
- Check for: fallback strategies, idempotent operations, event sourcing
- Command: `grep -rn "idempotent\|fallback\|recover\|replay\|retry\|backoff" $CODE_ROOT --include="*.py"`
- Example LLMem: JSONL append-only + idempotency_key in capture + rebuild command tested → Score 85 (GOOD)

**Principle: "Everything is Secure"**
- Check for: secret masking, PII hashing, auth checks, input validation
- Command: `grep -rn "mask\|hash\|sanitiz\|validate\|auth\|secret" $CODE_ROOT --include="*.py"`
- Example LLMem: triage/patterns.py detects + masks secrets + hashes PII, input validated → Score 89 (EXCELLENT)

**Output Template:**

| Princip | Score | Violations Found | Evidence (file:line) | Confidence |
|---------|-------|------------------|----------------------|------------|
| Everything is Async | 78 | `requests.post()` in capture_service.py, 2 `time.sleep()` in tests | src/llmem/services/capture.py:45, tests/test_capture.py:120 | HIGH |
| Everything is Documented | 82 | 6 public functions missing docstrings | src/llmem/recall/pipeline.py:12, :34, :67 | HIGH |
| Everything is Replaceable | 88 | Backend swappable via DI, all providers registered | src/llmem/api/server.py:20-30 | HIGH |
| Everything is Observable | 71 | Sparse logging in hot path (capture_event) | src/llmem/services/capture.py:15-40 | MEDIUM |
| Everything is Tested | 75 | Test:code ratio 0.62, missing tests for edge cases | tests/test_triage.py vs src/llmem/triage/ | MEDIUM |
| Everything is Versioned | 92 | API routes have /v1/ prefix, schema.v1 in models | src/llmem/api/routes/__init__.py, models.py | HIGH |
| Everything is Recoverable | 85 | Event-sourced JSONL log, idempotent with keys, fail-open design | src/llmem/storage/log_jsonl.py, services/capture.py | HIGH |
| Everything is Secure | 89 | Secrets masked, PII hashed, regex patterns tested | src/llmem/triage/patterns.py, heuristics.py | HIGH |

**A0 Score (Principle Alignment Overall):**
```
A0 = average of all 8 principle scores
   = (78 + 82 + 88 + 71 + 75 + 92 + 85 + 89) / 8
   = 82
```

**Minimum:**
- Per-principle score 0-100 with exact violations listed
- Evidence: file:line references (not vague)
- Confidence level per principle (HIGH/MEDIUM/LOW)
- A0 overall score

**Anti-patterns:**
- ❌ Don't score without evidence — always cite file:line
- ❌ Don't give 100% without verifying every public function/async call
- ❌ Don't skip any principle — even if "perfect", score it as such with evidence
- ❌ Don't make up violations — only cite what you actually found

---

### 7.3) A2: Architectural Scanning (A1-A19 dimensions)

**Co:** Evaluate all 19 remaining dimensions across 4 groups (Coherence, Modularity, Scalability, Evolution).

**Jak:** For each dimension below, apply scoring criteria. Organize by group.

#### **GROUP 1: KOHERENCE (A1-A4) — Layer Integrity**

**A1: Layer Isolation** (Are layers properly separated?)
- WHAT: API layer ↔ service layer ↔ storage layer boundaries
- HOW: Check for direct DB access in API routes; service use in storage
- WHERE: `src/llmem/api/routes/*.py`, `src/llmem/services/*.py`, `src/llmem/storage/*.py`
- Scoring:
  - 90-100: All imports follow layering (routes→services→storage), no cross-cutting imports
  - 70-89: Minor layer violations (1-2 places), quickly fixable
  - 40-69: Scattered layer violations, mixed concerns visible
  - 0-39: No clear layering, tangled dependencies
- Evidence: Import graph snapshot (what imports what)

**A2: Message Flow Consistency** (Do async events flow predictably?)
- WHAT: Event capture → triage → storage pipeline, no out-of-order processing
- HOW: Trace ObservationEvent lifecycle; check for race conditions, lost events
- WHERE: `src/llmem/services/capture.py`, `src/llmem/triage/`, `src/llmem/storage/`
- Scoring:
  - 90-100: JSONL source of truth, idempotent upserts, event replay tested
  - 70-89: Event log exists, idempotency keys present, one missing test
  - 40-69: Events processed, no clear replay strategy
  - 0-39: Non-deterministic processing, lost events possible
- Evidence: Capture flow diagram + relevant code lines

**A3: Pattern Consistency** (Are architectural patterns uniform?)
- WHAT: Service layer uses same pattern (init, main method, error handling)
- HOW: Compare CaptureService vs RecallService vs any custom logic
- WHERE: `src/llmem/services/`, `src/llmem/recall/`
- Scoring:
  - 90-100: Both services follow identical init/execute/error pattern
  - 70-89: ~80% pattern consistency, minor style differences
  - 40-69: Inconsistent patterns, ~50% duplicated logic
  - 0-39: Each service custom-built, duplicated logic everywhere
- Evidence: Pattern comparison table (init signature, method names, error handling)

**A4: API Surface** (Is the API stable and scoped?)
- WHAT: `/capture/event`, `/capture/batch`, `/recall` endpoints — no hidden endpoints, no leaky abstractions
- HOW: Enumerate all routes; check if they expose internal types or are RESTful
- WHERE: `src/llmem/api/routes/`
- Scoring:
  - 90-100: 3-5 well-defined endpoints, no internal type leakage, versioned
  - 70-89: 5-7 endpoints, minor leakage (1-2 internal types visible), versioned
  - 40-69: 8+ endpoints, leaky (internal storage types exposed), partial versioning
  - 0-39: Chaotic endpoint design, no versioning
- Evidence: OpenAPI/route listing with input/output types

---

#### **GROUP 2: MODULARITA (A5-A10) — Decomposition & Separation of Concerns**

**A5: Module Cohesion** (Are modules tightly focused?)
- WHAT: Each module (triage/, storage/, recall/) has single responsibility
- HOW: Inspect imports within each module; count modules with 3+ distinct purposes
- WHERE: `src/llmem/triage/`, `src/llmem/storage/`, `src/llmem/recall/`, `src/llmem/embeddings/`
- Scoring:
  - 90-100: Each module focused (triage=extraction, storage=persistence, recall=retrieval), 1 responsibility each
  - 70-89: Mostly focused, 1-2 modules doing 2 things
  - 40-69: Mixed concerns, ~50% modules doing 2+ things
  - 0-39: Module spaghetti, no clear boundaries
- Evidence: Module responsibility matrix (module name → [responsibilities])

**A6: Extractable Components** (Can subparts be used independently?)
- WHAT: Triage heuristics extracted to patterns.py; embeddings pluggable; storage backends swappable
- HOW: Try conceptually: Can I import `triage.heuristics` without `services`? Can I swap HashEmbedder for SemanticEmbedder?
- WHERE: `src/llmem/triage/patterns.py`, `src/llmem/embeddings/`, `src/llmem/storage/backends/`
- Scoring:
  - 90-100: All major subsystems extractable and independently testable
  - 70-89: 2-3 subsystems extractable, 1 tightly coupled
  - 40-69: ~50% extractable, major tangling
  - 0-39: Monolithic, no clear component boundaries
- Evidence: Extraction feasibility checklist per component

**A7: Testability** (Is code structured for testing?)
- WHAT: Dependency injection, mocks, test doubles, isolated units
- HOW: Count unmockable dependencies; check for tight coupling in services
- WHERE: `tests/`, `src/llmem/services/`, `src/llmem/api/`
- Scoring:
  - 90-100: Full DI, all backends mockable, 80%+ test coverage
  - 70-89: Mostly DI, some hardcoded deps, 60-80% coverage
  - 40-69: Mixed DI, several hardcoded deps, 40-60% coverage
  - 0-39: No DI, difficult to mock, <40% coverage
- Evidence: Coverage report (if available) + testability assessment per module

**A8: State Management** (Is mutable state isolated and bounded?)
- WHAT: Storage backends (InMemory, Qdrant) own their state; no globals
- HOW: Grep for global/class-level state; check for thread-unsafe data structures
- WHERE: `src/llmem/storage/backends/`, `src/llmem/api/server.py`
- Scoring:
  - 90-100: All state encapsulated, no globals, thread-safe constructs
  - 70-89: Mostly encapsulated, 1-2 globals for config, mostly safe
  - 40-69: Mixed state ownership, some unsafe globals, threading issues possible
  - 0-39: Uncontrolled globals, race conditions visible
- Evidence: State ownership diagram + grep results for `global`, class vars

**A9: Configuration Architecture** (Is config externalized and flexible?)
- WHAT: `config.py` uses pydantic-settings, env vars, no hardcoded values
- HOW: Verify all config sources (env, file, defaults); check for overrides
- WHERE: `src/llmem/config.py`, `src/llmem/api/server.py` (initialization)
- Scoring:
  - 90-100: Full pydantic-settings, env vars, file-based, no hardcoded values, clear override hierarchy
  - 70-89: Config externalized, 1-2 hardcoded defaults acceptable, env vars mostly used
  - 40-69: Mixed config sources, several hardcoded values, unclear override order
  - 0-39: Hardcoded config, no external sourcing
- Evidence: Config sources table (env var name → type → default)

**A10: Tool Ecosystem** (Is the build/test/deploy tooling mature?)
- WHAT: Makefile targets, pytest, linting, CI/CD-readiness
- HOW: Count make targets; verify pytest fixtures, linting coverage
- WHERE: `Makefile`, `pytest.ini`, `.ruff.toml`, `.github/workflows/` (if present)
- Scoring:
  - 90-100: Rich make targets (dev, test, lint, run, build), pytest fixtures, ruff configured, CI/CD ready
  - 70-89: Core targets (test, lint, run), fixtures present, CI/CD partial
  - 40-69: Minimal targets, some fixtures, linting basic
  - 0-39: Manual test/build, no tooling structure
- Evidence: Makefile target list + linting/testing coverage

---

#### **GROUP 3: ŠKÁLOVATELNOST (A11-A16) — Growth & Extensibility**

**A11: Memory Architecture** (Can the system scale to millions of memories?)
- WHAT: Efficient search (vector indexing), batch operations, dedup strategy
- HOW: Check Qdrant backend indexing (HNSW), batch endpoint, dedup logic
- WHERE: `src/llmem/storage/backends/qdrant.py`, `src/llmem/recall/pipeline.py` (dedup)
- Scoring:
  - 90-100: HNSW indexing, batch capture, content_hash dedup, query budgeting
  - 70-89: Indexing present, batch endpoint, dedup working
  - 40-69: Linear search fallback, no batch optimization
  - 0-39: O(n) search, no scaling strategy
- Evidence: Backend implementation review + query plan

**A12: Persistence Layer** (Can data survive restarts and scale?)
- WHAT: JSONL event sourcing + backend persistence, corruption recovery
- HOW: Verify JSONL appends, backend consistency, rebuild logic
- WHERE: `src/llmem/storage/log_jsonl.py`, `src/llmem/api/routes/doctor.py` (rebuild)
- Scoring:
  - 90-100: Append-only JSONL as source of truth, backend is cache, rebuild tested
  - 70-89: JSONL present, rebuild possible, one consistency gap
  - 40-69: Partial event sourcing, rebuild risky
  - 0-39: No event log, data loss on failure
- Evidence: Persistence flow diagram + rebuild test

**A13: Distribution Readiness** (Can multiple instances coexist?)
- WHAT: Per-instance isolation (Qdrant collections), no shared state, distributed-safe IDs
- HOW: Check instance ID handling, collection scoping, idempotency keys
- WHERE: `config.py` (instance setting), `src/llmem/storage/backends/` (collection scoping)
- Scoring:
  - 90-100: Per-instance collections, UUID-based IDs, idempotent ops, no shared state
  - 70-89: Per-instance design mostly present, 1-2 shared config concerns
  - 40-69: Partial instance isolation, some shared state risk
  - 0-39: Single-instance assumption baked in
- Evidence: Instance isolation checklist

**A14: LLM Provider Flexibility** (Can we swap embedding providers?)
- WHAT: Embeddings abstraction, pluggable providers, no hardcoded model names
- HOW: Check embeddings interface, provider registration
- WHERE: `src/llmem/embeddings/`, `src/llmem/api/server.py` (embedder injection)
- Scoring:
  - 90-100: Embedder interface, multiple impl (HashEmbedder, can add SemanticEmbedder), DI-injected
  - 70-89: Interface exists, 1 impl only but swappable, DI-injected
  - 40-69: Embedder hardcoded in 1-2 places
  - 0-39: Tight coupling to specific embedding model
- Evidence: Embeddings abstraction + provider registration

**A15: Tool Sandboxing** (Are external tool calls isolated?)
- WHAT: Tool execution context (if used for agent function calling)
- HOW: If tools are used, check for sandboxing, timeout, resource limits
- WHERE: TBD — depends on tool usage in agents
- Scoring:
  - 90-100: Sandboxed execution, timeouts, resource limits, error isolation
  - 70-89: Basic isolation, timeout present
  - 40-69: Minimal safeguards
  - 0-39: No sandboxing (or not applicable if no tool execution)
- Evidence: Tool execution policy (if applicable)

**A16: Observability** (Can we debug production issues?)
- WHAT: Structured logging, metrics, tracing, health checks
- HOW: Count log lines with context (request ID, instance ID); check for metrics instrumentation
- WHERE: Throughout `src/llmem/`, `/healthz` endpoint
- Scoring:
  - 90-100: Structured logs (JSON), request correlation, metrics emitted, health check detailed
  - 70-89: Structured logs, partial correlation, basic metrics
  - 40-69: Unstructured logs, minimal metrics
  - 0-39: Sparse logging, no observability
- Evidence: Logging example + metrics list

---

#### **GROUP 4: EVOLUCE (A17-A19) — Change & Future-Proofing**

**A17: Backlog Alignment** (Does architecture support planned features?)
- WHAT: T1/T2 epics (new features in 3-6 month roadmap) can be built without major refactoring
- HOW: For each T1/T2 epic, assess architectural readiness (abstractions exist, no blockers)
- WHERE: `backlog/`, codebase
- Scoring:
  - 90-100: All T1/T2 epics aligned, <10% refactoring tax
  - 70-89: Most epics aligned, 10-20% refactoring tax
  - 40-69: 50% of epics face architectural blockers, 20-40% tax
  - 0-39: Major blockers for most epics, >40% refactoring needed
- Evidence: Per-epic readiness table (epic → blockers → refactoring estimate)

**A18: Complexity Hotspots** (Where do most bugs and changes occur?)
- WHAT: Functions/modules with high cyclomatic complexity or low test coverage
- HOW: Grep for nested loops/conditionals; correlate with test coverage gaps
- WHERE: All `.py` files with complexity scoring
- Scoring:
  - 90-100: Max cyclomatic complexity <10, all hotspots tested, low churn
  - 70-89: Max complexity <15, hotspots mostly tested, moderate churn
  - 40-69: Max complexity 15-25, gaps in testing, high churn areas
  - 0-39: Complexity >25, untested hotspots, frequent changes
- Evidence: Top-10 complex functions with file:line + complexity score

**A19: ADR Coverage** (Are architectural decisions documented?)
- WHAT: Decisions in `fabric/decisions/` covering major choices
- HOW: Scan ADR filenames; count decisions in codebase vs documented
- WHERE: `fabric/decisions/`, codebase review
- Scoring:
  - 90-100: 8+ ADRs covering: secrets policy, ID generation, event-sourcing, injection, backends, versioning, testing, security
  - 70-89: 5-7 ADRs covering major decisions
  - 40-69: 3-4 ADRs, some key decisions undocumented
  - 0-39: <3 ADRs, most decisions undocumented
- Evidence: ADR checklist (which decisions documented, which missing)

---

**Output Template for All Dimensions (A1-A19):**

| Dimension | Group | Score | Severity | Confidence | Key Findings | Evidence |
|-----------|-------|-------|----------|------------|--------------|----------|
| A1: Layer Isolation | KOHERENCE | 88 | 🟢 GOOD | HIGH | API routes don't access DB directly; one util import crossing layers | src/llmem/api/routes/capture.py:12 imports storage util; fix: move to service layer |
| A2: Message Flow | KOHERENCE | 92 | 🟢 EXCELLENT | HIGH | JSONL log + idempotent upserts; event replay tested | src/llmem/storage/log_jsonl.py, tests/test_triage_and_recall.py |
| A3: Pattern Consistency | KOHERENCE | 78 | 🟡 NEEDS ATTENTION | MEDIUM | CaptureService and RecallService differ in error handling; one uses logger, one prints | src/llmem/services/capture.py vs recall.py |
| ... | ... | ... | ... | ... | ... | ... |
| A19: ADR Coverage | EVOLUCE | 72 | 🟡 NEEDS ATTENTION | HIGH | 6 ADRs present; missing docs for "distributed instance coordination" and "embedding provider versioning" | fabric/decisions/ listing |

**Scoring Scale (for severity emoji):**
- 🟢 EXCELLENT: 90-100 (no action needed unless strategic)
- 🟢 GOOD: 70-89 (no blocker, monitor)
- 🟡 NEEDS ATTENTION: 40-69 (plan fix in next cycle)
- 🔴 CRITICAL: 0-39 (blocks features or causes bugs, fix immediately)

**Minimum:**
- All 20 dimensions scored (0-100)
- Per-dimension severity emoji
- Confidence level (HIGH/MEDIUM/LOW)
- Specific evidence (file:line, not vague)
- Key findings per dimension

**Anti-patterns with detection bash & fix procedures (WQ4):**

**Anti-pattern A: God Class (single class with 10+ methods + 2+ responsibilities)**
- Detection bash: `find $CODE_ROOT -name "*.py" -exec grep -l "^class " {} \; | while read f; do METHODS=$(grep -c "^\s*def " "$f"); if [ $METHODS -gt 10 ]; then echo "$f: $METHODS methods"; fi; done`
- Fix procedure:
  1. Identify the god class and its distinct responsibilities
  2. Extract each responsibility to separate class
  3. Original class becomes coordinator/factory
  4. Update imports throughout codebase

**Anti-pattern B: Circular dependencies (module A imports B, B imports A)**
- Detection bash: `for f in $CODE_ROOT/**/*.py; do grep "^from\|^import" "$f" | while read imp; do TARGET=$(echo "$imp" | sed 's/from //; s/ import.*//'); if grep -l "from.*$(basename $f .py)\|import.*$(basename $f .py)" "$CODE_ROOT/**/$TARGET.py" 2>/dev/null; then echo "CIRCULAR: $f <-> $TARGET"; fi; done; done | sort | uniq`
- Fix procedure:
  1. Introduce abstraction layer or intermediate module
  2. Move shared code to common module
  3. Break import cycle by one party delegating

**Anti-pattern C: Missing abstraction layer (hardcoded storage backend in service)**
- Detection bash: `grep -rn "InMemoryBackend\|QdrantBackend" $CODE_ROOT/services/ --include="*.py"`
- If results are non-empty: Fix procedure:
  1. Define backend interface (if not exists)
  2. Inject backend via dependency injection
  3. Update service constructors to accept backend parameter

**Anti-pattern D: Hardcoded config values (string literals instead of env vars or config object)**
- Detection bash: `grep -rn 'localhost:6333\|port.*=.*80\|host.*=.*"' $CODE_ROOT --include="*.py" | grep -v "#.*\|test\|comment" | head -20`
- Fix procedure:
  1. Extract to config.py using pydantic-settings
  2. Replace all occurrences with config.<field>
  3. Verify all values can be overridden via env vars

**Anti-pattern E: Undocumented API surface (endpoint without docstring or OpenAPI schema)**
- Detection bash: `grep -rn "@router\|@app" $CODE_ROOT/api/routes/ --include="*.py" -A2 | grep -B2 "^def " | grep -v '"""' | grep "def "`
- Fix procedure:
  1. Add docstring to each route handler with description, params, responses
  2. Ensure all request/response models are documented
  3. Validate against OpenAPI spec

---

### 7.4) A3: Backlog Cross-Check (with filled-in LLMem example — WQ2 fix)

**Co:** For each T1/T2/T3 epic in backlog/, assess if current architecture supports building it.

**Jak:**
1. Extract title + description from each epic file
2. Identify what new abstractions or changes are needed
3. Check if prerequisites exist in codebase (e.g., "add semantic embeddings" needs embeddings interface — does it exist?)
4. Estimate refactoring effort as % of feature effort (10% = needs small fix; 40% = major prep work)
5. Mark blockers (unmet prerequisites that must be fixed first)

**Example Assessment with LLMem project data (WQ2 fix):**

| Epic | T | Architectural Readiness | Blockers | Refactoring % | Notes |
|------|---|------------------------|----------|--------------|-------|
| Semantic Embeddings | T1 | 85% ready | None — embeddings interface (HashEmbedder) exists in src/llmem/embeddings/ | 15% | Just create SemanticEmbedder impl + register in server.py:DI |
| Distributed Recall (multi-instance) | T1 | 40% ready | No cross-instance query API; per-instance collection isolation incomplete in Qdrant backend | 40% | Must add instance routing layer + collection naming scheme in storage/backends/qdrant.py |
| Admin Web Dashboard | T2 | 95% ready | None — /memories and /healthz endpoints stable; routes in api/routes/memories.py | 5% | Frontend only; API contracts stable as of v1 |
| GraphQL API Gateway | T2 | 60% ready | No query normalization layer; schema versioning undefined (now /v1/ routes but not schema.v1) | 35% | Add schema.v2 definitions + GraphQL-to-REST translation layer |
| PostgreSQL Backend | T1 | 50% ready | Event sourcing to JSONL incomplete; migration system missing | 45% | First finish log_jsonl.py rebuild logic; then design pg schema + migrations |
| PII/Secret Audit Trail | T1 | 92% ready | Minimal — triage/patterns.py already masks secrets; just add audit log endpoint | 8% | Add /memories/{id}/audit endpoint returning access history; minor API changes |

**Minimum:**
- Per-epic readiness % (estimate: ready to start with ≥80%)
- Blocker list per epic (what must be fixed first)
- Refactoring estimate as % of feature effort
- Confidence (can we commit to this timeline?)

**Anti-patterns:**
- ❌ Don't assess without reading epic description AND relevant code
- ❌ Don't ignore T3 epics (future features still inform architecture)
- ❌ Don't assume blockers — verify they're not already resolved

---

### 7.5) A4: Synthesis & Scoring

**Co:** Calculate weighted overall score, determine verdict, identify cross-dimensional insights.

**Scoring Formula:**

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

**WEIGHT JUSTIFICATION TABLE:**

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

**WQ5 enforcement — all scoring dimensions must have explicit measurable methods (not subjective judgment):**

Each scoring method above includes:
- **WHAT:** Clear definition (not vague goal)
- **HOW:** Bash command or code review step (reproducible)
- **WHERE:** Specific files/paths (not "the codebase")
- **Scoring anchors:** Numeric thresholds mapped to 0-100 scale (not "good/bad" opinions)
- **Evidence requirement:** File:line citations (not assertions)

Example check before submitting:
```bash
# Verify scoring is not subjective opinion
grep -n "seems\|appears\|probably\|likely\|might\|complex-ish" architect-report.md
# Should be 0 results; any hits = rewrite with measurable criteria
```

**Jak:**
1. Compile all 20 dimension scores (A0-A19)
2. Apply weights per formula above
3. Calculate sum and divide by sum of weights (28)
4. Determine verdict based on thresholds
5. Identify top-5 CRITICAL findings (🔴 score <40 or blocking T1 epic)
6. Identify top-5 hotspots (complex, low-coverage, high-churn modules)
7. Create cross-dimensional insight table (e.g., "Poor observability (A16) explains test gaps (A7)")

**Cross-Dimensional Insights Table:**

| Finding | Dimensions Involved | Impact | Recommendation |
|---------|-------------------|--------|-----------------|
| Sparse logging in capture hot path limits debugging | A16, A7, A3 | Hard to test async race conditions; production issues opaque | Add structured logging to capture_event; use request IDs |
| InMemory backend not tested at scale; Qdrant untested in CI | A11, A7, A10 | Risk of silent data loss; scale unknown | Add integration tests for both backends; scale tests in CI |
| ADRs missing for distributed recall design | A13, A19 | Risk of misaligned implementation; future work will redo | Add ADR for instance routing; document early |

**Minimum:**
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

### 7.6) A5: Mutations (default mode only — skip if --no-fix)

**Co:** Generate concrete backlog changes based on findings. Only in default mode.

**MUTATION VALIDATION (REQUIRED before creation):**

Before creating any backlog mutation, VALIDATE:

```bash
# For each dimension with score < 70 identified for mutation:
# 1. Verify the score is actually below threshold
# 2. Verify the evidence is concrete (file:line, not vague)
# 3. Verify acceptance criteria will actually raise score above threshold

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

Only create mutation if validation PASS.

**Jak:**

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

**Mutation Specification Template:**

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

**Minimum:**
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

## §8 Quality Gates

**All gates MUST PASS. Skill reports failure mode if any gate fails.**

| Gate | Criterion | PASS | FAIL |
|------|-----------|------|------|
| **Gate 1: Dimension Coverage** | All 20 dimensions (A0-A19) have scores | 20/20 scored | <20 scored → FAIL |
| **Gate 2: Evidence Requirement** | Each score backed by file:line refs (not vague) | ≥95% of scores have evidence | <80% with evidence → FAIL |
| **Gate 3: Scoring Consistency** | Self-verify: scored dimensions based on actual code read, not assumptions | All dimensions justified | Any dimension scored without reading → FAIL |
| **Gate 4: Mutation Validity (default mode only)** | All new backlog items have acceptance criteria + estimate | All mutations meet spec | Any mutation vague → FAIL (report issue, don't create) |

**On gate failure:**
- Report which gate failed
- Stop before creating mutations (if applicable)
- List violations preventing progress
- Guidance for operator: what to fix

---

## §9 Report

**Output file:** `reports/architect-{YYYY-MM-DD}.md`

**Schema:** fabric.report.v1

**Fields:**
```yaml
kind: architect
title: "Architectural Analysis Report"
date: 2026-03-05
codebase: "llmem"
version: "1.0"                                    # WQ9 fix: track report schema version
run_id: "architect-2026-03-05-abc123"            # WQ9 fix: unique run identifier
created_at: "2026-03-05T14:30:00Z"               # WQ9 fix: ISO 8601 timestamp
status: "PASS"                                    # WQ10 fix: CRITICAL findings → FAIL status
version_hash: "{git_commit_hash_or_state_hash}"

summary:
  overall_score: 76
  verdict: "NEEDS ATTENTION"
  dimensions_scored: 20
  critical_findings: 3
  mutations_count: 4
  adrs_created: 2

principle_alignment:
  score: 82
  violations_by_principle: [...]

dimension_scores:
  coherence:
    - {dim: "A1: Layer Isolation", score: 88, severity: "🟢 GOOD"}
    - {dim: "A2: Message Flow", score: 92, severity: "🟢 EXCELLENT"}
    ...

backlog_impact:
  ready_for_sprint: ["Web UI Dashboard", "Monitoring"]
  blocked_by_architecture: ["Distributed Recall", "PostgreSQL Backend"]

critical_findings:                              # WQ10 fix: CRITICAL (🔴) findings MUST block (status=FAIL)
  - {dim: "A16: Observability", issue: "Sparse logging in hot path", fix: "Add request ID correlation; structured logs", severity: "CRITICAL"}
  - {dim: "A11: Memory Architecture", issue: "Linear search will scale to O(n) at 100K+ memories", fix: "Implement HNSW indexing in Qdrant", severity: "CRITICAL"}

hotspots:
  - {file: "src/llmem/recall/pipeline.py", complexity: 18, coverage: 62}
  - ...

cross_dimensional_insights:
  - {finding: "Poor observability limits testing", dims: ["A16", "A7", "A3"]}

mutations:
  - {type: "T0", title: "Refactor capture service for async", status: "created"}
  - ...

adr_creations:
  - {title: "Distributed Instance Coordination", file: "reports/adr/ADR-020.md"}

next_steps:
  - "Apply T0 mutations before next feature sprint"
  - "Improve observability (A16) to enable faster debugging"
  - "Document distributed recall design in ADR"
```

**Include in report body:**
- Full dimension scoring table (A0-A19)
- Evidence sections (file:line references)
- Top-5 critical findings with remediation
- Cross-dimensional insights
- Mutation summary (T0/T1 count, each with estimate)
- Verdict explanation

---

## §10 Self-check (12+ items)

**Run before completing skill:**

**Existence Checks:**
- [ ] Report file `reports/architect-{YYYY-MM-DD}.md` created
- [ ] All mutations written to `backlog/` (if default mode)
- [ ] ADR files created for undocumented decisions (if A19 < 80)
- [ ] Protocol log has START and END timestamps
- [ ] Backlog index updated with new items + counts

**Quality Checks:**
- [ ] All 20 dimensions scored (A0-A19)
- [ ] Weighted formula correctly applied: (A0×2 + ... + A19) / 28
- [ ] Each CRITICAL (🔴) finding has corresponding T0 mutation (default mode)
- [ ] Evidence is file:line specific, not vague ("src/llmem/services/capture.py:45" not "capture service")
- [ ] Verdict matches score range (≥80 → SOLID, <40 → REDESIGN, etc.)
- [ ] Cross-dimensional insights table present (≥3 insights)

**Invariant Checks:**
- [ ] Zero code files modified (architect is read-only analysis)
- [ ] Only mutations: backlog files, ADR files, report file
- [ ] In --no-fix mode: zero backlog mutations created (only report)
- [ ] All new backlog items in `backlog/` with proper filename (`T0-architect-*.md`)
- [ ] No external API calls (all analysis local)

**Anti-patterns Final Check:**
- [ ] Didn't skip vision.md reading
- [ ] Didn't assume architecture — verified with code
- [ ] Didn't give 100% scores without extensive evidence
- [ ] Didn't skip any dimension
- [ ] Didn't create vague mutations (all have AC + estimate + files)

---

## §11 Failure Handling

| Phase | Error | Action |
|-------|-------|--------|
| **Preconditions** | vision.md missing | STOP immediately — cannot score without vision principles. Log: "CRITICAL: vision.md required." Exit code 1. |
| **Pre-flight (A0)** | No .py files found | STOP — nothing to analyze. Log error, exit code 1. |
| **A1 Scanning** | Cannot parse file (syntax error) | WARN + skip file + note in report "File skipped due to parse error: {file}". Continue with other files. |
| **A2-A4 Scanning** | Confidence <50% on >50% of dimensions | REPORT WARN in final report: "High uncertainty on this analysis. Confidence: 50%. Consider manual review." Mark those dimensions LOW confidence. |
| **Mutation Creation (default mode)** | Cannot write to backlog/ | WARN + list mutations in report with message: "Mutations not created. Apply manually:" + show each mutation spec. |
| **Report Write Failure** | Cannot create reports/ directory | STOP + exit. Log: "Cannot write report — check permissions." Exit code 1. |

**Operator Guidance on Errors:**
- Missing precondition → fix precondition, re-run skill
- Parse error → fix syntax, re-run skill
- Low confidence → manually review hotspots; re-run with --strategy=DEEP
- Backlog write fail → manually apply mutations from report

---

## §12 Metadata

```yaml
phase: orientation
step: architect
skills:
  - fabric-architect (this skill)
dependencies_required:
  - fabric-init (must run first)
dependencies_optional:
  - fabric-intake (if new observations to triage)
depends_on: [fabric-init, fabric-vision]
feeds_into: [fabric-process, fabric-gap, fabric-sprint, fabric-implement]
may_modify_state: false
may_modify_backlog: true    # default mode only — creates T0/T1 items, ADRs, priority shifts
may_modify_code: false      # architect is read-only; never modifies source
may_create_intake: true     # can generate new intake items if observations found
output_kind: report
output_schema: fabric.report.v1
report_fields:
  - kind: architect
  - score: 0-100
  - verdict: SOLID|NEEDS_ATTENTION|REFACTOR_FIRST|REDESIGN
  - dimensions_scored: 20
  - mutations_count: 0-N
  - critical_findings: list
runtime_limit: 5 minutes  # analysis should complete quickly; anything longer suggests bugs in scanning
cron_schedule: "null"     # manual trigger only (not a background job)
runs_in_session: true     # operates within fabric planning session
isolation: full           # no side effects beyond backlog + report
repeatable: true          # can re-run; will overwrite prior report
```

---

## Closure Notes

**fabric-architect** is the architectural quality gatekeeper. It runs after `fabric-init`, scans the codebase against the vision, and surfaces debt systematically.

Without it: architecture silently drifts. Decisions fragment. Refactoring becomes reactive ("it's broken") instead of proactive ("we planned this").

With it: every decision is scored, every blocker is documented, every mutation is concrete.

Workflow:
```
fabric-init
   ↓
fabric-architect (you are here)
   ↓
fabric-prio (prioritizes backlog using architect findings)
   ↓
fabric-sprint (selects features/refactoring mix for next cycle)
```

---

**End of SKILL.md**

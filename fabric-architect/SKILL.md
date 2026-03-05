---
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

## §2 Protokol

Uses standard `protocol_log.py` with:
```
skill = "architect"
phase = "orientation"
action = "analyze"
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
5. Assign score 0-100 based on adherence % + severity weighting

**Example principle scanning:**

**Principle: "Everything is Async"**
- Check for: `time.sleep()`, `requests.` (sync), blocking subprocess, `threading.Thread`, `BlockingIO`
- Command: `grep -rn "time.sleep\|requests\.\|BlockingIO\|threading\.Thread" $CODE_ROOT --include="*.py"`
- Violations per file + context (what operation, why blocking)
- Score: 100% async code → 95-100; <10% blocking → 85-94; >20% blocking → <70

**Principle: "Everything is Documented"**
- Check for: public functions with docstrings
- Command: `grep -n "^def \|^class " $CODE_ROOT/**/*.py | xargs -I{} sh -c 'grep -A1 "{}" | grep "\"\"\"" || echo "MISSING"'`
- Calculate: (functions with docstrings / total public functions) × 100
- Score: ≥90% → 90-100; 70-89% → 70-89; <70% → <70

**Principle: "Everything is Replaceable"**
- Check for: dependency injection patterns, registry pattern, pluggable providers
- Command: `grep -rn "@dataclass\|@injectable\|Registry\|Provider\|factory\|__init__" $CODE_ROOT --include="*.py" | wc -l`
- Assess module boundaries: can backend be swapped (InMemory ↔ Qdrant)?
- Score: Clean DI + multiple backends → 85-100; Some DI, single backend → 70-84; No DI, monolithic → <70

**Principle: "Everything is Observable"**
- Check for: logging calls, error handling, metrics instrumentation
- Command: `grep -rn "logger\.\|log\.\|metric\.\|trace\.\|error\|exception" $CODE_ROOT --include="*.py" | wc -l`
- Measure: log lines per KLOC (kilo-lines-of-code)
- Score: >5 log/KLOC + structured logs → 85-100; 2-5 log/KLOC → 70-84; <2 → <70

**Principle: "Everything is Tested"**
- Check for: test-to-code ratio, coverage hints, test patterns
- Command: `find tests/ -name "test_*.py" | xargs wc -l | tail -1`
- Calculate: (test LOC / code LOC) ratio
- Score: >1.0 ratio → 85-100; 0.5-1.0 → 70-84; <0.5 → <70

**Principle: "Everything is Versioned"**
- Check for: API versioning, schema versioning, migration markers
- Command: `grep -rn "v[0-9]\|version\|schema\.v" $CODE_ROOT --include="*.py" | wc -l`
- Score: Explicit versioning in API + data models → 85-100; Partial versioning → 70-84; None → <40

**Principle: "Everything is Recoverable"**
- Check for: fallback strategies, idempotent operations, event sourcing
- Command: `grep -rn "idempotent\|fallback\|recover\|replay\|retry\|backoff" $CODE_ROOT --include="*.py"`
- Score: Event-sourced log + idempotent writes → 85-100; Retry logic only → 70-84; None → <40

**Principle: "Everything is Secure"**
- Check for: secret masking, PII hashing, auth checks, input validation
- Command: `grep -rn "mask\|hash\|sanitiz\|validate\|auth\|secret" $CODE_ROOT --include="*.py"`
- Score: Comprehensive secret + PII handling → 85-100; Partial masking → 70-84; None → <40

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

**Anti-patterns:**
- ❌ Don't score without reading relevant code
- ❌ Don't assume architecture — verify with grep/imports
- ❌ Don't skip LOW-confidence dimensions — score them but mark confidence
- ❌ Don't make findings vague; always cite file:line

---

### 7.4) A3: Backlog Cross-Check

**Co:** For each T1/T2/T3 epic in backlog/, assess if current architecture supports building it.

**Jak:**
1. Extract title + description from each epic file
2. Identify what new abstractions or changes are needed
3. Check if prerequisites exist in codebase (e.g., "add semantic embeddings" needs embeddings interface — does it exist?)
4. Estimate refactoring effort as % of feature effort (10% = needs small fix; 40% = major prep work)
5. Mark blockers (unmet prerequisites that must be fixed first)

**Example Assessment:**

| Epic | T | Architectural Readiness | Blockers | Refactoring % | Notes |
|------|---|------------------------|----------|--------------|-------|
| Semantic Embeddings | T1 | 85% ready | None — embeddings interface exists | 15% | Just plug in new impl; minor changes to config |
| Distributed Recall | T1 | 40% ready | No cross-instance query API; collection isolation incomplete | 40% | Must implement instance routing; high effort |
| Web UI Dashboard | T2 | 95% ready | None | 5% | API endpoints stable; just frontend work |
| GraphQL Gateway | T2 | 60% ready | No query normalization layer; schema versioning unclear | 35% | Need query safety layer; schema design effort |
| PostgreSQL Backend | T1 | 50% ready | No migration system; JSONL event sourcing unfinished | 45% | Must complete event sourcing first; then pg adapter |

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

**Weighting Rationale:**
- A0 (Principle Alignment) ×2: Foundation — all other dimensions rest on principles
- A1 (Layer Isolation) ×2: Core to modularity
- A2, A3, A4: Layer aspects, weight normally
- A5 (Cohesion) ×1.5: Directly impacts testability + change velocity
- A6, A7×1.5, A8, A9: Modularity components
- A10 ×1.5: Tooling forces quality (test, lint, build)
- A11 (Memory Arch) ×2: Scalability is critical for production
- A12 ×1.5, A13 ×2, A14, A15 ×2, A16 ×1.5: Scalability aspects
- A17 (Backlog Align) ×2: Strategic alignment drives all work
- A18, A19: Evolution aspects, normal weight

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

**Jak:**

1. **For each 🔴 CRITICAL dimension (score <40):**
   - Create new `backlog/T0-architect-{name}.md` refactoring task
   - Title: Concrete action (e.g., "T0: Refactor capture service for async/await compliance")
   - Acceptance criteria: Dimension must reach ≥70 after fix
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
version: "1.0.0"
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

critical_findings:
  - {dim: "A16: Observability", issue: "Sparse logging in hot path", fix: "Add request ID correlation; structured logs"}
  - ...

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

# Architectural Dimensions: A0-A19

This document defines all 20 dimensions used in fabric-architect scoring.

---

## GROUP 0: PRINCIPLES – A0

### A0: Principle Alignment (Overall)

**Definition:**
Average adherence of codebase to all 8 design principles from vision.md. Foundation for all other dimensions.

**Numeric Anchors & Interpolation:**

For all principle scoring, use this interpolation formula to convert metrics to 0-100 scale:
```
score = lower_threshold + (metric - lower_bound) / (upper_bound - lower_bound) × (upper_threshold - lower_threshold)
```

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

---

## GROUP 1: KOHERENCE – A1 to A4

### A1: Layer Isolation

**Definition:** Are layers properly separated? API layer ↔ service layer ↔ storage layer boundaries maintained.

**Scoring Criteria:**
- **90-100:** All imports follow layering (routes→services→storage), no cross-cutting imports
- **70-89:** Minor layer violations (1-2 places), quickly fixable
- **40-69:** Scattered layer violations, mixed concerns visible
- **0-39:** No clear layering, tangled dependencies

**Evidence:** Import graph snapshot (what imports what)

---

### A2: Message Flow Consistency

**Definition:** Do async events flow predictably? Event capture → triage → storage pipeline, no out-of-order processing.

**Scoring Criteria:**
- **90-100:** JSONL source of truth, idempotent upserts, event replay tested
- **70-89:** Event log exists, idempotency keys present, one missing test
- **40-69:** Events processed, no clear replay strategy
- **0-39:** Non-deterministic processing, lost events possible

**Evidence:** Capture flow diagram + relevant code lines

---

### A3: Pattern Consistency

**Definition:** Are architectural patterns uniform? Service layer uses same pattern (init, main method, error handling).

**Scoring Criteria:**
- **90-100:** Both services follow identical init/execute/error pattern
- **70-89:** ~80% pattern consistency, minor style differences
- **40-69:** Inconsistent patterns, ~50% duplicated logic
- **0-39:** Each service custom-built, duplicated logic everywhere

**Evidence:** Pattern comparison table (init signature, method names, error handling)

---

### A4: API Surface

**Definition:** Is the API stable and scoped? No hidden endpoints, no leaky abstractions.

**Scoring Criteria:**
- **90-100:** 3-5 well-defined endpoints, no internal type leakage, versioned
- **70-89:** 5-7 endpoints, minor leakage (1-2 internal types visible), versioned
- **40-69:** 8+ endpoints, leaky (internal storage types exposed), partial versioning
- **0-39:** Chaotic endpoint design, no versioning

**Evidence:** OpenAPI/route listing with input/output types

---

## GROUP 2: MODULARITA – A5 to A10

### A5: Module Cohesion

**Definition:** Are modules tightly focused? Each module has single responsibility.

**Scoring Criteria:**
- **90-100:** Each module focused (triage=extraction, storage=persistence, recall=retrieval), 1 responsibility each
- **70-89:** Mostly focused, 1-2 modules doing 2 things
- **40-69:** Mixed concerns, ~50% modules doing 2+ things
- **0-39:** Module spaghetti, no clear boundaries

**Evidence:** Module responsibility matrix (module name → [responsibilities])

---

### A6: Extractable Components

**Definition:** Can subparts be used independently? Triage heuristics extracted; embeddings pluggable; storage backends swappable.

**Scoring Criteria:**
- **90-100:** All major subsystems extractable and independently testable
- **70-89:** 2-3 subsystems extractable, 1 tightly coupled
- **40-69:** ~50% extractable, major tangling
- **0-39:** Monolithic, no clear component boundaries

**Evidence:** Extraction feasibility checklist per component

---

### A7: Testability

**Definition:** Is code structured for testing? Dependency injection, mocks, test doubles, isolated units.

**Scoring Criteria:**
- **90-100:** Full DI, all backends mockable, 80%+ test coverage
- **70-89:** Mostly DI, some hardcoded deps, 60-80% coverage
- **40-69:** Mixed DI, several hardcoded deps, 40-60% coverage
- **0-39:** No DI, difficult to mock, <40% coverage

**Evidence:** Coverage report (if available) + testability assessment per module

---

### A8: State Management

**Definition:** Is mutable state isolated and bounded? No globals, thread-safe constructs.

**Scoring Criteria:**
- **90-100:** All state encapsulated, no globals, thread-safe constructs
- **70-89:** Mostly encapsulated, 1-2 globals for config, mostly safe
- **40-69:** Mixed state ownership, some unsafe globals, threading issues possible
- **0-39:** Uncontrolled globals, race conditions visible

**Evidence:** State ownership diagram + grep results for `global`, class vars

---

### A9: Configuration Architecture

**Definition:** Is config externalized and flexible? No hardcoded values, env vars sourced.

**Scoring Criteria:**
- **90-100:** Full pydantic-settings, env vars, file-based, no hardcoded values, clear override hierarchy
- **70-89:** Config externalized, 1-2 hardcoded defaults acceptable, env vars mostly used
- **40-69:** Mixed config sources, several hardcoded values, unclear override order
- **0-39:** Hardcoded config, no external sourcing

**Evidence:** Config sources table (env var name → type → default)

---

### A10: Tool Ecosystem

**Definition:** Is the build/test/deploy tooling mature? Makefile targets, pytest, linting, CI/CD-readiness.

**Scoring Criteria:**
- **90-100:** Rich make targets (dev, test, lint, run, build), pytest fixtures, ruff configured, CI/CD ready
- **70-89:** Core targets (test, lint, run), fixtures present, CI/CD partial
- **40-69:** Minimal targets, some fixtures, linting basic
- **0-39:** Manual test/build, no tooling structure

**Evidence:** Makefile target list + linting/testing coverage

---

## GROUP 3: ŠKÁLOVATELNOST – A11 to A16

### A11: Memory Architecture

**Definition:** Can the system scale to millions of memories? Efficient search (vector indexing), batch operations, dedup strategy.

**Scoring Criteria:**
- **90-100:** HNSW indexing, batch capture, content_hash dedup, query budgeting
- **70-89:** Indexing present, batch endpoint, dedup working
- **40-69:** Linear search fallback, no batch optimization
- **0-39:** O(n) search, no scaling strategy

**Evidence:** Backend implementation review + query plan

---

### A12: Persistence Layer

**Definition:** Can data survive restarts and scale? JSONL event sourcing + backend persistence, corruption recovery.

**Scoring Criteria:**
- **90-100:** Append-only JSONL as source of truth, backend is cache, rebuild tested
- **70-89:** JSONL present, rebuild possible, one consistency gap
- **40-69:** Partial event sourcing, rebuild risky
- **0-39:** No event log, data loss on failure

**Evidence:** Persistence flow diagram + rebuild test

---

### A13: Distribution Readiness

**Definition:** Can multiple instances coexist? Per-instance isolation, no shared state, distributed-safe IDs.

**Scoring Criteria:**
- **90-100:** Per-instance collections, UUID-based IDs, idempotent ops, no shared state
- **70-89:** Per-instance design mostly present, 1-2 shared config concerns
- **40-69:** Partial instance isolation, some shared state risk
- **0-39:** Single-instance assumption baked in

**Evidence:** Instance isolation checklist

---

### A14: LLM Provider Flexibility

**Definition:** Can we swap embedding providers? Embeddings abstraction, pluggable providers, no hardcoded model names.

**Scoring Criteria:**
- **90-100:** Embedder interface, multiple impl (HashEmbedder, can add SemanticEmbedder), DI-injected
- **70-89:** Interface exists, 1 impl only but swappable, DI-injected
- **40-69:** Embedder hardcoded in 1-2 places
- **0-39:** Tight coupling to specific embedding model

**Evidence:** Embeddings abstraction + provider registration

---

### A15: Tool Sandboxing

**Definition:** Are external tool calls isolated? Tool execution context, sandboxing, timeout, resource limits.

**Scoring Criteria:**
- **90-100:** Sandboxed execution, timeouts, resource limits, error isolation
- **70-89:** Basic isolation, timeout present
- **40-69:** Minimal safeguards
- **0-39:** No sandboxing (or not applicable if no tool execution)

**Evidence:** Tool execution policy (if applicable)

---

### A16: Observability

**Definition:** Can we debug production issues? Structured logging, metrics, tracing, health checks.

**Scoring Criteria:**
- **90-100:** Structured logs (JSON), request correlation, metrics emitted, health check detailed
- **70-89:** Structured logs, partial correlation, basic metrics
- **40-69:** Unstructured logs, minimal metrics
- **0-39:** Sparse logging, no observability

**Evidence:** Logging example + metrics list

---

## GROUP 4: EVOLUCE – A17 to A19

### A17: Backlog Alignment

**Definition:** Does architecture support planned features? T1/T2 epics can be built without major refactoring.

**Scoring Criteria:**
- **90-100:** All T1/T2 epics aligned, <10% refactoring tax
- **70-89:** Most epics aligned, 10-20% refactoring tax
- **40-69:** 50% of epics face architectural blockers, 20-40% tax
- **0-39:** Major blockers for most epics, >40% refactoring needed

**Evidence:** Per-epic readiness table (epic → blockers → refactoring estimate)

---

### A18: Complexity Hotspots

**Definition:** Where do most bugs and changes occur? Functions/modules with high cyclomatic complexity or low test coverage.

**Scoring Criteria:**
- **90-100:** Max cyclomatic complexity <10, all hotspots tested, low churn
- **70-89:** Max complexity <15, hotspots mostly tested, moderate churn
- **40-69:** Max complexity 15-25, gaps in testing, high churn areas
- **0-39:** Complexity >25, untested hotspots, frequent changes

**Evidence:** Top-10 complex functions with file:line + complexity score

---

### A19: ADR Coverage

**Definition:** Are architectural decisions documented? Decisions in `fabric/decisions/` covering major choices.

**Scoring Criteria:**
- **90-100:** 8+ ADRs covering: secrets policy, ID generation, event-sourcing, injection, backends, versioning, testing, security
- **70-89:** 5-7 ADRs covering major decisions
- **40-69:** 3-4 ADRs, some key decisions undocumented
- **0-39:** <3 ADRs, most decisions undocumented

**Evidence:** ADR checklist (which decisions documented, which missing)

---

## Scoring Scale

- **🟢 EXCELLENT:** 90-100 (no action needed unless strategic)
- **🟢 GOOD:** 70-89 (no blocker, monitor)
- **🟡 NEEDS ATTENTION:** 40-69 (plan fix in next cycle)
- **🔴 CRITICAL:** 0-39 (blocks features or causes bugs, fix immediately)

---

End of dimensions.md

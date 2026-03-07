# Architectural Analysis Examples

This document provides filled-in examples from real projects to illustrate the scanning procedures.

---

## Example: LLMem Principle Scoring (A0)

From a real analysis of the LLMem memory infrastructure system.

**Principle Alignment Findings Table:**

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

**A0 Score Calculation:**
```
A0 = (78 + 82 + 88 + 71 + 75 + 92 + 85 + 89) / 8
   = 660 / 8
   = 82.5 (GOOD)
```

---

## Example: Dimension Scoring (A1-A19)

Partial table from LLMem architecture analysis:

| Dimension | Group | Score | Severity | Confidence | Key Findings | Evidence |
|-----------|-------|-------|----------|------------|--------------|----------|
| A1: Layer Isolation | KOHERENCE | 88 | 🟢 GOOD | HIGH | API routes don't access DB directly; one util import crossing layers | src/llmem/api/routes/capture.py:12 imports storage util; remediation: move to service layer |
| A2: Message Flow | KOHERENCE | 92 | 🟢 EXCELLENT | HIGH | JSONL log + idempotent upserts; event replay tested | src/llmem/storage/log_jsonl.py:1-50, tests/test_triage_and_recall.py:rebuild_test |
| A3: Pattern Consistency | KOHERENCE | 78 | 🟡 NEEDS ATTENTION | MEDIUM | CaptureService and RecallService differ in error handling; one uses structured logger, one prints to stdout | src/llmem/services/capture.py:error_handler vs recall.py:error_handler |
| A4: API Surface | KOHERENCE | 85 | 🟢 GOOD | HIGH | 5 well-defined endpoints (/capture/event, /capture/batch, /recall, /memories, /healthz); all versioned /v1/ | src/llmem/api/routes/__init__.py |
| A5: Module Cohesion | MODULARITA | 84 | 🟢 GOOD | HIGH | triage, storage, recall modules focused; minor: embeddings do 2 things (hash + storage) | src/llmem/embeddings/hash_embedder.py |
| A7: Testability | MODULARITA | 82 | 🟢 GOOD | HIGH | Full DI in services, backends mockable; 72% test coverage (good for data system) | tests/test_capture.py:mock_backend_fixture |
| A11: Memory Architecture | ŠKÁLOVATELNOST | 92 | 🟢 EXCELLENT | HIGH | HNSW indexing in Qdrant backend; batch capture endpoint; content_hash dedup; query budgeting | src/llmem/storage/backends/qdrant.py:search_hnsw, recall/pipeline.py:budget |
| A13: Distribution Readiness | ŠKÁLOVATELNOST | 76 | 🟡 NEEDS ATTENTION | HIGH | Per-instance Qdrant collections; UUID-based IDs; gap: no multi-instance routing API yet | config.py:instance_id, storage/backends/qdrant.py:collection_name |
| A16: Observability | ŠKÁLOVATELNOST | 68 | 🟡 NEEDS ATTENTION | MEDIUM | Structured JSON logs + request IDs in capture path; gap: no tracing for cross-service calls | src/llmem/services/capture.py:structured_logging |
| A19: ADR Coverage | EVOLUCE | 72 | 🟡 NEEDS ATTENTION | HIGH | 6 ADRs present (secrets, IDs, event-sourcing, injection, backends, versioning); missing: distributed instance coordination, embedding provider versioning | fabric/decisions/ |

---

## Backlog Cross-Check Example (WQ2 fix)

Assessment of LLMem T1/T2 roadmap epics against current architecture.

| Epic | T | Architectural Readiness | Blockers | Refactoring % | Notes |
|------|---|------------------------|----------|--------------|-------|
| Semantic Embeddings | T1 | 85% ready | None — embeddings interface (HashEmbedder) exists in src/llmem/embeddings/ | 15% | Just create SemanticEmbedder impl + register in server.py DI container. Can start now. |
| Distributed Recall (multi-instance) | T1 | 40% ready | No cross-instance query API; per-instance collection isolation incomplete in Qdrant backend | 40% | Must add instance routing layer + collection naming scheme in storage/backends/qdrant.py before starting feature. Blocks enterprise deployments. |
| Admin Web Dashboard | T2 | 95% ready | None — /memories and /healthz endpoints stable; routes in api/routes/memories.py | 5% | Frontend only; API contracts stable as of v1. Can start immediately. |
| GraphQL API Gateway | T2 | 60% ready | No query normalization layer; schema versioning undefined (now /v1/ routes but not schema.v1 migrations) | 35% | Add schema.v2 definitions + GraphQL-to-REST translation layer first. Medium priority. |
| PostgreSQL Backend | T1 | 50% ready | Event sourcing to JSONL incomplete; migration system missing | 45% | First finish log_jsonl.py rebuild logic; then design pg schema + migrations. High effort blocker. |
| PII/Secret Audit Trail | T1 | 92% ready | Minimal — triage/patterns.py already masks secrets; just add audit log endpoint | 8% | Add /memories/{id}/audit endpoint returning access history; minor API changes. Can start within week. |

**Readiness Definition:**
- ✅ **≥80%:** Ready to start now. Refactoring cost < 20% of feature effort.
- ⚠️ **60-79%:** Needs 1-2 day prep work. Estimated 20-40% refactoring tax.
- ❌ **<60%:** Major architectural work required. >40% refactoring. Block from sprint.

**Strategic Recommendation:** Schedule `Distributed Recall` and `PostgreSQL Backend` prep work in T0 tasks next sprint, unblocking T1 features for following sprint.

---

## Weighted Scoring Calculation Example

From LLMem overall analysis.

### Scores Table

| Dimension | Score | Weight | Product |
|-----------|-------|--------|---------|
| A0 | 82 | 2.0 | 164 |
| A1 | 88 | 2.0 | 176 |
| A2 | 92 | 1.0 | 92 |
| A3 | 78 | 1.0 | 78 |
| A4 | 85 | 1.0 | 85 |
| A5 | 84 | 1.5 | 126 |
| A6 | 80 | 1.0 | 80 |
| A7 | 82 | 1.5 | 123 |
| A8 | 86 | 1.0 | 86 |
| A9 | 82 | 1.0 | 82 |
| A10 | 85 | 1.5 | 127.5 |
| A11 | 92 | 2.0 | 184 |
| A12 | 88 | 1.5 | 132 |
| A13 | 76 | 2.0 | 152 |
| A14 | 88 | 1.0 | 88 |
| A15 | 84 | 2.0 | 168 |
| A16 | 68 | 1.5 | 102 |
| A17 | 80 | 2.0 | 160 |
| A18 | 74 | 1.0 | 74 |
| A19 | 72 | 1.0 | 72 |

### Calculation

```
Sum of products = 164 + 176 + 92 + 78 + 85 + 126 + 80 + 123 + 86 + 82
                + 127.5 + 184 + 132 + 152 + 88 + 168 + 102 + 160 + 74 + 72
                = 2,232.5

Sum of weights = 2 + 2 + 1 + 1 + 1 + 1.5 + 1 + 1.5 + 1 + 1
               + 1.5 + 2 + 1.5 + 2 + 1 + 2 + 1.5 + 2 + 1 + 1
               = 28

Overall Score = 2,232.5 / 28 = 79.8 ≈ 80

Verdict: NEEDS ATTENTION (60-79 range, rounds to upper bound)
```

---

## Cross-Dimensional Insights Example

Insights revealing hidden architectural risks from LLMem analysis.

| Finding | Dimensions Involved | Impact | Recommendation |
|---------|-------------------|--------|-----------------|
| Sparse logging in capture hot path limits debugging race conditions | A16 (Observability: 68), A7 (Testability: 82), A3 (Pattern Consistency: 78) | Hard to test async race conditions in capture pipeline; production issues opaque when concurrent requests conflict. 30% slower incident resolution. | Add structured logging to capture_event with request IDs + correlation tracking. A16 score gains 10-15 points → overall +0.5 points. |
| InMemory backend not tested at scale; Qdrant untested under load | A11 (Memory Architecture: 92), A7 (Testability: 82), A10 (Tool Ecosystem: 85) | Risk of silent data loss at >100K memories; scaling assumptions unvalidated. Qdrant stress tests missing from CI. | Add integration tests for both backends at scale (100K memories, concurrent requests). Add load tests to CI/CD. Improves A11 confidence from HIGH → CRITICAL. |
| ADRs missing for distributed instance coordination | A13 (Distribution Readiness: 76), A19 (ADR Coverage: 72) | Risk of misaligned implementation when adding multi-instance support; T1 epic "Distributed Recall" will redo design work. 10-20 hour waste. | Add ADR-021 for instance routing, collection naming, ID distribution. Document early in design phase. A19 score +5 points, A13 confidence improves. |
| Error handling patterns diverge across services (CaptureService vs RecallService) | A3 (Pattern Consistency: 78), A7 (Testability: 82), A16 (Observability: 68) | Inconsistent logging + error behavior makes cross-service debugging hard; test mocks don't catch real production errors. Team spends 20% more time on incident response. | Standardize error handler: create shared ErrorHandler base class or context manager. Unify logging + metrics emission. A3 → 88, A16 → 75. |

**Strategic Impact:** Each insight represents 5-10 points of architectural risk. Fixing top-3 insights → +3-5 overall score points → SOLID territory.

---

## Mutation Specification Examples

Real mutation specs generated from architectural findings.

### Example T0 Mutation (CRITICAL)

```markdown
# T0: Refactor CaptureService for error handling consistency

**Epic:** Architect Findings — CRITICAL: Pattern Consistency (A3: 78/100)

**Problem:** CaptureService and RecallService implement different error-handling patterns:
- CaptureService: uses structured logger + context dict
- RecallService: uses try-except with print() statements
- Tests: mock two different error paths

Results in:
- Production debugging hard (inconsistent log levels + fields)
- Tests brittle (different mocking strategies)
- New developers confused about team convention

**Solution:**
1. Create shared ErrorHandler utility in services/error_handler.py
   - `class ErrorHandler: log_and_retry(error, fn, max_attempts, backoff)`
   - Implements: structured logging + context injection + exponential backoff
   - All services use same handler

2. Refactor CaptureService.capture_event():
   - Replace inline try-except → `ErrorHandler.log_and_retry()`
   - Ensure logger.info(context={...}) on all paths

3. Refactor RecallService.recall():
   - Replace print() → structured logger calls
   - Use ErrorHandler for consistency

4. Update tests:
   - Create mock ErrorHandler for all services
   - Single test fixture + @patch.object(services, 'ErrorHandler')

**Acceptance Criteria:**
- ✅ CaptureService + RecallService use identical error-handling pattern
- ✅ All error logs include: {request_id, user_id, error_type, file:line, timestamp}
- ✅ All tests pass; zero print() statements in production code
- ✅ New developer can copy-paste error-handling pattern without questions
- ✅ A3 score ≥88 (from 78) via pattern unification

**Files Changed:**
- src/llmem/services/error_handler.py (NEW)
- src/llmem/services/capture.py (error handling refactor)
- src/llmem/services/recall.py (error handling refactor)
- tests/test_capture.py (update mocks)
- tests/test_recall.py (update mocks)

**Estimate:** T0 (1 day)
**Dependencies:** None (standalone)
**Unblocks:** A3 dimension improvement; makes A7 (Testability) easier going forward
```

### Example T1 Mutation (FEATURE ENABLING)

```markdown
# T1: Extract embeddings abstraction for semantic provider

**Epic:** Architect Findings — Enables T1 Feature: Semantic Embeddings

**Problem:** Current HashEmbedder hardcoded in CaptureService:
```python
embedder = HashEmbedder()
hash_vec = embedder.embed(observation)
```

To add SemanticEmbedder later:
- Must refactor CaptureService to accept embedder parameter
- Must define EmbedderInterface
- Must register embedders in DI container

This refactoring tax blocks the semantic feature until we prep the abstraction.

**Solution:**
1. Define EmbedderInterface in embeddings/__init__.py:
   ```python
   class EmbedderInterface:
       def embed(self, text: str) -> List[float]: ...
       def dimension(self) -> int: ...
   ```

2. Refactor HashEmbedder → implement EmbedderInterface

3. Update CaptureService.__init__() to accept `embedder: EmbedderInterface`

4. Update api/server.py DI container:
   ```python
   embedder = HashEmbedder()  # Can swap to SemanticEmbedder later
   capture_service = CaptureService(embedder=embedder)
   ```

5. Add tests with mock embedder

**Acceptance Criteria:**
- ✅ EmbedderInterface defined + documented
- ✅ HashEmbedder + CaptureService use DI pattern
- ✅ Can swap embedders in DI container without code changes
- ✅ Semantic feature now buildable (all abstractions in place)
- ✅ All tests pass
- ✅ A14 score ≥92 (from 88)

**Files Changed:**
- src/llmem/embeddings/__init__.py (add interface)
- src/llmem/embeddings/hash_embedder.py (implement interface)
- src/llmem/services/capture.py (accept embedder DI)
- src/llmem/api/server.py (DI registration)
- tests/test_capture.py (mock embedder)

**Estimate:** T1 (2-3 days)
**Dependencies:** None
**Unblocks:** T1 Feature: Semantic Embeddings (estimated 3-5 days once abstraction ready)
```

---

End of examples.md

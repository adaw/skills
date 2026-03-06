# Analyze — Příklady (K10)

> Konkrétní příklady per-task analýzy s reálnými LLMem daty.
> Čti pomocí Read toolu pro referenci při vytváření analýz.

---

## Example: Per-task Analysis for Sprint-2 Task

**File:** `{ANALYSES_ROOT}/T-TRI-02-analysis.md`

```yaml
---
schema: fabric.report.v1
kind: analysis
version: "1.0"
run_id: "analyze-2026-03-06-run42"
created_at: "2026-03-06T10:15:00Z"
task_id: "T-TRI-02"
source_target: "BACKLOG-021"
status: "READY"
effort_estimate: "M"
---

# T-TRI-02 — Analysis (Triage Heuristics Implementation)

## Goal

Implement deterministic triage heuristics that extract secrets, PII, preferences, and decisions from ObservationEvents without LLM calls. Enable capture→triage→store pipeline with gating via allow_secrets=false default on recall.

## 1. Constraints (POVINNÉ)

| ADR/Spec | Requirement | How this task satisfies it |
|----------|-------------|---------------------------|
| D0001 (secrets-policy) | Secrets stored plaintext (MVP); allow_secrets=false by default on recall | Task adds secret detection patterns; gating applied in RecallService.filter_secrets() |
| D0003 (event-sourcing) | All writes append to JSONL log before store mutation | CaptureService.capture() logs before calling triage heuristics |
| D0004 (deterministic IDs) | IDs from content_hash, no LLM | Heuristics use regex only, hash computed in models.py |

## 2. Data Flow (POVINNÉ)

ASCII diagram:
```
ObservationEvent → [Secret/PII/Pref/Decision regex] → MemoryItems → Store/JSONL
                 ↓ no match                                          ↓ error
                 [log as UNKNOWN]                                  [retry]
```

## 3. Module Dependency Table

| Module | Type | Upstream | Downstream | Risk |
|--------|------|----------|-----------|------|
| `src/llmem/triage/heuristics.py::triage_event()` | CREATE | `services/capture.py` | `models.MemoryItem` | MEDIUM |
| `src/llmem/triage/patterns.py` | CREATE | `heuristics.py` | regex compilation | LOW |
| `tests/test_triage_heuristics.py` | CREATE | pytest | — | LOW |

## 4. Entity Lifecycle

ObservationEvent → TRIAGED (heuristics extract) → STORED (upsert) → INDEXED (embedding) → RECALLED → EXPIRED

## 5. Affected Processes

Write Path (capture → triage → store) — heuristics is core to triage step. Test recommendation: `test_e2e_capture_to_triage_to_store`.

## 6. Design & Pseudocode

Implement `triage_event(event: ObservationEvent, instance_id: str) → list[MemoryItem]`:
- Step 1: Detect secret (OpenAI, GitHub, AWS, Bearer, password)
- Step 2: Detect PII (email, phone, SSN)
- Step 3: Extract preference (patterns: "prefer", "avoid", "want")
- Step 4: Extract decision (patterns: "decided", "plan to", "will")
- Step 5: Return MemoryItem[] (tier, type, content_hash, instance_id)

## 7. Alternatives

| # | Approach | Complexity | Risk | ADR | Test | Total | Pros | Cons | Chosen |
|---|----------|-----------|------|-----|------|-------|------|------|--------|
| A | Regex-only heuristics (no LLM) | 2 | 1 | 5 | 5 | 18 | Fast, deterministic, no API calls | False positives possible | ✅ |
| B | LLM-based extraction | 4 | 3 | 2 | 2 | 11 | High precision, context-aware | D0004 violation, cost, latency | — |

## 8. Test Strategy

**Unit Tests (≥3):**
- `test_secret_detection_openai_key()`
- `test_pii_detection_email()`
- `test_preference_extraction_prefer_pattern()`

**Integration Tests:**
- `test_triage_with_real_patterns()`

**E2E Tests:**
- `test_e2e_capture_to_triage()`

**Edge Cases:**
- `test_triage_edge_empty_event()`
- `test_triage_edge_unicode_normalization()`

## 9. Effort Estimate

FILES_TOUCHED=2 (heuristics.py, patterns.py); NEW_TESTS=8; MAX_COMPLEXITY=3
→ Estimate: M (4-8 hours)

## 10. Acceptance Criteria Mapping

| AC | How Satisfied |
|----|---------------|
| Capture triggers triage | CaptureService.capture() calls triage_event() |
| Secrets detected | test_secret_detection_openai_key PASS |
| No LLM calls in hot path | Zero openai/anthropic imports in heuristics.py |

## 11. Risks & Open Questions

**Risk:** Regex false positives (e.g., AWS key pattern matches random strings)
**Mitigation:** Test against 50+ real + 50+ synthetic non-matches (97% precision target)

**Open:** Should heuristics normalize unicode before matching? (DESIGN, needs clarification)
```

---

## FILLED-IN EXAMPLE: Complete Per-Task Analysis (T-STR-01)

**File:** `{ANALYSES_ROOT}/T-STR-01-analysis.md`

```md
---
schema: fabric.report.v1
kind: analysis
version: "1.0"
run_id: "analyze-2026-03-05-run-001"
created_at: "2026-03-05T10:30:00Z"
task_id: "T-STR-01"
source_target: "Target-storage-backend"
status: "READY"
effort_estimate: "M"
---

# T-STR-01 — Add In-Memory Storage Backend (Dev/Test)

## Goal

Implement a thread-safe in-memory backend for LLMem storage layer. Developers can run tests/dev without Qdrant infrastructure. Backend supports same interface as QdrantBackend (store, search, upsert, delete).

## 1. Constraints

| ADR/Spec | Requirement | How this task satisfies it |
|----------|-------------|---------------------------|
| D0001 (secrets-policy) | Storage backend must support allow_secrets filtering | InMemoryBackend receives MemoryItem (PII/secrets already masked by triage) |
| D0003 (event-sourcing) | All writes reflected in JSONL log (append-first) | InMemoryBackend not log source (log is managed by CaptureService), backend just stores |
| S0002 (recall-pipeline) | Backend must implement search(query, limit) with cosine similarity | InMemoryBackend.search() uses HashEmbedder (dev mode) + cosine distance |

## 2. Data Flow

```
Initialize (create backend) → [Memory created in dict]
                              ↓ error: none (in-process)
Store(memory) → [Validate ID] → [Insert/upsert dict] → [Success]
               ↓ invalid ID     ↓ duplicate key       ↓ returns stored count
             raise ValueError  upsert (overwrite)    response
Search(query, limit) → [Encode query] → [Cosine distance calc] → [Sort top-K] → [Return memories]
                       ↓ query empty   ↓ no matches            ↓ K=0           ↓ empty list
                     warn/skip        return []               return []        response
Delete(id) → [Find key] → [Remove] → [Success]
             ↓ not found   ↓ error   ↓ returns deleted count
           warn (idempotent) log   response
```

## 3. Module Dependency Table

| Module | Type | Upstream deps | Downstream deps | Risk |
|--------|------|---------------|-----------------|------|
| `src/llmem/storage/backends/inmemory.py::InMemoryBackend` | CREATE | `api/routes/capture.py`, `services/capture.py` (via StorageBackend interface) | `models.py` (MemoryItem), `embeddings/hash_embedder.py` (search) | LOW |
| `tests/test_inmemory_backend.py` | CREATE | n/a (test file) | test execution | LOW |

## 4. Entity Lifecycle

```
INITIALIZED (backend created with empty dict)
  → STORED (MemoryItem inserted via upsert)
  → INDEXED (embedding computed on search)
  → SEARCHED (matched against query)
  → DELETED (key removed, idempotent)
  → [cycle repeats or EXPIRED]
```

## 5. Affected Processes

**Process map reference:** Write Path (capture → triage → store) uses backend.upsert().

- **Write Path (touched)**: CaptureService calls backend.upsert() after triage
  - Contract: Store must complete within 100ms (in-memory, trivial for tests)
  - Recommendation: Add test `test_e2e_capture_to_inmemory_store` to verify Write Path end-to-end

- **Recall Path (not touched)**: RecallService calls backend.search()
  - Indirect dependency: InMemoryBackend.search() must return same interface as QdrantBackend
  - Recommendation: Add test `test_recall_with_inmemory_backend` to verify Recall Path compatibility

**Causal dependency:** InMemoryBackend enables full Write→Recall E2E tests without Qdrant.

## 6. Constraints & Pseudocode

### Design approach

In-memory dict-based backend using Python dict for O(1) upsert, O(n) search (acceptable for dev/test, ≤1000 items typical). Thread-safety via threading.Lock on all methods. Cosine similarity using HashEmbedder (deterministic, not ML-based).

### Pseudocode

```python
# src/llmem/storage/backends/inmemory.py

import threading
from typing import Optional
from llmem.models import MemoryItem
from llmem.embeddings.hash_embedder import HashEmbedder

class InMemoryBackend:
    """Thread-safe in-memory storage for testing/development."""

    def __init__(self, collection: str = "default"):
        """Initialize empty memory dict."""
        self.collection = collection
        self.memories: dict[str, MemoryItem] = {}  # id → MemoryItem
        self.lock = threading.Lock()
        self.embedder = HashEmbedder()  # Deterministic embedding

    def store(self, instance_id: str, memory: MemoryItem) -> int:
        """Store or upsert memory item. Returns 1 if stored/updated."""
        # Step 1: Validate input (fail-safe)
        if not memory.id:
            raise ValueError("MemoryItem must have id field")

        # Step 2: Acquire lock (thread-safety)
        with self.lock:
            # Step 3: Upsert (insert or overwrite)
            self.memories[memory.id] = memory
            return 1  # Always succeeds in-memory

    def search(
        self,
        instance_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryItem]:
        """Search memories by cosine similarity (deterministic embeddings)."""
        # Step 1: Validate query
        if not query or not query.strip():
            return []  # Empty query → empty result

        # Step 2: Encode query (deterministic hash embedding)
        query_embedding = self.embedder.encode(query)

        # Step 3: Compute similarity for all memories (O(n))
        with self.lock:
            scores = []
            for memory in self.memories.values():
                embedding = self.embedder.encode(memory.content)
                similarity = self._cosine_similarity(query_embedding, embedding)
                scores.append((similarity, memory))

        # Step 4: Sort and select top-K
        scores.sort(key=lambda x: x[0], reverse=True)
        results = [memory for _, memory in scores[:limit]]

        return results

    def delete(self, instance_id: str, memory_id: str) -> int:
        """Delete memory by ID. Idempotent (no error if not found)."""
        with self.lock:
            if memory_id in self.memories:
                del self.memories[memory_id]
                return 1
            return 0

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(x**2 for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
```

## 7. Alternatives

| # | Approach | Complexity | Risk | ADR Align | Test | Total | Pros | Cons | Chosen |
|---|----------|-----------|------|-----------|------|-------|------|------|--------|
| A | Dict-based with threading.Lock, cosine similarity via HashEmbedder | 2 | 1 | 5 | 5 | 4+5+5+5=19 | Simple, no external deps, deterministic, thread-safe | O(n) search slow at scale (acceptable: dev only, <1000 items) | ✅ |
| B | Use SQLite in-memory (:memory:), SQL interface | 4 | 2 | 3 | 3 | 2+4+3+3=12 | Scalable, familiar SQL | Overkill for dev, harder to test embedding similarity | — |
| C | Mock backend returning static test data | 1 | 3 | 2 | 2 | 5+3+2+2=12 | Trivial to implement | Cannot test real search logic, too simplistic | — |

**Decision:** Approach A chosen (highest TOTAL, lowest complexity, aligns ADR, deterministic).

## 8. Test Strategy

### Unit Tests (POVINNÉ ≥3)

```python
# tests/test_inmemory_backend.py

class TestInMemoryBackend:
    """Tests for InMemoryBackend — T-STR-01"""

    def test_store_happy_path(self):
        """Happy path: store memory → memory retrievable"""
        backend = InMemoryBackend()
        memory = MemoryItem(id="m1", content="Test", tier="preference")
        result = backend.store("instance-1", memory)
        assert result == 1
        assert backend.memories["m1"] == memory

    def test_search_cosine_similarity(self):
        """Search returns memories ranked by cosine similarity"""
        backend = InMemoryBackend()
        backend.store("instance-1", MemoryItem(id="m1", content="Python is great"))
        backend.store("instance-1", MemoryItem(id="m2", content="JavaScript is fun"))
        results = backend.search("instance-1", query="Python", limit=2)
        assert len(results) > 0
        assert results[0].id == "m1"  # Most similar

    def test_search_empty_query_edge(self):
        """Edge case: empty query → empty result"""
        backend = InMemoryBackend()
        backend.store("instance-1", MemoryItem(id="m1", content="Test"))
        results = backend.search("instance-1", query="", limit=5)
        assert results == []
```

### Integration Tests

```python
# tests/test_inmemory_integration.py

def test_capture_to_inmemory_store_e2e():
    """E2E: CaptureService writes to InMemoryBackend"""
    backend = InMemoryBackend()
    service = CaptureService(backend=backend)
    event = ObservationEvent(type="decision", text="Use InMemory for tests")
    response = service.capture("instance-1", event)
    assert response.memories_created >= 1
    assert len(backend.memories) > 0
```

### E2E Tests

```python
# tests/test_e2e_inmemory.py

def test_e2e_write_path_with_inmemory():
    """E2E: ObservationEvent → Capture → Triage → Store (InMemory)"""
    app = create_app(backend=InMemoryBackend())
    client = TestClient(app)
    response = client.post("/capture/event", json={"instance_id": "e2e", ...})
    assert response.status_code == 200
    backend_state = app.state.storage_backend
    assert len(backend_state.memories) > 0
```

### Edge Cases

```python
def test_concurrent_upsert_thread_safety():
    """Thread safety: concurrent upserts don't corrupt state"""
    backend = InMemoryBackend()
    threads = []
    for i in range(10):
        def worker(n):
            for j in range(100):
                memory = MemoryItem(id=f"m-{n}-{j}", content="...")
                backend.store("instance", memory)
        t = Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert len(backend.memories) == 1000  # All stored
```

## 9. Effort Estimate

**Calculation:**

FILES_TOUCHED:
1. `src/llmem/storage/backends/inmemory.py` (new file)
2. `tests/test_inmemory_backend.py` (new test file)

Total: 2 files

NEW_TESTS: 8 (3 unit + 1 integration + 1 e2e + 2 edge + 1 regression check)

MAX_COMPLEXITY: InMemoryBackend.search() has 1 loop + 1 sort, CC ≈ 4 (acceptable)

Calculation:
- FILES_TOUCHED = 2 ✓ (≤ 4 for S)
- NEW_TESTS = 8 ✓ (> 6 for S, suggests M)
- MAX_COMPLEXITY = 4 ✓ (≤ 10)

**Adjusted:** FILES_TOUCHED=2 is low, but NEW_TESTS=8 suggests M effort. Given implementation is straightforward (no complex algorithms), estimate **M (4-8 hours)** with possibility for XS/S if developer familiar with threading.

## 10. Acceptance Criteria Mapping

| AC# | Original AC | Task Satisfies By |
|-----|-------------|-------------------|
| AC1 | In-memory backend stores MemoryItem | InMemoryBackend.store(instance_id, memory) upserts to dict |
| AC2 | Search returns top-K by cosine similarity | InMemoryBackend.search(query, limit) ranks by cosine_similarity() |
| AC3 | Thread-safe for concurrent tests | All methods protected by threading.Lock |
| AC4 | Compatible with existing StorageBackend interface | Implements store, search, delete methods with same signature |
| AC5 | Deterministic (no randomness) | HashEmbedder used (deterministic), cosine similarity deterministic |

## 11. Open Questions & Risks

### Open questions
- Q: Should InMemoryBackend support persistence (save to file)? → Answer: No, dev-only, ephemeral is fine
- Q: What's acceptable search latency for tests? → Answer: <100ms for ≤1000 items (O(n) is OK)

### Known risks
- **Performance regression at scale**: If test dataset grows >10k items, O(n) search becomes slow
  → Mitigation: Add performance test `test_search_performance_100k_items()` with timeout assertion; flag if >1s
- **Embedding drift**: HashEmbedder might change in future, breaking test reproducibility
  → Mitigation: Pin embedder version + add regression test `test_search_deterministic_embedding()`
```

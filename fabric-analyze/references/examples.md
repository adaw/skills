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

## Example: Complete Per-Task Analysis (T-STR-01)

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

Initialize (create backend) → [Memory created in dict]
Store(memory) → [Validate ID] → [Insert/upsert dict] → [Success]
Search(query, limit) → [Encode query] → [Cosine distance calc] → [Sort top-K] → [Return memories]
Delete(id) → [Find key] → [Remove] → [Success]

## 3-11. (See full analysis in examples file)

Decision: Dict-based with threading.Lock, cosine via HashEmbedder. Effort: M (4-8 hours).
```

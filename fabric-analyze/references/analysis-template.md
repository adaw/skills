# Per-Task Analysis Template (KOMPLETNÍ POVINNÝ)

> Tento soubor obsahuje kompletní template pro per-task analýzy.
> Čti pomocí Read toolu při vytváření analýz pro jednotlivé tasky.
> VŠECHNY sekce jsou POVINNÉ — analýza bez kterékoli MUSÍ zůstat DRAFT.

---

## Template: `{ANALYSES_ROOT}/{task_id}-analysis.md`

```md
---
schema: fabric.report.v1
kind: analysis
version: "1.0"
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
task_id: "{task_id}"
source_target: "{target_id}"
status: "DRAFT"  # DRAFT | READY (READY → musí mít VŠECHNY sekce vyplněné)
effort_estimate: "S"  # XS | S | M | L | XL (algoritmicky vypočtené)
---

# {task_id} — Analysis

## Goal
{WHAT_SUCCESS_LOOKS_LIKE}

## 1. Constraints (POVINNÉ)

> **KONTRAKT:** Tato sekce MUSÍ existovat. Pokud je prázdná, napiš "None — task není vázán na ADR/spec."

| ADR/Spec | Requirement | How this task satisfies it |
|----------|-------------|---------------------------|
| {ADR_ID or SPEC_ID} | {Concrete requirement text} | {Jak task splňuje} |

**Example (LLMem):**
| D0001 (secrets-policy) | Secrets stored plaintext (MVP); allow_secrets=false by default on recall | Task adds `allow_secrets` flag to RecallQuery validation |
| S0003 (event-sourcing) | All writes append to JSONL log before store mutation | Task wraps CaptureService.capture() with log-first semantics |

## 2. Data Flow (POVINNÉ)

> ASCII diagram vstup → transformace → výstup s error paths. Minimálně 3-5 kroků, explicitně error handling.

```
{INPUT} → [Validace] → [Transformace] → [Persistence] → [Response]
           ↓ error      ↓ error          ↓ error         ↓ error
         400/422        500/log          retry/fail       500/partial
```

**Example (LLMem capture):**
```
ObservationEvent → [Schema validation] → [Triage] → [JSONL append] → [Store upsert] → [RecallResponse]
                  ↓ invalid              ↓ heuristic ↓ disk full    ↓ backend err    ↓ format error
                422 Unprocessable       warn/skip   retry/fallback  raise(log warn)  500 Server Error
```

## 3. Module Dependency Table (POVINNÉ)

> Tabulka: který modul, jaký typ změny, co volá upstrem, co volá downstrem, risk.

| Module | Type | Upstream deps | Downstream deps | Risk |
|--------|------|---------------|-----------------|------|
| {FULL_PATH} | MODIFY/CREATE/DELETE | {modules calling this} | {modules called by this} | LOW/MEDIUM/HIGH |

**Example (LLMem):**
| `src/llmem/services/capture.py::CaptureService.capture()` | MODIFY | `api/routes/capture.py` | `triage/heuristics.py`, `storage/backends/base.py` | MEDIUM |
| `src/llmem/triage/heuristics.py::triage_event()` | MODIFY | `services/capture.py` | `models.py` (MemoryItem) | MEDIUM |
| `src/llmem/storage/backends/qdrant.py::QdrantBackend.upsert()` | MODIFY | `services/capture.py` | — | HIGH |

## 4. Entity Lifecycle (POVINNÉ pokud task mění chování entity; jinak "N/A")

> Stavy entity a přechody: CREATED → VALIDATED → STORED → [RECALLED] → EXPIRED

**Example (LLMem MemoryItem):**
```
NEW (ObservationEvent arrives) → TRIAGED (heuristics extract) → STORED (upsert to backend)
    → INDEXED (embedding computed)
    → RECALLED (score+select+inject)
    → EXPIRED (TTL or manual purge)
```

Pokud task nemění Entity lifecycle: `N/A — task nemění entity lifecycle.`

## 5. Affected Processes (POVINNÉ)

> Cross-reference s `{WORK_ROOT}/fabric/processes/process-map.md`. Pokud soubor chybí, napiš "NOTE: process-map.md not found — skipping cross-reference".

**Procedure (deterministic bash):**
```bash
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
TOUCHED_FILES="{full_paths_from_module_table}"  # e.g., "services/capture.py triage/heuristics.py"

if [ ! -f "$PROCESS_MAP" ]; then
  echo "NOTE: process-map.md not found — skipping"
else
  for file in $TOUCHED_FILES; do
    # Find process sections containing this file
    grep -B 10 -A 10 "$file" "$PROCESS_MAP" 2>/dev/null | \
      grep -E "^##\s+|^###\s+" | head -1 || true
  done | sort -u
fi
```

**Output (v analýze):**
```
### Affected Processes
- **Write Path** (capture → triage → store): services/capture.py, triage/heuristics.py touched
  - Contract modules: CaptureService, TriageEngine, StorageBackend
  - Causal dependency: Write Path → Recall Path (new memories affect recall results)
  - Recommendation: Ensure `test_e2e_capture_to_recall` passes + cover triage edge cases

- **Recall Path**: not directly modified, but affected by Write Path changes
  - Recommendation: Add regression test `test_recall_with_new_triage_behavior`

- Process-map dependencies: None external (task is contained within LLMem core)
```

Pokud task je izolován: `N/A — task touches only utility functions, no documented process impact.`

## 6. Constraints & Pseudocode (POVINNÉ)

### Design approach
{Textový popis strategie: co, jak, proč}

### Pseudocode (konkrétní, ne generický)

> KONTRAKT: Pseudocode MUSÍ referencovat **skutečné soubory, funkce, importy z projektu**, ne generic Python.
> Každý řádek má komentář: krok, validace, error handling.

**Example (LLMem capture validation):**
```python
# src/llmem/services/capture.py::CaptureService.capture()
# Assumes: models.ObservationEvent, triage/heuristics.py, storage backend loaded

def capture(
    instance_id: str,
    event: models.ObservationEvent,
    idempotency_key: Optional[str] = None
) -> models.CaptureResponse:
    """Idempotent event capture with triage."""

    # Step 1: Validate instance_id format (D0002: per-instance isolation)
    if not instance_id or not RE_INSTANCE_ID.match(instance_id):
        raise ValueError(f"Invalid instance_id format: {instance_id}")

    # Step 2: Check idempotency (fail-open: if cache miss, continue)
    if idempotency_key:
        cached = self.idempotency_cache.get(idempotency_key)
        if cached:
            return cached

    # Step 3: Append to JSONL log (event-sourcing source of truth, D0003)
    try:
        log_entry = {
            "timestamp": event.timestamp,
            "instance_id": instance_id,
            "event": event.model_dump()
        }
        self.log_manager.append(instance_id, log_entry)
    except IOError as e:
        logger.warning(f"Log append failed for {instance_id}: {e} — continuing (fail-open)")

    # Step 4: Triage using deterministic heuristics (no LLM in hot path, D0004)
    memory_items: list[models.MemoryItem] = []
    try:
        memory_items = triage_heuristics.triage_event(event, instance_id)
    except Exception as e:
        logger.error(f"Triage failed for event {event.id}: {e} — skipping memories")
        memory_items = []  # Fail-open: don't block on triage failure

    # Step 5: Upsert to storage backend (with retry)
    stored_count = 0
    for memory in memory_items:
        try:
            self.backend.upsert(instance_id, memory)
            stored_count += 1
        except Exception as e:
            logger.warning(f"Storage upsert failed for memory {memory.id}: {e}")

    # Step 6: Return response with audit trail
    response = models.CaptureResponse(
        instance_id=instance_id,
        event_id=event.id,
        memories_created=stored_count,
        timestamp=datetime.utcnow()
    )

    # Step 7: Cache for idempotency
    if idempotency_key:
        self.idempotency_cache.set(idempotency_key, response, ttl=3600)

    return response
```

## 7. Alternatives (POVINNÉ, ≥2 alternativy)

> KONTRAKT: Pokud task nemá alespoň 2 přístupy, přepracuj task definition (problém je v scope).

**Selection algorithm with tiebreaker rules (WQ5: ENFORCEMENT):**

```
For each alternative:
  complexity_score = 1..5 (1=trivial, 5=very hard)
  risk_score = 1..5 (1=safe, 5=risky)
  adr_alignment_score = 1..5 (1=conflicts, 5=aligned)
  test_coverage_ease = 1..5 (1=hard to test, 5=trivial)

  TOTAL = (6 - complexity_score) + (6 - risk_score) + adr_alignment + test_coverage_ease

Pick alternative with highest TOTAL.

TIEBREAKER RULES (if TOTAL scores equal):
1. **Simpler wins**: Choose alternative with LOWER complexity_score
2. **Lower risk wins**: Choose alternative with LOWER risk_score
3. **Better test coverage**: Choose alternative with HIGHER test_coverage_ease
4. **KISS principle**: Fewest new abstractions / most straightforward implementation

Example: A=19, B=19 (tie) → A: complexity 2, risk 2 | B: complexity 3, risk 1
  → Pick A (lower complexity beats risk reduction per KISS)
```

| # | Approach | Complexity | Risk | ADR Align | Test Ease | Total | Pros | Cons | Chosen? |
|---|----------|-----------|------|-----------|-----------|-------|------|------|---------|
| A | {Approach text} | 1-5 | 1-5 | 1-5 | 1-5 | TOTAL | {bullet list} | {bullet list} | ✅ or — |
| B | {Approach text} | 1-5 | 1-5 | 1-5 | 1-5 | TOTAL | {bullet list} | {bullet list} | ✅ or — |

**Example (LLMem): Add `allow_secrets` flag to RecallQuery**

| # | Approach | Complexity | Risk | ADR Align | Test | Total | Pros | Cons | Chosen |
|---|----------|-----------|------|-----------|------|-------|------|------|--------|
| A | Add boolean flag `allow_secrets: bool = False` to `RecallQuery` model, gate secret filtering in `recall/pipeline.py::filter_secrets()` | 2 | 1 | 5 | 5 | 4+5+5+5=19 | Simple API, backward-compatible default, aligns D0001 (secrets policy) | Minimal, explicit in code | ✅ |
| B | Use string enum `secret_mode: Literal["block", "mask", "allow"]` with filtering logic for each mode | 3 | 2 | 4 | 3 | 3+4+4+3=14 | Future-extensible for masking mode | Over-engineered for MVP, harder to test | — |
| C | Filter secrets only if `RecallQuery.max_token_budget < threshold` (implicit heuristic) | 1 | 4 | 2 | 2 | 5+2+2+2=11 | Simplest code change | Implicit behavior is confusing, violates D0001 explicitness | — |

**Decision:** Approach A chosen (highest TOTAL + aligns ADR requirement).
|---|----------|-----------|------|-----------|-----------|-------|------|------|---------|

## 8. Test Strategy (POVINNÉ, všech 5 úrovní)

> KONTRAKT: Každá úroveň MUSÍ mít konkrétní test jména a assertions, ne "implementátor to doplní".
> Pokud úroveň není relevantní (např. E2E pro utility), napiš "N/A — {reason}".

### Unit Tests (Úroveň 1, POVINNÉ ≥3)

```python
# tests/test_capture_service.py

def test_capture_happy_path():
    """Valid ObservationEvent → stored as MemoryItem"""
    service = CaptureService(backend=InMemoryBackend())
    event = ObservationEvent(type="decision", text="Use Qdrant for recall")
    response = service.capture("instance-1", event)

    assert response.memories_created == 1
    assert response.event_id == event.id

def test_capture_idempotency_edge():
    """Duplicate idempotency_key → same response"""
    service = CaptureService(backend=InMemoryBackend())
    event = ObservationEvent(type="decision", text="...")
    key = "idempotent-key-123"

    resp1 = service.capture("instance-1", event, idempotency_key=key)
    resp2 = service.capture("instance-1", event, idempotency_key=key)

    assert resp1 == resp2  # Exact same response object/values

def test_capture_invalid_instance_id_error():
    """Invalid instance_id format → ValueError, not stored"""
    service = CaptureService(backend=InMemoryBackend())
    event = ObservationEvent(type="fact", text="...")

    with pytest.raises(ValueError, match="Invalid instance_id"):
        service.capture("", event)  # empty string
```

### Integration Tests (Úroveň 2, POVINNÉ pokud task mění API/service)

```python
# tests/test_capture_integration.py

def test_capture_api_endpoint_integration():
    """POST /capture/event → 200 + memory stored"""
    client = TestClient(app)
    payload = {
        "instance_id": "test-instance",
        "event": {"type": "decision", "text": "..."}
    }

    response = client.post("/capture/event", json=payload)
    assert response.status_code == 200
    assert response.json()["memories_created"] >= 0

def test_capture_with_real_backend():
    """CaptureService + QdrantBackend (no mocks)"""
    backend = QdrantBackend(collection="test-capture")
    service = CaptureService(backend=backend)
    event = ObservationEvent(type="decision", text="Test with Qdrant")

    response = service.capture("real-instance", event)

    # Verify stored in Qdrant
    recalled = backend.search("real-instance", query="Test", limit=1)
    assert len(recalled) >= 1
```

### E2E Tests (Úroveň 3, POVINNÉ pokud user-facing feature)

```python
# tests/test_e2e_capture_to_recall.py

def test_e2e_capture_event_then_recall():
    """End-to-end: capture observation → recall it"""
    app = create_app(backend=InMemoryBackend())
    client = TestClient(app)

    # 1. Capture decision
    capture_resp = client.post(
        "/capture/event",
        json={
            "instance_id": "e2e-test",
            "event": {"type": "decision", "text": "Use deterministic IDs"}
        }
    )
    assert capture_resp.status_code == 200

    # 2. Recall memories
    recall_resp = client.post(
        "/recall",
        json={
            "instance_id": "e2e-test",
            "query": "IDs",
            "max_memories": 5
        }
    )
    assert recall_resp.status_code == 200
    memories = recall_resp.json()["memories"]
    assert any("deterministic" in m["content"] for m in memories)
```

### Edge Case Tests (Úroveň 4, POVINNÉ ≥2)

```python
# tests/test_capture_edge_cases.py

def test_capture_concurrent_writes():
    """Multiple threads writing to same instance → no corruption"""
    service = CaptureService(backend=InMemoryBackend())
    instance_id = "concurrent-test"

    def writer(n):
        for i in range(10):
            event = ObservationEvent(type="fact", text=f"Event {n}-{i}")
            service.capture(instance_id, event)

    threads = [Thread(target=writer, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Verify all 50 events stored
    memories = service.backend.get_all(instance_id)
    assert len(memories) == 50

def test_capture_disk_full_fail_open():
    """Storage backend disk full → log warning, don't crash"""
    backend = Mock(spec=StorageBackend)
    backend.upsert.side_effect = IOError("No space left on device")

    service = CaptureService(backend=backend)
    event = ObservationEvent(type="decision", text="Should not crash")

    response = service.capture("instance-1", event)  # Should not raise
    assert response.memories_created == 0  # But nothing stored
    # Verify warning logged (check logger.warning called)
```

### Regression Tests (Úroveň 5, POVINNÉ pokud bugfix)

> N/A — task není bugfix (nebo uveď test regression pro konkrétní bug)

```python
# Pokud je bugfix:
def test_capture_regression_issue_102():
    """Issue #102: secrets leaked in non-secret items — now fixed"""
    service = CaptureService(backend=InMemoryBackend())
    event = ObservationEvent(
        type="fact",
        text="My AWS key is AKIA1234567890ABCD"  # Secret in fact
    )

    response = service.capture("instance-1", event)
    stored = service.backend.get_all("instance-1")[0]

    assert "AKIA" not in stored.content  # Secret masked, not leaked
```

### Test Evidence Artifacts

Specify what to capture in reports:
- Coverage report: `coverage html` → save `/htmlcov/index.html`
- Test output: `pytest -v --tb=short` → save output log
- Timing: `pytest --durations=10` → identify slow tests

## 9. Effort Estimate (ALGORITMICKÉ, ne heuristika)

> **KONTRAKT:** Effort musí být vypočten podle algoritmu, ne intuicí. Zapiš výpočet do analýzy.

**Algoritmus:**

```
1. Count FILES_TOUCHED from module dependency table
2. Count NEW_TESTS from Test Strategy (all 5 levels combined)
3. Find MAX_CYCLOMATIC_COMPLEXITY of modified functions (rough estimate)

Then:
  if FILES_TOUCHED ≤ 2 AND NEW_TESTS ≤ 3 AND MAX_COMPLEXITY ≤ 5:
    EFFORT = XS (< 2 hours)
  elif FILES_TOUCHED ≤ 4 AND NEW_TESTS ≤ 6 AND MAX_COMPLEXITY ≤ 10:
    EFFORT = S (2-4 hours)
  elif FILES_TOUCHED ≤ 8 AND NEW_TESTS ≤ 12 AND MAX_COMPLEXITY ≤ 15:
    EFFORT = M (4-8 hours)
  elif FILES_TOUCHED ≤ 15 AND NEW_TESTS ≤ 20 AND MAX_COMPLEXITY ≤ 25:
    EFFORT = L (8-16 hours)
  else:
    EFFORT = XL (>16 hours) → CONSIDER SPLITTING TASK
```

**Example calculation (LLMem):**

```
Task: Add allow_secrets flag to RecallQuery

FILES_TOUCHED:
  1. src/llmem/models.py (RecallQuery — add field)
  2. src/llmem/recall/pipeline.py (filter_secrets() — check flag)
  Total: 2 files

NEW_TESTS (from Test Strategy above):
  Unit: test_recall_respects_allow_secrets_true (1)
         test_recall_allow_secrets_false_masks_secret (1)
         test_recall_invalid_query_error (1)
  Integration: test_recall_api_with_secrets_flag (1)
  E2E: test_e2e_capture_secret_recall_gated (1)
  Edge: test_recall_concurrent_flag_changes (1)
  Total: 6 tests

MAX_COMPLEXITY: RecallQuery is simple dataclass (1), filter_secrets() has 1 if statement (2)
  Max: 2

Calculation:
  FILES_TOUCHED = 2 ✓ (≤ 4)
  NEW_TESTS = 6 ✓ (≤ 6)
  MAX_COMPLEXITY = 2 ✓ (≤ 10)

  → EFFORT = S (2-4 hours)
```

## 10. Acceptance Criteria Mapping (POVINNÉ)

| AC# | Original AC | Task Satisfies By |
|-----|-------------|-------------------|

## 11. Open Questions & Risks (POVINNÉ)

### Open questions
- {QUESTION} → {OWNER}

### Known risks
- **{RISK_TITLE}**: {description} → Mitigation: {how to reduce}
```

---

## Contract Enforcement Script

Analýza NESMÍ být označena `READY` pokud chybí KTERÁKOLI povinná sekce:

```bash
#!/bin/bash
# MANDATORY CONTRACT VALIDATION — blocking, not warnings

ANALYSIS_FILE="{ANALYSES_ROOT}/{task_id}-analysis.md"
TASK_ID=$(grep "^task_id:" "$ANALYSIS_FILE" | cut -d'"' -f2)
MISSING=""

echo "=== VALIDATING ANALYSIS CONTRACT FOR $TASK_ID ==="

grep -q "^## 1. Constraints" "$ANALYSIS_FILE" || MISSING="${MISSING} [1.Constraints]"
grep -q "^## 2. Data Flow" "$ANALYSIS_FILE" || MISSING="${MISSING} [2.DataFlow]"
grep -q "^## 3. Module Dependency Table" "$ANALYSIS_FILE" || MISSING="${MISSING} [3.ModuleDeps]"
grep -q "^## 4. Entity Lifecycle" "$ANALYSIS_FILE" || MISSING="${MISSING} [4.EntityLifecycle]"
grep -q "^## 5. Affected Processes" "$ANALYSIS_FILE" || MISSING="${MISSING} [5.AffectedProcesses]"
grep -q "^## 6. Constraints & Pseudocode" "$ANALYSIS_FILE" || MISSING="${MISSING} [6.Pseudocode]"

grep -q "^## 7. Alternatives" "$ANALYSIS_FILE" || {
  if grep -q "effort_estimate: \"XS\"" "$ANALYSIS_FILE" || grep -q "effort_estimate: \"S\"" "$ANALYSIS_FILE"; then
    echo "WARN: Alternatives missing, but task is XS/S (acceptable)"
  else
    MISSING="${MISSING} [7.Alternatives]"
  fi
}

grep -q "^## 8. Test Strategy" "$ANALYSIS_FILE" || MISSING="${MISSING} [8.TestStrategy]"
grep -q "^## 9. Effort Estimate" "$ANALYSIS_FILE" || MISSING="${MISSING} [9.EffortEstimate]"
grep -q "^## 10. Acceptance Criteria Mapping" "$ANALYSIS_FILE" || MISSING="${MISSING} [10.ACMapping]"
grep -q "^## 11. Open Questions & Risks" "$ANALYSIS_FILE" || MISSING="${MISSING} [11.Risks]"

if [ -n "$MISSING" ]; then
  echo "❌ FAIL: Analysis incomplete. Missing sections:$MISSING"
  echo "→ Set status = DRAFT, keep task in DESIGN state"
  exit 1
else
  echo "✅ PASS: Analysis complete. All mandatory sections present."
  echo "→ Safe to set status = READY"
  exit 0
fi
```

**Výsledek:**
- ✅ PASS → `status: READY`, task připraven pro implementaci
- ❌ FAIL → `status: DRAFT`, implementátor task přeskočí

---

## Status Synchronization

Kdykoli změníš status tasku (DESIGN → READY nebo naopak), aktualizuj **všechna tři místa**:
1. Per-task analýza (`{ANALYSES_ROOT}/{task_id}-analysis.md`, frontmatter `status:`)
2. Sprint plan Task Queue (`sprints/sprint-{N}.md`, sloupec `Status`)
3. Backlog item (`backlog/{task_id}.md`, frontmatter `status:`)

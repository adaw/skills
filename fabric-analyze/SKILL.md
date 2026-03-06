---
name: fabric-analyze
description: "Convert Sprint Targets into Task Queue + per-task analyses with explicit governance constraints."
---

# fabric-analyze

> **Úkol:** Převést `Sprint Targets` → **Task Queue** tak, aby implementace byla deterministická, kontrolovatelná a v souladu s governance (decisions/specs).

## Cíl

- Naplnit `Task Queue` tak, aby na něj šlo navázat `fabric-implement` bez dodatečných otázek.
- Pro každý task vytvořit krátkou **per-task analýzu** v `{ANALYSES_ROOT}/`.
- Explicitně uvést **Constraints** (které ADR/spec ovlivňují task).
- Když chybí informace → vytvořit intake item (clarification / blocker) místo vymýšlení.

## K10 Fix: Per-task Analysis Example with Real LLMem Data

Here is a concrete example of a completed per-task analysis for a Sprint-2 task:

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

## Downstream Contract (WQ7)

**fabric-analyze** contracts with **downstream skills:**

| Skill | Contract | Enforcement |
|-------|----------|------------|
| **fabric-implement** | Per-task analysis MUST have §1-§11 (see contract enforcement). Task status = READY only if complete. | Implement reads analysis; DRAFT analysis = task skipped, READY = proceeds |
| **fabric-review** | Task Queue ordered by dependencies. No circular deps. Cross-task analysis documents execution order. | Review can cherry-pick tasks if analysis explicitly marks them independent |
| **fabric-sprint** | Sprint Targets fully decomposed into Task Queue. Effort estimates algorithmically sound. | Sprint planner uses estimates for capacity; miscalculated estimates = sprint overrun |
| **backlog index** | Backlog items linked to analysis (field: `analysis_report:` path). Task status synchronized across 3 places. | Loop verifies backlog.md ↔ backlog/{id}.md ↔ analysis{id}.md consistency |

**Errors that break contract (CRITICAL):**
- ❌ Analysis incomplete (missing §1-§11) but status=READY → implement fails blindly
- ❌ Task Queue contains circular dependencies → loop cannot order tasks, sprint stalls
- ❌ Analysis contradicts backlog AC → inconsistent requirements, rework wasted
- ❌ Effort estimate off by >2x → sprint fails velocity predictions

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/sprints/sprint-{N}.md`
- `{WORK_ROOT}/backlog.md` + `{WORK_ROOT}/backlog/{id}.md` (všechny targety)
- `{WORK_ROOT}/decisions/INDEX.md` + `{WORK_ROOT}/decisions/*.md`
- `{WORK_ROOT}/specs/INDEX.md` + `{WORK_ROOT}/specs/*.md`
- `{CODE_ROOT}/` + `{TEST_ROOT}/` + `{DOCS_ROOT}/`

## Výstupy

- Aktualizovaný `{WORK_ROOT}/sprints/sprint-{N}.md` (vyplněný `Task Queue`)
- `{ANALYSES_ROOT}/{task_id}-analysis.md` pro každý task v Task Queue
- 0..N intake items v `{WORK_ROOT}/intake/` (clarifications / blockers)
- `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md` (souhrn)

## Preconditions

```bash
# --- Precondition 1: Config existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: State existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 3: Sprint plan existuje ---
CURRENT_SPRINT=$(grep '^sprint:' "{WORK_ROOT}/state.md" 2>/dev/null | awk '{print $2}')
if [ -z "$CURRENT_SPRINT" ]; then
  echo "STOP: Current sprint not found in state.md"
  exit 1
fi

SPRINT_FILE="{WORK_ROOT}/sprints/sprint-${CURRENT_SPRINT}.md"
if [ ! -f "$SPRINT_FILE" ]; then
  echo "STOP: Sprint plan $SPRINT_FILE not found — run fabric-sprint first"
  exit 1
fi

# --- Precondition 4: Backlog index existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "STOP: {WORK_ROOT}/backlog.md not found — run fabric-intake first"
  exit 1
fi

# --- Precondition 5: Governance resources exist ---
if [ ! -f "{WORK_ROOT}/decisions/INDEX.md" ]; then
  echo "WARN: decisions/INDEX.md not found — governance constraints unavailable"
fi
if [ ! -f "{WORK_ROOT}/specs/INDEX.md" ]; then
  echo "WARN: specs/INDEX.md not found — specs constraints unavailable"
fi
```

**Dependency chain:** `fabric-sprint` → [fabric-analyze] → `fabric-implement`

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

## Kanonická pravidla

1. **Task Queue je autoritativní** pro implementaci. Implement/test/review se řídí pouze `Task Queue`.
2. **Každá per-task analýza musí mít sekci `Constraints`** (i kdyby byla `None`).
3. **Do Task Queue patří pouze:** `Task | Bug | Chore | Spike`.
4. `Epic/Story` target se vždy rozpadne na konkrétní Tasks.
5. Když není dost specifikace → vytvoř intake item (clarification) a nech task status `DESIGN`.
6. Když je specifikace dostatečná → nastav task status `READY`.

## Formát per-task analýzy (KOMPLETNÍ POVINNÝ TEMPLATE)

Ulož do `{ANALYSES_ROOT}/{task_id}-analysis.md`. **VŠECHNY následující sekce jsou POVINNÉ** — analýza bez kterékoli z nich MUSÍ zůstat ve stavu `DRAFT` a task se NESMÍ značit jako `READY`.

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
effort_estimate: "S"  # XS | S | M | L | XL (algoritmicky vypočtené, viz §7.4.6)
---

# {task_id} — Analysis

## Goal
{WHAT_SUCCESS_LOOKS_LIKE}

## 1. Constraints (POVINNÉ)

> **KONTRAKT:** Tato sekce MUSÍ existovat. Pokud je prázdná, napiš "None — task není vázán na ADR/spec."
> Format: `| ADR/Spec | Requirement | How this task satisfies it |`

| ADR/Spec | Requirement | How this task satisfies it |
|----------|-------------|---------------------------|
| {ADR_ID or SPEC_ID} | {Concrete requirement text} | {Jak task splňuje} |
| — | — | — |

**Example (LLMem):**
| D0001 (secrets-policy) | Secrets stored plaintext (MVP); allow_secrets=false by default on recall | Task adds `allow_secrets` flag to RecallQuery validation |
| S0003 (event-sourcing) | All writes append to JSONL log before store mutation | Task wraps CaptureService.capture() with log-first semantics |

## 2. Data Flow (POVINNÉ)

> ASCII diagram vstup → transformace → výstup s error paths. Minimálně 3-5 kroků, explicitně error handling.

**Diagram:**
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

```
CREATED → VALIDATED → STORED → [RECALLED] → EXPIRED
```

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
3. **Better test coverage**: Choose alternative with HIGHER test_coverage_ease (easier to validate)
4. **KISS principle**: Fewest new abstractions / most straightforward implementation

Example: A=19, B=19 (tie) → A: complexity 2, risk 2 | B: complexity 3, risk 1
  → Pick A (lower complexity beats risk reduction per KISS)
```

| # | Approach | Complexity | Risk | ADR Align | Test Ease | Total | Pros | Cons | Chosen? |
|---|----------|-----------|------|-----------|-----------|-------|------|------|---------|
| A | {Approach text} | 1-5 | 1-5 | 1-5 | 1-5 | TOTAL | {bullet list} | {bullet list} | ✅ or — |
| B | {Approach text} | 1-5 | 1-5 | 1-5 | 1-5 | TOTAL | {bullet list} | {bullet list} | ✅ or — |
| C | {Approach text (if applicable)} | 1-5 | 1-5 | 1-5 | 1-5 | TOTAL | {bullet list} | {bullet list} | ✅ or — |

**Example (LLMem): Add `allow_secrets` flag to RecallQuery**

| # | Approach | Complexity | Risk | ADR Align | Test | Total | Pros | Cons | Chosen |
|---|----------|-----------|------|-----------|------|-------|------|------|--------|
| A | Add boolean flag `allow_secrets: bool = False` to `RecallQuery` model, gate secret filtering in `recall/pipeline.py::filter_secrets()` | 2 | 1 | 5 | 5 | 4+5+5+5=19 | Simple API, backward-compatible default, aligns D0001 (secrets policy) | Minimal, explicit in code | ✅ |
| B | Use string enum `secret_mode: Literal["block", "mask", "allow"]` with filtering logic for each mode | 3 | 2 | 4 | 3 | 3+4+4+3=14 | Future-extensible for masking mode | Over-engineered for MVP, harder to test | — |
| C | Filter secrets only if `RecallQuery.max_token_budget < threshold` (implicit heuristic) | 1 | 4 | 2 | 2 | 5+2+2+2=11 | Simplest code change | Implicit behavior is confusing, violates D0001 explicitness | — |

**Decision:** Approach A chosen (highest TOTAL + aligns ADR requirement).

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

## FILLED-IN EXAMPLE: Complete Per-Task Analysis (WQ2)

**File: `{ANALYSES_ROOT}/T-STR-01-analysis.md`**

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

        # Step 2: Acquire lock (thread-safety, §3 table risk=LOW since in-process)
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
        """Search memories by cosine similarity (deteministic embeddings)."""
        # Step 1: Validate query
        if not query or not query.strip():
            return []  # Empty query → empty result

        # Step 2: Encode query (deterministic hash embedding)
        query_embedding = self.embedder.encode(query)  # Returns embedding vector

        # Step 3: Compute similarity for all memories (O(n))
        with self.lock:
            scores = []
            for memory in self.memories.values():
                embedding = self.embedder.encode(memory.content)
                # Cosine similarity: dot(A, B) / (||A|| * ||B||)
                similarity = self._cosine_similarity(query_embedding, embedding)
                scores.append((similarity, memory))

        # Step 4: Sort and select top-K
        scores.sort(key=lambda x: x[0], reverse=True)
        results = [memory for _, memory in scores[:limit]]

        # Step 5: Return results (empty list if no matches)
        return results

    def delete(self, instance_id: str, memory_id: str) -> int:
        """Delete memory by ID. Idempotent (no error if not found)."""
        # Step 1: Acquire lock
        with self.lock:
            # Step 2: Remove if exists (idempotent)
            if memory_id in self.memories:
                del self.memories[memory_id]
                return 1
            # Step 3: Not found (idempotent, just return 0)
            return 0

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        # Dot product
        dot = sum(x * y for x, y in zip(a, b))
        # Norms
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(x**2 for x in b) ** 0.5
        # Similarity
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
    # Capture
    response = client.post("/capture/event", json={"instance_id": "e2e", ...})
    assert response.status_code == 200
    # Verify stored
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

## 10. Acceptance Criteria Mapping (POVINNÉ)

> Map each AC from backlog item to how task satisfies it.

| AC# | Original AC | Task Satisfies By |
|-----|-------------|-------------------|
| AC1 | {Requirement} | {Konkrétní implementace} |
| AC2 | {Requirement} | {Konkrétní implementace} |

**Example:**
| AC1 | Allow callers to opt-out of secret recall | RecallQuery.allow_secrets: bool = False (default) gates filtering |
| AC2 | Non-secret items MUST never leak secrets | triage masks PII in non-secret items + recall filters by flag |

## 11. Open Questions & Risks (POVINNÉ)

```markdown
### Open questions
- {QUESTION_1} → {OWNER}
- {QUESTION_2} → {OWNER}

### Known risks
- **{RISK_TITLE}**: {description} → Mitigation: {how to reduce}
```

**Example:**
```
### Open questions
- Q: How to handle mixed instance_ids in batch capture? → Ask product lead
- Q: Should triage reject events with no content? → Check existing behavior first

### Known risks
- **Race condition on idempotency cache**: Concurrent requests with same key might bypass check
  → Mitigation: Use atomic compare-and-swap in cache.set(), add test_capture_concurrent_idempotency
- **JSONL log append performance**: Large events might slow down log writes
  → Mitigation: Benchmark with 10MB events, consider async append
```
```

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="planning"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-analyze. Expected: $EXPECTED_PHASES"
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
# validate_path "$TASK_FILE"
# validate_path "$ANALYSIS_FILE"
```

### 0) Deterministická příprava (rychlá)

```bash
python skills/fabric-init/tools/fabric.py backlog-index
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null
if [ $? -ne 0 ]; then
  echo "WARN: governance-index failed — continuing without governance data"
fi
```

> Tohlo je strojová práce: srovná indexy a odhalí strukturální drift.

**Governance index error handling (P2 fix):** The governance-index call is wrapped with error suppression and continuation logic. If the governance index fails (e.g., missing ADR/spec files), the analysis continues without hard blocking, and a warning is logged for manual review.

### 1) Načti sprint plan a targety

- Najdi aktivní sprint v `state.md` (`state.active_sprint`) a otevři `sprints/sprint-{N}.md`.
- Z tabulky `Sprint Targets` vezmi seznam targetů.
- Pokud `Task Queue` už existuje a není prázdná:
  - doplň jen chybějící tasks
  - nemaž ručně vložené změny, pokud nejsou zjevně špatně.

### 2) Pro každý target vytvoř návrh tasks

**Co:** Rozložit targety na implementovatelné tasky s jasným scope a testovatelností.

**K2 Fix: Loop termination with numeric validation**
```bash
# Counter initialization with MAX from config
MAX_ANALYSIS_TASKS=${MAX_ANALYSIS_TASKS:-200}
ANALYSIS_COUNTER=0

# Validate MAX_ANALYSIS_TASKS is numeric (K2 tight validation)
if ! echo "$MAX_ANALYSIS_TASKS" | grep -qE '^[0-9]+$'; then
  MAX_ANALYSIS_TASKS=200
  echo "WARN: MAX_ANALYSIS_TASKS not numeric, reset to default (200)"
fi
```

**Size guard (P2 fix): Skip oversized backlog items to prevent parsing performance issues:**
```bash
# Per-target processing loop with counter guard
for target in $TARGETS; do
  ANALYSIS_COUNTER=$((ANALYSIS_COUNTER + 1))

  # Numeric validation of counter (K2 strict check)
  if ! echo "$ANALYSIS_COUNTER" | grep -qE '^[0-9]+$'; then
    ANALYSIS_COUNTER=0
    echo "WARN: ANALYSIS_COUNTER corrupted, reset to 0"
  fi

  if [ "$ANALYSIS_COUNTER" -gt "$MAX_ANALYSIS_TASKS" ]; then
    echo "WARN: max analysis iterations ($ANALYSIS_COUNTER) reached — stopping"
    break
  fi

  # Size guard: skip oversized backlog items (P2 fix)
  FILE_SIZE=$(wc -c < "{WORK_ROOT}/backlog/${target}.md" 2>/dev/null || echo 0)
  MAX_SIZE=102400  # 100KB
  if [ "$FILE_SIZE" -gt "$MAX_SIZE" ]; then
    echo "WARN: backlog item ${target}.md exceeds ${MAX_SIZE} bytes — skipping"
    continue
  fi
done
```

Pro každý target:

1) Otevři backlog item `{WORK_ROOT}/backlog/{target}.md`
2) Urči typ (Epic/Story/Task/Bug/Chore/Spike)
3) Pokud Epic/Story:
   - rozpadni na 3–12 tasks (jasně pojmenované, testovatelné)
4) Pokud Task/Bug/Chore/Spike:
   - vytvoř 1 task (můžeš ho upřesnit na implementovatelný)

Každý task musí mít:
- `ID` (např. `{target}-T01`, nebo nově `TASK-XXXX` — buď konzistentní v rámci sprintu)
- `Type` (Task/Bug/Chore/Spike)
- `Status` (DESIGN/READY)
- `Description` (1–2 věty max)
- `Estimate` (S/M/L; heuristika)

**Effort sanity check (POVINNÉ):**
Pokud analýza odhalí, že skutečný scope neodpovídá effort odhadu:
```bash
# Effort sanity: pokud task odhadnutý jako S ale dotýká se ≥5 souborů nebo ≥3 modulů → WARN
TOUCHED_FILES=$(echo "{files_list}" | wc -w)
if [ "$EFFORT" = "S" ] && [ "$TOUCHED_FILES" -ge 5 ]; then
  echo "WARN: task $TASK_ID estimated S but touches $TOUCHED_FILES files — consider M or L"
fi
```
Pokud effort mismatch: uprav odhad v Task Queue a backlog itemu + zapiš důvod do analýzy.

**Anti-patterns (zakázáno):**
- ❌ Vágní task popis ("implementuj feature X" — musí být konkrétní: jaké soubory, jaký endpoint, jaký model)
- ❌ Task bez testovatelných AC (každý task musí mít alespoň 1 ověřitelné akceptační kritérium)
- ❌ Estimate bez zdůvodnění (L protože "je to složité" — uveď proč: nový model + API + testy)
- ❌ Epic/Story v Task Queue bez rozkladu na Tasks

### 2.1) Procesní analýza per task (ABSOLUTNĚ POVINNÉ, ne opcional)

> **KONTRAKT:** KAŽDÝ task MUSÍ mít kompletní procesní analýzu se VŠEMI čtyřmi komponenty:
> Data Flow + Module Dependency Table + Entity Lifecycle + Affected Processes.
> Pokud kterákoli z nich chybí nebo je incomplete, analýza → DRAFT, task → DESIGN.

Pro KAŽDÝ task PŘED zápisem do analýzy proveď KOMPLETNÍ procesní rozbor (ne dílčí):

**A) Datový tok (§2.1A, POVINNÉ)**

Identifikuj jak data tečou systémem pro tento task. ASCII diagram s minimálně 3-5 kroky a error handling.

Zapiš do analýzy sekci `## 2. Data Flow (POVINNÉ)` s:
- Vstup → Transformace → Výstup (v sekvenci)
- Error handling pro každý krok (jaký HTTP status / log / retry)
- Konkrétní příklad z LLMem nebo projektu (ne generický)

**Povinný format:**
```
{INPUT} → [Krok1] → [Krok2] → [Krok3] → [OUTPUT]
          ↓ err      ↓ err      ↓ err      ↓ err
        status1    status2    status3    status4
```

Anti-pattern ❌: Vynechavat error paths ("je to happy path"). **Každý diagram MUSÍ mít error branch.**

**B) Dotčené moduly a závislosti (§2.1B, POVINNÉ)**

SYSTEMATICKY (ne vágní "files likely touched"). Vytvoř tabulku se VŠEMI:
- Modul (full path)
- Typ změny (MODIFY/CREATE/DELETE)
- Upstream dependencies (co to volá)
- Downstream dependencies (co to volá)
- Risk (LOW/MEDIUM/HIGH)

Zapiš do analýzy sekci `## 3. Module Dependency Table (POVINNÉ)`.

**Povinný format:**
```markdown
| Module | Type | Upstream deps | Downstream deps | Risk |
|--------|------|---------------|-----------------|------|
| src/llmem/{path} | MODIFY/CREATE | {modules} | {modules} | LOW/MEDIUM/HIGH |
```

Anti-pattern ❌: Vágní seznam ("api/, triage/"). **Musí být konkrétní cesta + typ + deps.**

**C) Message/Entity lifecycle (§2.1C, POVINNÉ pokud task mění entity; jinak "N/A")**

Identifikuj stavy entity a přechody pokud task mění behavior.

Zapiš do analýzy sekci `## 4. Entity Lifecycle (POVINNÉ pokud task mění chování entity; jinak "N/A")`.

**Povinný format:**
```
STATE_A → STATE_B → STATE_C → ...
```

Pokud task nemění lifecycle: `N/A — task nemění entity lifecycle.` (a to je ok).

Anti-pattern ❌: Ignorovat lifecycle když task mění entity behavior. **Musí se zmapovat.**

**D) Process-map cross-reference & Affected Processes (§2.1D, POVINNÉ)**

DETERMINISTIC BASH: Pro KAŽDÝ task (bez výjimky) proveď procesní mapování:

```bash
#!/bin/bash
# Deterministic cross-reference: which documented processes does this task affect?

TASK_ID="{task_id}"
TOUCHED_FILES="{files_from_module_table}"  # space-separated: "src/llmem/services/capture.py src/llmem/triage/heuristics.py"
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"

# 1. Check if process-map exists
if [ ! -f "$PROCESS_MAP" ]; then
  echo "NOTE: process-map.md not found at $PROCESS_MAP"
  echo "→ Skipping process cross-reference. Update process-map.md in repo to enable this check."
  exit 0
fi

# 2. For each touched file, find affected processes
echo "=== AFFECTED PROCESSES FOR $TASK_ID ==="
AFFECTED=""
for file in $TOUCHED_FILES; do
  # Search process-map for this file
  MATCHES=$(grep -n "$file" "$PROCESS_MAP" 2>/dev/null | cut -d: -f1 || true)
  if [ -n "$MATCHES" ]; then
    # Find the process section (## or ###) containing this line
    while IFS= read -r line_num; do
      # Backtrack to find process header
      awk "NR < $line_num && /^##\s+|^###\s+/ {last=NR; header=\$0} \
           NR == $line_num {print header}" "$PROCESS_MAP" || true
    done <<< "$MATCHES"
  fi
done | sort -u > /tmp/affected_processes.txt

if [ -s /tmp/affected_processes.txt ]; then
  echo "Affected processes:"
  cat /tmp/affected_processes.txt
  # For each affected process, extract contract_modules and dependencies
  while IFS= read -r process; do
    echo ""
    echo "  Process: $process"
    # Find contract modules and dependencies
    grep -A 20 "$process" "$PROCESS_MAP" | grep -E "contract_modules|dependencies|Risk" | head -5 || true
  done < /tmp/affected_processes.txt
else
  echo "No documented processes found for touched files."
  echo "→ Task appears to be isolated (or process-map needs update)."
fi
```

Zapiš do analýzy sekci `## 5. Affected Processes (POVINNÉ)` s:
- Seznamem dotčených procesů (nebo "NOTE: process-map.md not found" / "N/A — isolated task")
- Contract modules z process-map
- Kauzální závislosti (Write Path → Recall Path apod.)
- Test coverage recommendation

Anti-patterns:
- ❌ Přeskočit procesní mapování ("je to jednoduchý task") — i jednoduchý task se musí zmapovat
- ❌ "NOTE: process-map.md not found" bez vysvětlení — musíš psát explicitně: why it's missing, impact
- ✅ ASCII diagram VŽDY, i kdyby měl jen 3 boxy
- ✅ Fail-open: chybí process-map → pokračuj, zaznamenáš do analýzy "NOTE: process-map.md missing"

### 3) Governance constraints per task

- Z `decisions/INDEX.md` a `specs/INDEX.md` vyber relevantní kontrakty.
- Pokud backlog item explicitně odkazuje na ADR/SPEC, použij je.
- Pokud je konflikt:
  - nevymýšlej workaround
  - vytvoř intake item `intake/governance-clarification-{task_id}.md`
  - v tasku nastav `Status = DESIGN`

### 4) Zapiš per-task analýzy (s POVINNÝM CONTRACT ENFORCEMENT)

**Co:** Pro každý task vytvořit kompletní analýzu s VŠEMI povinými sekcemi.

- Pro každý task vytvoř `{ANALYSES_ROOT}/{task_id}-analysis.md` podle template výše (§2.1).
- Pokud má task otevřené otázky → ponech `status: DRAFT` a `Task Queue Status = DESIGN`.
- Pokud je vše jasné A analýza má VŠECHNY povinné sekce → `status: READY` a `Task Queue Status = READY`.

**Contract enforcement (MUSÍ BLOKOVAT, ne jen warning):**

Analýza NESMÍ být označena `READY` pokud chybí KTERÁKOLI z následujících sekcí. Pokud chybí, **FAIL task** (vrat do DESIGN):

```bash
#!/bin/bash
# MANDATORY CONTRACT VALIDATION — blocking, not warnings

ANALYSIS_FILE="{ANALYSES_ROOT}/{task_id}-analysis.md"
TASK_ID=$(grep "^task_id:" "$ANALYSIS_FILE" | cut -d'"' -f2)
MISSING=""

# Check ALL mandatory sections (from §2.1 template)
echo "=== VALIDATING ANALYSIS CONTRACT FOR $TASK_ID ==="

# 1. Constraints (§2.1 section 1) — FAIL if missing
grep -q "^## 1. Constraints" "$ANALYSIS_FILE" || MISSING="${MISSING} [1.Constraints]"

# 2. Data Flow (§2.1 section 2) — FAIL if missing
grep -q "^## 2. Data Flow" "$ANALYSIS_FILE" || MISSING="${MISSING} [2.DataFlow]"

# 3. Module Dependency Table (§2.1 section 3) — FAIL if missing
grep -q "^## 3. Module Dependency Table" "$ANALYSIS_FILE" || MISSING="${MISSING} [3.ModuleDeps]"

# 4. Entity Lifecycle (§2.1 section 4) — FAIL if missing
grep -q "^## 4. Entity Lifecycle" "$ANALYSIS_FILE" || MISSING="${MISSING} [4.EntityLifecycle]"

# 5. Affected Processes (§2.1 section 5) — FAIL if missing
grep -q "^## 5. Affected Processes" "$ANALYSIS_FILE" || MISSING="${MISSING} [5.AffectedProcesses]"

# 6. Design + Pseudocode (§2.1 section 6) — FAIL if missing
grep -q "^## 6. Constraints & Pseudocode" "$ANALYSIS_FILE" || MISSING="${MISSING} [6.Pseudocode]"

# 7. Alternatives (§2.1 section 7) — WARN if missing (ok for XS/S trivial tasks)
grep -q "^## 7. Alternatives" "$ANALYSIS_FILE" || {
  if grep -q "effort_estimate: \"XS\"" "$ANALYSIS_FILE" || grep -q "effort_estimate: \"S\"" "$ANALYSIS_FILE"; then
    echo "WARN: Alternatives missing, but task is XS/S (acceptable for trivial tasks)"
  else
    MISSING="${MISSING} [7.Alternatives]"
  fi
}

# 8. Test Strategy (§2.1 section 8) — FAIL if missing
grep -q "^## 8. Test Strategy" "$ANALYSIS_FILE" || MISSING="${MISSING} [8.TestStrategy]"

# 9. Effort Estimate (§2.1 section 9) — FAIL if missing
grep -q "^## 9. Effort Estimate" "$ANALYSIS_FILE" || MISSING="${MISSING} [9.EffortEstimate]"

# 10. Acceptance Criteria Mapping (§2.1 section 10) — FAIL if missing
grep -q "^## 10. Acceptance Criteria Mapping" "$ANALYSIS_FILE" || MISSING="${MISSING} [10.ACMapping]"

# 11. Open Questions & Risks (§2.1 section 11) — FAIL if missing
grep -q "^## 11. Open Questions & Risks" "$ANALYSIS_FILE" || MISSING="${MISSING} [11.Risks]"

if [ -n "$MISSING" ]; then
  echo ""
  echo "❌ FAIL: Analysis incomplete. Missing sections:$MISSING"
  echo "→ Set status = DRAFT, keep task in DESIGN state"
  echo "→ Implementátor dostane neúplnou analýzu — UNACCEPTABLE"
  exit 1
else
  echo ""
  echo "✅ PASS: Analysis complete. All mandatory sections present."
  echo "→ Safe to set status = READY, mark task as READY"
  exit 0
fi
```

**Výsledek validace:**
- ✅ PASS → `status: READY`, task je připraven pro implementaci
- ❌ FAIL → task vrátí do `status: DRAFT`, implementátor task přeskočí (zabezpečení integrity)

**DŮLEŽITÉ:** Tato validace se MUSÍ spustit PŘED nastavením `status: READY`. Pokud by implementátor dostal task s neúplnou analýzou, je to FAILURE stavu analýzy.

**Anti-patterns (zakázáno):**
- ❌ Analýza bez pseudokódu ("implementuj dle specifikace" — LLM potřebuje konkrétní kroky)
- ❌ Jediná alternativa ("jinak to nejde" — vždy existují ≥2 přístupy, byť jeden je horší, vyjimka jen pro XS/S)
- ❌ Prázdná sekce Tests ("testy doplní implementátor" — analyzátor MUSÍ definovat co testovat na které úrovni)
- ❌ Vágní rizika ("může to být složité" — konkrétní: "SQLite lock contention při concurrent writes")
- ❌ Over-engineering ("abstrakce pro budoucí rozšiřitelnost" bez aktuálního use case — YAGNI/KISS)
- ✅ Preferuj jednodušší řešení: pokud alternativa A je jednodušší a splňuje AC, zvol A i když B je "elegantnější"

**DŮLEŽITÉ: Synchronizace statusu.**  Kdykoli změníš status tasku (DESIGN → READY nebo naopak), aktualizuj **všechna tři místa**:
1. Per-task analýza (`{ANALYSES_ROOT}/{task_id}-analysis.md`, frontmatter `status:`)
2. Sprint plan Task Queue (`sprints/sprint-{N}.md`, sloupec `Status`)
3. **Backlog item** (`backlog/{task_id}.md`, frontmatter `status:`)

Pokud některé z těchto míst neaktualizuješ, `fabric-implement` uvidí nekonzistentní stav a task přeskočí.

### 4.1) Cross-task analýza (ABSOLUTNĚ POVINNÉ, VŽDY, ne jen pro ≥3 tasks)

> **KONTRAKT:** Proveď cross-task analýzu VŽDY, i pro single task (min. reference na impact na backlog).
> Analýza report NESMÍ být finalizován bez sekce `## Cross-task Analysis`.

**A) Pro 1-2 tasks:**
```markdown
## Cross-task Analysis

N/A — Sprint contains {N} task(s) only.
- Impact on other backlog: {task_id} does not conflict with pending items {item_ids} (verified via module dependency table)
- Future dependency: {if task creates new API/entity, note which future tasks will depend on this}
```

**B) Pro ≥3 tasks (MANDATORY ANALYSIS):**

Proveď kompletní cross-task analýzu PŘED finalizací:

**B1) Sdílené patterny:**
- Používají ≥2 tasks stejný modul? → identifikuj POŘADÍ implementace (who goes first)
- Zavádí ≥2 tasks nové modely? → ověř konzistenci naming/patterns
- Mění ≥2 tasks stejný ADR/spec constraint? → ověř že interpretace je konzistentní

**B2) Závislosti a konflikty (TABULKA):**

Vytvořit tabulku se VŠEMI páry tasků, které by mohly mít interakce:

```markdown
### Cross-task Dependencies

| Task A | Task B | Interaction | Resolution | Order |
|--------|--------|-------------|-----------|-------|
| {id} | {id} | {type: shared_module|new_model|conflict_adrs|data_dependency} | {solution} | A → B or B → A |
```

**Typy interakcí:**
- **shared_module**: Oba tasks modifikují stejný soubor → need sequential order
- **new_model**: Jeden task vytváří model, druhý ho čte → order: creator first
- **conflict_adrs**: Oba interpretují ADR jinak → escalate to governance review
- **data_dependency**: Task A vytváří data pro task B → A musí být READY prvo

**B3) Optimální pořadí (scoring algorithm):**

```
For each task pair:
  dependency_score = 1 if A blocks B, else 0
  risk_score = max_risk of both tasks (HIGH=3, MEDIUM=2, LOW=1)
  effort_score = effort (XS=1, S=2, M=3, L=4, XL=5)

For each position in queue:
  candidates = tasks with no unmet dependencies
  score each candidate: + (3 - effort) + (3 - risk)
    (prefer simpler, lower-risk tasks early for momentum)
  place highest-scored candidate

Result: ordered task list reflecting dependencies + risk mitigation
```

**Example (LLMem):**
```
Task Queue (INITIAL):
1. T-CORE-01: Add Qdrant backend (L, HIGH) — touches storage/backends/
2. T-API-02: Add allow_secrets flag (S, LOW) — touches models.py, recall/pipeline.py
3. T-TEST-03: Add regression test suite (M, LOW) — touches tests/

Cross-task Analysis:
- T-CORE-01 & T-API-02: no shared module, but T-API-02 needs storage layer stable
  → Recommend: T-CORE-01 first (foundational), then T-API-02
- T-CORE-01 & T-TEST-03: T-TEST-03 is orthogonal, can run in parallel
- T-API-02 & T-TEST-03: no interaction

Optimized Order (by scoring):
1. T-CORE-01 (L, HIGH) — foundational, block others
2. T-API-02 (S, LOW) — depends on CORE-01, simpler
3. T-TEST-03 (M, LOW) — orthogonal, runs in parallel

Recommendation: Execute CORE-01 first (blocking), then {API-02, TEST-03} in parallel.
```

**B4) Zapiš do analyze reportu:**

```markdown
## Cross-task Analysis

Tasks in sprint: {N}

### Shared Modules & Dependencies
{tabulka z B2}

### Execution Order
1. {task_id} (reason: {why first})
2. {task_id} (reason: {why second})
...

### Parallel Opportunities
- {task_id} + {task_id} can run in parallel (no shared modules)
- {task_id} + {task_id} must be sequential ({reason})

### Risks Mitigation
- {HIGH risk task}: ensure {specific test} passes before next task
- {potential conflict}: cross-reference {which AC/ADR} across tasks
```

**Anti-patterns:**
- ❌ Analyzovat tasks izolovaně bez cross-task pohledu (i pro single task: note impact on backlog)
- ❌ Nechat pořadí v Task Queue náhodné (musí reflektovat závislosti)
- ❌ Ignorovat shared module conflicts (=bug waiting to happen)
- ✅ Vždy identifikovat sdílené moduly a konflikty, i pro 1-2 tasks

### 5) Aktualizuj sprint plan deterministicky

Preferuj `plan-apply` (ne ruční edit), aby byl diff čistý:

```bash
python skills/fabric-init/tools/fabric.py plan-apply --plan "{WORK_ROOT}/sprints/sprint-{N}.md" --patch "{WORK_ROOT}/plans/analyze-{run_id}.yaml"
```

- Pokud `plan-apply` není praktické, uprav sprint plan ručně, ale zachovej tabulku strukturu.

> **OWNERSHIP (P2 fix #38):** Sekce `## Task Queue` v sprint plánu je vlastněna výhradně `fabric-analyze`. Jiné skills (fabric-sprint, fabric-implement) ji ČTOU ale NEPÍŠOU. Pokud implementátor potřebuje změnit status tasku, mění ho v `backlog/{id}.md` a v `analyses/{id}-analysis.md`, ne přímo v Task Queue.

### 6) Vygeneruj analyze report

- Shrň:
  - kolik targetů
  - kolik tasks (READY vs DESIGN)
  - jaké ADR/SPEC constraints byly použity
  - jaké clarifications jsi vytvořil do intake

Ulož do `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md` (schema `fabric.report.v1`) s kompletním frontmatter:

```yaml
---
schema: fabric.report.v1
kind: analyze
run_id: "analyze-{YYYY-MM-DD}-{RUN_ID}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: PASS
---
```

## Protokol (povinné)

Na začátku a na konci tohoto skillu zapiš události do protokolu:

- START:
  - `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "analyze" --event start`
- END (OK/WARN/ERROR):
  - `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "analyze" --event end --status {OK|WARN|ERROR} --report "{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}.md"`

---

## Self-check (VŠECHNY položky MUSÍ být ✅ ANTES publish)

### Per-task Analysis Quality (§2.1 contract)

- [ ] **Každý task má kompletní per-task analýzu** v `{ANALYSES_ROOT}/{task_id}-analysis.md`
- [ ] **§1 Constraints**: Tabulka `| ADR/Spec | Requirement | How satisfied |` — ≥1 row (može být "None")
- [ ] **§2 Data Flow**: ASCII diagram s minimálně 3 kroky + error handling pro každý krok (ne jen happy path)
- [ ] **§3 Module Dependency Table**: Tabulka `| Module | Type | Upstream | Downstream | Risk |` — VŠECHNY dotčené moduly
- [ ] **§4 Entity Lifecycle**: Stavy CREATED → ... → EXPIRED (pokud task mění entity); jinak "N/A — {reason}"
- [ ] **§5 Affected Processes**: Cross-reference s process-map.md (konkrétní proces jméno + kontrakty) nebo "NOTE: file not found"
- [ ] **§6 Pseudocode**: KONKRÉTNÍ (references actual files, functions, imports), ne generický Python
- [ ] **§7 Alternatives**: ≥2 alternativy (nebo WARN pro XS/S) s tabulkou `| Approach | Complexity | Risk | ADR Align | Test | Total | Chosen |`
- [ ] **§8 Test Strategy**: VŠECH 5 úrovní (Unit/Integration/E2E/Edge/Regression) s konkrétními test jmény (ne "implementátor doplní")
- [ ] **§9 Effort Estimate**: Vypočteno algoritmicky (FILES_TOUCHED + NEW_TESTS + MAX_COMPLEXITY) + výpočet zobrazen
- [ ] **§10 AC Mapping**: Tabulka mapování AC → jak task splňuje
- [ ] **§11 Risks & Open Questions**: Konkrétní rizika (ne "může být složité") + mitigation + open questions (ne prázdné)

### Contract Validation (§4 enforcement)

- [ ] **Contract validation script PASSED**: Všechny 11 sekcí přítomny (výjimka: Alternatives ok pro XS/S)
  - Pokud FAIL → task vrácen do DESIGN, implementátor ho přeskočí
  - Pokud PASS → status nastavěn na READY ✅
- [ ] **Status synchronization**: VŠECHNY 3 místa updated:
  1. `{ANALYSES_ROOT}/{task_id}-analysis.md` frontmatter `status:`
  2. `{WORK_ROOT}/sprints/sprint-{N}.md` Task Queue sloupec `Status`
  3. `{WORK_ROOT}/backlog/{task_id}.md` frontmatter `status:`

### Cross-task Analysis (§4.1 ALWAYS)

- [ ] **Cross-task analýza v analyze reportu** (i pro 1-2 tasks):
  - 1-2 tasks: "N/A — {N} tasks, impact on backlog verified"
  - ≥3 tasks: KOMPLETNÍ analýza s dependency table + execution order + parallel opportunities
- [ ] **Dependency ordering**: Task Queue seřazeno podle: dependencies → risk → effort (momentum)
- [ ] **Shared modules identified**: Pokud ≥2 tasks touch stejný soubor → explicita order v reportu

### Governance Integrity

- [ ] **Governance indexes existují** a jsou čitelné (`{WORK_ROOT}/decisions/INDEX.md`, `{WORK_ROOT}/specs/INDEX.md`)
- [ ] **Constraints sekce**: Všechny relevantní ADR/SPEC odkazovány (ne vynechané)
- [ ] **Conflicts escalated**: Pokud task conflicts s ADR/SPEC → intake item `governance-clarification-{task_id}.md` vytvořen

### Test Coverage & Process Chain

- [ ] **Write Path tasks** (capture, triage, store): test pokrytí Write Path chain (capture→triage→store→verify)
- [ ] **Recall Path tasks** (recall, scoring, injection): test pokrytí Recall Path chain (query→search→score→inject)
- [ ] **Critical process tests**: Pokud task mění process-map kontrakty → `test_e2e_{process_name}` zmapován
- [ ] **Regression coverage**: Pokud bugfix → `test_{id}_regression_{bug}` named konkrétně

### Effort & Scope Sanity

- [ ] **Effort sanity check**: Pokud S ale FILES_TOUCHED ≥5 → odhad Updated (L nebo XL)
- [ ] **XL/oversized tasks split**: Pokud EFFORT = XL → task je rozložen na ≤L subtasks
- [ ] **Anti-patterns**: Vágní popis ("implementuj feature X" — musí být konkrétní soubory/funkce)

### Report & Artifacts

- [ ] **Analyze report** (`{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md`) vytvořen:
  - Souhrn: N targetů → N tasks (M READY, N-M DESIGN)
  - ADR/SPEC constraints použité
  - Clarifications vytvořené (intake items)
  - Cross-task analysis sekce
- [ ] **Intake items** (pokud potřeba): `{WORK_ROOT}/intake/governance-clarification-*.md` + `{WORK_ROOT}/intake/blocker-*.md`
- [ ] **Backlog updated**: Všechny backlog items s linkama na analysis (`See {ANALYSES_ROOT}/{task_id}-analysis.md`)

### Final Checkpoint

**BLOCKING ENFORCEMENT (WQ10: CRITICAL findings MUST fail analyze):**

- [ ] ✅ Všechny per-task analýzy prošly contract validation (PASS)
  - ❌ CRITICAL: Analýza chybí povinné sekce (§1-§11) → **FAIL task** (vrátit do DESIGN, EXIT 1)
  - ❌ CRITICAL: Task in READY ale bez Data Flow diagram → **EXIT 1** (incomplete specification)
- [ ] ✅ Všechny tasks v Task Queue jsou READY nebo DESIGN (ne other states)
  - ❌ CRITICAL: Task se opakuje ve více řádcích Task Queue → **EXIT 1** (duplicate cleanup required)
- [ ] ✅ Žádný task v READY bez kompletní analýzy (contract enforcement passed)
  - ❌ CRITICAL: Status sync mismatch (READY v analysis, DESIGN v backlog) → **EXIT 1** (synchronize before publish)
- [ ] ✅ Cross-task analýza pokrývá všechny interakce (dependency ordering optimized)
  - ❌ CRITICAL: Circular dependency detected (A→B→A) → **EXIT 1** (unresolvable, intake item required)
- [ ] ✅ Report vygenerován a archivován
  - ❌ CRITICAL: Analyze report missing or truncated → **EXIT 1** (re-run analysis)

**Non-critical warnings (don't fail analyze):**
- ⚠️ WARN: Task is DESIGN (incomplete analysis) — note in report, implementer will skip
- ⚠️ WARN: Effort estimate ≥XL — recommend splitting (but don't fail)
- ⚠️ WARN: process-map.md missing — note in report, continue without process validation

Pokud JAKÝKOLIV CRITICAL check selhává → **EXIT 1, log error, artifact cleanup** (don't publish partial report).

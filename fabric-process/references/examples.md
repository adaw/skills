# Examples & Templates — fabric-process

This file contains detailed examples and templates referenced from §7 of the main SKILL.md.

## P1: Complete LLMem External Processes Example

```markdown
## External Processes

### API Endpoints

| Process ID | Actor(s) | Trigger | Entry Point | Response | Status |
|---|---|---|---|---|---|
| ext-capture-event | agent, client | Tool execution completes | POST /capture/event | CaptureResponse (event_id, stored_memories, ok) | ACTIVE |
| ext-capture-batch | agent, client | Batch observation upload | POST /capture/batch | list[CaptureResponse] (per-event statuses) | ACTIVE |
| ext-recall-query | agent, client | Before agent turn, context needed | POST /recall | RecallResponse (xml_block, memory_count, budget_used) | ACTIVE |
| ext-memory-create | admin, client | Direct memory insertion | POST /memories | MemoryItem (id, content, tier, sensitivity) | ACTIVE |
| ext-memory-get | admin, client | Retrieve specific memory | GET /memories/{instance_id}/{memory_id} | MemoryItem (full record) | ACTIVE |
| ext-memory-tombstone | admin, system | Soft-delete memory (privacy) | POST /memories/{instance_id}/{memory_id}/tombstone | TombstoneResponse (deleted_id, timestamp) | ACTIVE |
| ext-health-check | monitoring, orchestration | Liveness probe (periodic ~30s) | GET /healthz | HealthResponse (status, version, instance_id) | ACTIVE |
| ext-health-check-v1 | monitoring, orchestration | API v1 health endpoint | GET /api/v1/healthz | HealthResponse (status, version) | ACTIVE |

### CLI Commands

| Process ID | Actor(s) | Trigger | Entry Point | Output | Status |
|---|---|---|---|---|---|
| ext-cli-serve | sysadmin, operator | Manual start (docker/systemd) | `llmem serve` | HTTP server listening on 127.0.0.1:8080 | ACTIVE |
| ext-cli-capture | user, script | Manual/scripted event submission | `llmem capture --text "..."` | Stored memory ID + triage results | ACTIVE |
| ext-cli-recall | user, operator | Manual context retrieval | `llmem recall --query "..."` | XML-formatted recall block | ACTIVE |
| ext-cli-healthz | monitoring, script | Health check via CLI | `llmem healthz` | Status output (HEALTHY/DEGRADED) | ACTIVE |
| ext-cli-doctor | sysadmin | Diagnostic check | `llmem doctor` | Report of configuration + backend health | ACTIVE |
| ext-cli-rebuild | operator, dba | Event-source rebuild from JSONL log | `llmem rebuild --instance <id>` | Rebuilt collection + validation report | ACTIVE |
```

## P2: Internal Process Call Chain Example

```
Entry: POST /capture/event
  │
  ├─ 1. routes/capture.py::capture_event()
  │     Input: ObservationEventIn (validated by Pydantic)
  │     Calls: CaptureService.capture()
  │
  ├─ 2. services/capture_service.py::CaptureService.capture()
  │     ├─ Generate event_id (UUIDv7 from content_hash — D0002)
  │     ├─ LogManager.append(event) → JSONL (source of truth — D0003)
  │     ├─ prepare() → triage_event()
  │     │     ├─ patterns.detect_secrets() → sensitivity tagging
  │     │     ├─ score_importance() → MemoryTier (must_remember/nice_to_have/ignore)
  │     │     ├─ mask_pii() if non-secret item contains PII
  │     │     └─ return list[MemoryItem]
  │     └─ store(items) → Backend.upsert()
  │
  ├─ 3. storage/backends/{inmemory|qdrant}.py::upsert()
  │     Side effect: Qdrant collection updated (or dict in InMemory)
  │
  └─ Return: CaptureResponse(ok=True, stored_memories=[ids])

Contract modules: [routes/capture.py, services/capture_service.py, triage/heuristics.py, triage/patterns.py, storage/log_jsonl.py, storage/backends/]
Governance: D0001 (secrets), D0002 (IDs), D0003 (event-sourcing)
```

## P2: Individual Process File Template (v1.2)

```markdown
---
schema: fabric.process.v1
id: int-capture-triage-store
category: internal
actors: [agent, tool]
status: ACTIVE
version: "1.2"                    # WQ9 fix: track process signature version
version_history:                   # WQ9 fix: when did signature change
  - version: "1.2"
    date: 2026-03-06
    change: "Added sensitivity.elevated_risk field for new secret patterns"
  - version: "1.1"
    date: 2025-12-15
    change: "Introduced PII hashing in triage"
  - version: "1.0"
    date: 2025-06-01
    change: "Initial process definition"
entry_point: "CaptureService.capture()"
contract_modules: [services/capture_service.py, triage/heuristics.py, triage/patterns.py, storage/log_jsonl.py]
related_external: [ext-capture-event, ext-capture-batch, ext-cli-capture]
governance: [D0001, D0002, D0003]
---

## Summary
Single-event capture pipeline: validates input, triages importance, masks secrets/PII, stores to backend.

## Call Chain
[ASCII diagram as shown above]

## Causal Dependencies
- ObservationEvent.text → triage scoring → MemoryTier assignment → storage decision
- D0001 secrets policy → sensitivity tagging → recall filtering (allow_secrets gate)
- D0002 content_hash → deterministic event_id → idempotency (duplicate detection)

## Side Effects
- JSONL log: immutable append (source of truth for rebuild)
- Qdrant/InMemory: upsert (queryable by recall)

## Error Paths
- Invalid input → 400 (Pydantic validation)
- Backend unavailable → 500 but fail-open (log warning, event still in JSONL)
- Secret detected → tagged sensitivity=secret, stored but filtered on recall

## Test Coverage
- Unit: tests/test_capture_service.py
- Integration: tests/test_triage_and_recall.py
- E2E: tests/e2e/ (if present)

## Deprecation (if applicable)
status: DEPRECATED                # WQ9 fix: if process is being retired
migration_to: int-capture-v2-async # Which new process replaces it
sunset_date: 2026-06-01           # When old process will be removed
migration_notes: |
  Use int-capture-v2-async for new integrations.
  Existing code can call int-capture-triage-store until sunset_date.
  See ADR-0005 for migration guide.
```

## P3: Cross-Layer Mapping Template

```markdown
## Cross-Layer Mappings

| External Process | Internal Chain(s) | Verified |
|---|---|---|
| ext-capture-event | int-capture-triage-store, int-async-capture-worker | ✓ |
| ext-recall-query | int-recall-multi-layer | ✓ |
| ext-cli-serve | int-server-startup | ✓ |

## Orphan Detection

### External without implementation (CRITICAL)
- [ ] ext-cli-knowledge-add — documented in vision, no CLI code yet (→ PLANNED)

### Code without external interface
- InMemoryBackend.search_hybrid() — INTERNAL_ONLY (dev/test backend, correct)
- score_importance() — INTERNAL_ONLY (helper called from prepare(), correct)

### Unresolved
(žádné, nebo seznam s intake items)
```

## Orphan Classification Categories

### DEAD_CODE
- **Definition:** No callers found in the codebase
- **Action:** Remove or document why exists
- **Intake Type:** Chore

### INTERNAL_ONLY
- **Definition:** Callers only from test files or internal helpers
- **Action:** Correct — no intake item needed (test helper)
- **Intake Type:** None

### UNDOCUMENTED
- **Definition:** Function is called in production code but callers are not in process-map contract_modules
- **Action:** Extend process-map to add calling chain, or reclassify as INTERNAL_ONLY if actually a helper
- **Intake Type:** Task

### DOCUMENTED
- **Definition:** Function is properly listed in a process chain
- **Action:** No action needed
- **Intake Type:** None

## P5: Process Map Master Document Template

```markdown
---
schema: fabric.process-map.v1
kind: process-map
version: "1.0"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
last_validated: {YYYY-MM-DD}
validation_status: VALID
external_count: {N}
internal_count: {N}
orphan_count: {N}
---

# LLMem Process Map

> Živá mapa business procesů. Aktualizuje `fabric-process` v orientační fázi.
> Downstream skills: fabric-gap (coverage), fabric-review (chain validation),
> fabric-check (freshness), fabric-analyze (affected processes).

## External Processes (vnější)

{tabulky z P1 — per kategorie: API, CLI, System-to-System}

## Internal Processes (vnitřní)

{per-process: ID, trigger, call chain, contract_modules, governance}

## Cross-Layer Mappings

{tabulka z P3: external → internal chain(s)}

## Orphan Detection

{orphan lista z P3 s klasifikací}

## Validation Notes

- Last validated: {datum}
- Test result: {PASS/FAIL/SKIP}
- Stale threshold: 7 days
```

## Process ID Naming Conventions

- **External:** `ext-{doména}-{akce}`
  - Example: `ext-capture-event`, `ext-cli-serve`, `ext-health-check`
- **Internal:** `int-{flow}-{popis}`
  - Example: `int-capture-triage-store`, `int-recall-multi-layer`
- **Cross-reference:** `cross-{vnější}-to-{vnitřní}`
  - Note: Link, not standalone process

## Significant Process Threshold (WQ5)

A process is SIGNIFICANT (requires detailed trace) if:
1. **API route or CLI command** (external-facing) — OR
2. **Has ≥3 downstream function calls** (depth ≥3: handler→service→helper) — OR
3. **Modifies persisted state** (writes to JSONL, DB, cache) — OR
4. **Critical to agent execution** (memory capture, recall, health check)

Examples:
- `POST /capture/event` → SIGNIFICANT (API + 4-level depth + JSONL write)
- `GET /healthz` → SIGNIFICANT (API endpoint, even if 1-level deep)
- `score_importance()` → NOT significant (internal helper, called from significant process but traced via parent)

# fabric-gap Examples & Templates

Příklady vyplněných gap reportů, intake items, a vzory z praktiky.

---

## Example 1: Gap Report — Security & Validation Gaps

Real LLMem project data:

```yaml
---
title: "Gap Report - 2026-03-06"
version: "1.0"
date: "2026-03-06"
status: "CRITICAL_FINDINGS_PRESENT"
gap_count: 7
critical_gaps: 2
---

## Summary

**Coverage:** 18 of 22 capabilities have code/test coverage. 2 capabilities completely missing (async validation, rate limiting).

**Test Status:** 87 passed, 2 failed. Stubs found: 3 (in api/routes/capture.py).

**Security Gaps:** 2 CRITICAL (missing input validation on /capture endpoint, no rate limiting).

## Gap Analysis

### Critical Gaps (Must Fix Before Merge)

| Gap ID | Type | Root Cause | Evidence | Impact | Priority |
|--------|------|-----------|----------|--------|----------|
| G-001 | Vision→Code gap | OVERSIGHT | POST /capture/event handler in api/routes/capture.py:line 45 has no Pydantic validation. Accepts raw dict. | CRITICAL — DOS vulnerability, any malformed JSON crashes endpoint | 30 (URGENT) |
| G-002 | Code→Test gap | DEFERRED | Rate limiting middleware not implemented. No test_rate_limit.py exists. Referenced in ADR-002 but marked DEFER. | HIGH — Every sprint needs rate limiting, easy fix (1 day) | 20 (HIGH) |
| G-003 | Code→Docs gap | CAPACITY | `/recall` endpoint exists but unmarked in API docs. No usage examples. Users cannot discover feature. | MEDIUM — Reduces discoverability, not urgent | 4 (MEDIUM) |

### Intake Items Created

- `intake/gap-g001-add-pydantic-validation.md` — Add Pydantic validation to /capture/event endpoint
- `intake/gap-g002-implement-rate-limiting.md` — Implement rate limiting middleware
- `intake/gap-g003-document-recall-endpoint.md` — Add /recall to API docs with examples

## Test Execution Results

```
Test Command: pytest -q --tb=line
Exit Code: 1 (1 FAIL detected)
Passed: 87
Failed: 2 (test_capture_no_validation, test_async_pending)
Errors: 0
Skipped: 5

Failing Tests:
- test_capture_no_validation: ValidationError expected but got dict (PROOF: G-001 is real)
- test_async_pending: NotImplementedError in async_embedder (PROOF: stub exists)
```

## Process Coverage

All 3 external processes have implementation code in {CODE_ROOT}:
- [IMPLEMENTED] EmbeddingProcess → src/llmem/embeddings/embed_service.py
- [IMPLEMENTED] RecallProcess → src/llmem/recall/pipeline.py
- [IMPLEMENTED] TriageProcess → src/llmem/triage/heuristics.py
```

---

## Example 2: Gap Report — Missing Feature & Backlog Drift

```yaml
---
title: "Gap Report - 2026-02-28"
version: "1.0"
date: "2026-02-28"
status: "HIGH_PRIORITY_BACKLOG_DRIFT"
gap_count: 5
critical_gaps: 1
---

## Summary

**Coverage:** 20 of 22 capabilities. Vision includes "Semantic Embeddings" (T1 goal) but backlog has no READY items for it.

**Backlog Drift:** 1 capability (semantic-embeddings) has 0 backlog items despite being vision pillar.

**Code Readiness:** Core API complete. Triage heuristics complete. Embedding layer is stub (NotImplementedError).

## Gap Analysis

| Gap ID | Type | Capability | Root Cause | Evidence | Impact | Priority |
|--------|------|-----------|-----------|----------|--------|----------|
| G-101 | Vision→Backlog gap | Semantic Embeddings | BLOCKED | Vision: {VISIONS_ROOT}/semantic-v2.md mentions embeddings. Backlog.md has NO items tagged T1. Analysis doc exists but stuck in DESIGN. | HIGH — Blocks T1 delivery | 15 (HIGH) |
| G-102 | Backlog→Code gap | CLI rebuild command | DEFERRED | Backlog item B-045 (READY). Code exists: src/llmem/cli.py:rebuild_command, but NOT exposed in main CLI entry. | MEDIUM — Feature complete, not exposed | 6 (MEDIUM) |

## Intake Items Created

- `intake/gap-g101-unblock-semantic-embeddings-spike.md` — Schedule spike to unblock semantic embeddings design (Blocker for T1)
- `intake/gap-g102-expose-rebuild-in-cli.md` — Wire rebuild_command into CLI main entrypoint
```

---

## Intake Item Template 1: Security Gap (CRITICAL)

```markdown
---
schema: fabric.intake_item.v1
title: "Add Pydantic validation to /capture/event endpoint"
source: gap
initial_type: Bug
raw_priority: 10
created: 2026-03-06
status: new
linked_vision_goal: "Reliable event capture"
---

## Problem

The POST /capture/event endpoint at `api/routes/capture.py:line 45` accepts raw dictionaries without Pydantic validation. This allows malformed JSON to crash the endpoint, creating a DOS vulnerability.

## Evidence

- **Gap ID:** G-001
- **Root Cause:** OVERSIGHT — validation was meant to be added but slipped
- **Severity:** CRITICAL
- **File:** `src/llmem/api/routes/capture.py:45`
- **Proof:** test_capture_no_validation fails: expects ValidationError but gets dict

## Impact

- DOS vulnerability: any malformed JSON crashes endpoint
- Production availability risk
- Blocks deployment to customers

## Recommended Action

1. Import Pydantic BaseModel in capture.py
2. Create `CaptureEventModel` with strict validation (required fields: timestamp, agent_id, data)
3. Wrap handler parameter: `event: CaptureEventModel`
4. Update test_capture_no_validation to expect proper validation
5. Add test_capture_invalid_json: send `{"invalid": "json"}`, expect 422 Unprocessable Entity

## Acceptance Criteria

- [ ] POST /capture/event validates incoming JSON against Pydantic schema
- [ ] Invalid requests return 422 Unprocessable Entity with field errors
- [ ] test_capture_no_validation passes (ValidationError raised)
- [ ] test_capture_invalid_json passes (malformed JSON rejected)
- [ ] Endpoint is no longer vulnerable to DOS from malformed input

## Estimated Effort

1 day (validation logic + 2 tests)
```

---

## Intake Item Template 2: Backlog-Code Gap (HIGH)

```markdown
---
schema: fabric.intake_item.v1
title: "Implement rate limiting middleware"
source: gap
initial_type: Task
raw_priority: 8
created: 2026-03-06
status: new
linked_vision_goal: "Production-ready API"
---

## Problem

Rate limiting middleware is referenced in ADR-002 and marked READY in the backlog (item B-042), but implementation is deferred. Without rate limiting, /capture endpoint is vulnerable to abuse and can be overwhelmed by high-volume requests.

## Evidence

- **Gap ID:** G-002
- **Root Cause:** DEFERRED — PR #123 waiting code review
- **Severity:** HIGH
- **Backlog Item:** B-042 (READY, marked DEFERRED in PR #123)
- **Missing:** No rate_limit or RateLimiter imports in src/llmem/api/

## Impact

- Every sprint, capacity is wasted defending against high-volume abuse
- No rate limiting = predictable bottleneck in production
- Blocks T1 reliability goal

## Recommended Action

1. Add `python-slowapi` dependency to requirements-dev.txt
2. Create `src/llmem/api/middleware/rate_limit.py` with:
   - FastAPI Limiter integration
   - Default: 100 requests per minute per client IP
   - /capture endpoint: 10 requests per minute (tighter limit)
3. Apply middleware in server.py
4. Write test_rate_limit.py (3 tests: normal, burst, exceed)
5. Document in API spec

## Acceptance Criteria

- [ ] Rate limiter middleware installed and applied to FastAPI app
- [ ] /capture endpoint limited to 10 req/min per IP
- [ ] Other endpoints default to 100 req/min per IP
- [ ] test_rate_limit_normal: 100 requests succeed
- [ ] test_rate_limit_burst: 101st request returns 429 Too Many Requests
- [ ] test_rate_limit_headers: response includes X-RateLimit headers

## Estimated Effort

2 days (middleware + tests + docs)
```

---

## Intake Item Template 3: Docs Gap (MEDIUM)

```markdown
---
schema: fabric.intake_item.v1
title: "Document /recall endpoint in API docs"
source: gap
initial_type: Chore
raw_priority: 6
created: 2026-03-06
status: new
linked_vision_goal: "Discoverability"
---

## Problem

The `/recall` endpoint exists in code (`src/llmem/api/routes/recall.py`) and works correctly, but is not documented in `{DOCS_ROOT}/`. Users cannot discover this feature.

## Evidence

- **Gap ID:** G-003
- **Root Cause:** CAPACITY — doc writing was lower priority
- **Severity:** MEDIUM
- **Missing:** No mention of /recall in docs/ — grep failure
- **Code:** Endpoint fully implemented and tested

## Impact

- Users unaware of recall feature → low adoption
- Support burden increases when users rediscover via luck

## Recommended Action

1. Add `/recall` section to `docs/api.md` (or create `docs/recall.md`)
2. Include:
   - Endpoint signature: POST /recall
   - Query parameters (query, memory_tier, limit, budget_tokens)
   - Response schema (JSON example with actual output)
   - 2 code examples (cURL, Python)
   - Use case: "Search long-term memory for related observations"
3. Link from main API overview

## Acceptance Criteria

- [ ] `/recall` documented in docs/ with full signature
- [ ] At least 1 code example (cURL or Python)
- [ ] Response schema shown with example output
- [ ] Linked from docs/api.md overview

## Estimated Effort

0.5 days (doc writing + 1 example)
```

---

## Intake Item Template 4: Vision-Backlog Gap (SPIKE)

```markdown
---
schema: fabric.intake_item.v1
title: "Unblock semantic embeddings spike"
source: gap
initial_type: Spike
raw_priority: 9
created: 2026-03-06
status: new
linked_vision_goal: "Semantic Embeddings (T1)"
---

## Problem

Vision document `{VISIONS_ROOT}/semantic-v2.md` lists "Semantic Embeddings" as a T1 goal, but backlog.md has no READY or PLANNED items for it. Analysis stuck in DESIGN phase. This blocks T1 delivery and creates risk of missing deadline.

## Evidence

- **Gap ID:** G-101
- **Root Cause:** BLOCKED — waiting decision on embedding model vendor
- **Severity:** HIGH
- **Vision:** {VISIONS_ROOT}/semantic-v2.md (T1 pillar)
- **Backlog:** 0 items tagged "semantic-embeddings"
- **Analysis:** {ANALYSES_ROOT}/semantic-design.md (stuck in DESIGN, needs review)

## Impact

- Blocks T1 delivery (scheduled Q2 release)
- Unknown effort estimate
- Risk of missing deadline if vendor decision delayed further

## Recommended Action

1. Schedule decision meeting: choose embedding model vendor (OpenAI, Anthropic, local)
2. Unblock analysis doc (semantic-design.md) — apply comments, finalize SPEC
3. Create 2–3 backlog items from SPEC:
   - B-2XX: Integrate embedding API (Task, 5 days)
   - B-2YY: Write semantic similarity scoring (Task, 3 days)
   - B-2ZZ: Write tests for recall with embeddings (Task, 2 days)
4. Estimate total effort: 10 days

## Acceptance Criteria

- [ ] Vendor decision made and documented in semantic-design.md
- [ ] semantic-design.md approved (no longer DESIGN status)
- [ ] At least 2 backlog items created with concrete effort estimates
- [ ] T1 timeline updated with realistic dates based on effort

## Estimated Effort

0.5 days decision + 0.5 days analysis finalization + 0.5 days backlog creation = 1.5 days
```

---

## Intake Item Template 5: Process Coverage Gap (TASK)

```markdown
---
schema: fabric.intake_item.v1
title: "Implement external process: async-validation"
source: gap
initial_type: Task
raw_priority: 7
created: 2026-03-06
status: new
---

## Problem

External process `async-validation` is documented in `fabric/processes/process-map.md` but has no implementation in the codebase. This process is referenced by Vision (async validation of requests), but has no handler.

## Evidence

- **Documented in:** `fabric/processes/process-map.md` (line 42: `- [async-validation]`)
- **Missing handler:** grep `{CODE_ROOT}/` for "async_validation" or "async-validation" returns no match
- **Impact:** Vision goal "Async Validation" cannot be realized

## Recommended Action

1. Create `src/llmem/api/middleware/async_validation.py` with:
   - Async validator handler
   - Input contract: event (ObservationEvent)
   - Output contract: validation_result (ValidationResult)
2. Register in process registry (config.py or process_map_impl.py)
3. Write tests: test_async_validation_valid, test_async_validation_invalid
4. Document handler in ADR-002

## Acceptance Criteria

- [ ] Handler created with clear input/output contracts
- [ ] Handler registered in process registry
- [ ] Basic tests verify handler can be invoked
- [ ] Documentation updated with implementation details

## Estimated Effort

3 days (handler + tests + ADR update)
```

---

## Real Gap Report Format (Full Example)

```markdown
---
schema: fabric.report.v1
kind: gap
run_id: "gap-20260306-001"
created_at: "2026-03-06T14:32:15Z"
status: WARN
critical_findings_count: 2
total_gaps: 7
intake_items_created: 3
---

# Gap Report — 2026-03-06

## Summary

- **Coverage:** 18 of 22 capabilities have code/test coverage. Missing: async-validation, rate-limiting (partially), semantic-embeddings (design phase), cli-rebuild (code exists, not exposed).
- **Test Status:** 87 passed, 2 failed. Stubs found: 3.
- **Security Gaps:** 2 CRITICAL (input validation, hardcoded secrets), 1 HIGH (rate limiting).

## Vision→Backlog Gap Analysis

| Capability | Backlog Items | Status | Note |
|------------|---------------|--------|------|
| Core event capture | B-001, B-002 | DONE | ✓ |
| Triage heuristics | B-010 | DONE | ✓ |
| Recall pipeline | B-020, B-021 | DONE | ✓ |
| Async validation | — | MISSING | Gap G-101 |
| Semantic embeddings | Design phase | BLOCKED | Gap G-102 |
| Rate limiting | B-042 | DEFERRED | Gap G-103 |

## Backlog→Code Gap Analysis

| Item | Title | Status | Code Exists | Gap ID |
|------|-------|--------|-------------|--------|
| B-001 | Capture event handler | DONE | ✓ but unvalidated | G-001 |
| B-042 | Rate limiting | READY | ✗ deferred | G-002 |
| B-050 | CLI rebuild | READY | ✓ but not exposed | G-003 |

## Code→Test Gap Analysis

| Module | Tests Exist | Coverage | Gap ID |
|--------|-------------|----------|--------|
| capture.py | ✓ | 85% | — |
| rate_limit.py | ✗ missing | 0% | G-002 |
| recall.py | ✓ | 92% | — |

## Code→Docs Gap Analysis

| Endpoint | Documented | Gap ID |
|----------|-------------|--------|
| POST /capture/event | ✓ | — |
| POST /recall | ✗ | G-004 |
| GET /healthz | ✓ | — |

## Security Gaps

| Gap ID | Type | Evidence | Severity | Priority |
|--------|------|----------|----------|----------|
| G-001 | Input Validation | capture.py:45 no Pydantic | CRITICAL | 30 |
| G-005 | Hardcoded Secret | config.py:12 OPENAI_KEY="sk-..." | CRITICAL | 25 |
| G-002 | Rate Limiting | No middleware | HIGH | 20 |

## Operational Gaps

| Gap ID | Type | Evidence | Severity |
|--------|------|----------|----------|
| G-006 | Logging | api/server.py has no logger config | MEDIUM |
| G-007 | Timeout Config | routes/*.py missing timeout | MEDIUM |

## Intake Items Created

1. `intake/gap-g001-add-pydantic-validation.md` — Fix input validation (CRITICAL)
2. `intake/gap-g002-implement-rate-limiting.md` — Add rate limiting (HIGH)
3. `intake/gap-g004-document-recall.md` — Document /recall endpoint (MEDIUM)

---

Total: 7 gaps identified, 3 critical/high priority → 3 intake items created.
```

---

## How to Validate a Gap Report

**Checklist:**
- [ ] All 7 gap types represented (if applicable): Vision→Backlog, Backlog→Code, Code→Tests, Code→Docs, Security, Operational, Process
- [ ] Each gap has: gap_id, type, severity, root_cause, evidence (file:line), impact, priority
- [ ] CRITICAL gaps have intake items
- [ ] Intake items have AC (acceptance criteria)
- [ ] Report frontmatter has `schema: fabric.report.v1`
- [ ] Test results recorded (PASS/FAIL/TIMEOUT)
- [ ] Stub count recorded

**Anti-check:**
- [ ] No gap without root cause (DEFER/BLOCK/OVERSIGHT/CAPACITY)
- [ ] No vague evidence ("something missing")
- [ ] No CRITICAL gaps without intake items (unless justified)

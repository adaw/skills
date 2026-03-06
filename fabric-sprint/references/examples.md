# fabric-sprint — Praktické příklady

Tato příloha obsahuje konkrétní vyplněné příklady sprint plánů a reportů.

---

## Příklad 1: Sprint 2 pro LLMem — Triage & Security

**Kontext:** Po Sprint 1 máme základní capture/recall pipeline. Sprint 2 se zaměřuje na triage heuristics a security (input validation, rate limiting).

**File:** `{WORK_ROOT}/sprints/sprint-2.md`

```yaml
---
schema: fabric.report.v1
kind: sprint-plan
version: "1.0"
sprint_number: 2
start_date: "2026-03-10"
end_date: "2026-03-14"
goal: "Implement deterministic triage with secret/PII/preference detection; 70% test coverage on triage module."
max_tasks: 5
capacity_effort_hours: 40
---

# Sprint 2 Plan — Triage & Security

## Sprint Targets (Selected by fabric-prio)

| Priority | ID | Type | Title | Status | Effort | Confidence |
|----------|----|----|-------|--------|--------|-----------|
| 1 | T-TRI-01 | Task | Design triage heuristics (secret, PII, pref, decision) | READY | M | High |
| 2 | T-TRI-02 | Task | Implement triage heuristics module | READY | M | High |
| 3 | T-CAP-01 | Task | Integrate triage into CaptureService | READY | S | High |
| 4 | T-TEST-01 | Task | Add triage unit tests (patterns, edge cases) | READY | M | High |
| 5 | T-DOC-01 | Chore | Document triage heuristics API | DESIGN | S | Medium |

## Sprint Goal Justification

Triage heuristics unblock core Write Path functionality. T-TRI-01/02 jsou na kritické cestě. T-CAP-01 se integruje s CaptureService (vysoká jistota). T-TEST-01 řeší mezerou 62% → 70% coverage. T-DOC-01 je označen DESIGN (může se posunout).

**Effort Budget:** 5×M + 1×S = ~40 hours (kapacita: 40h, marže: 0%)

## Dependency Graph

| Task ID | Title | Depends On | Blocks | Critical Path |
|---------|-------|-----------|--------|--------------|
| T-TRI-01 | Design triage heuristics | None | T-TRI-02 | YES |
| T-TRI-02 | Implement triage heuristics | T-TRI-01 | T-CAP-01, T-TEST-01 | YES |
| T-CAP-01 | Integrate triage into CaptureService | T-TRI-02 | None | YES |
| T-TEST-01 | Add triage unit tests | T-TRI-02 | None | YES |
| T-DOC-01 | Document triage heuristics API | None | None | NO |

**Kritická cesta:** T-TRI-01 → T-TRI-02 → T-CAP-01 = 3 tasks (dobře se vejde do 5-day sprintu).

## Risk Assessment

| Task | Risk Level | Risk Description | Mitigation |
|------|-----------|------------------|-----------|
| T-TRI-01 | LOW | Design je na známých regex pattern — dobře zdokumentovaný | Standard design review |
| T-TRI-02 | MEDIUM | Regex patterns mohou být komplexní; edge cases se často découvri během impl | Pair programming s Alice; code review |
| T-CAP-01 | LOW | Integration pattern je standardní — CaptureService je stabilní | Standard testing |
| T-TEST-01 | MEDIUM | Mohou se objevit edge cases v pattern matching — třeba přidání nových testů | Run tests in isolation první; mock secret data |
| T-DOC-01 | LOW | Dokumentace — bez runtime rizika | Lze posunout pokud čas bude krátký |

**Akce:** Žádné HIGH-risk items. T-TRI-02 a T-TEST-01 vyžadují pair programming.

## Capacity Planning

| Dev | Availability | Max Hours | Assigned | Headroom | Utilization |
|-----|--------------|-----------|----------|----------|------------|
| Alice | 100% | 30h | 29h (T-TRI-01, T-TRI-02, T-CAP-01 vedení) | 1h | 97% |
| Bob | 80% (Pátek off) | 24h | 22h (T-TEST-01, T-DOC-01) | 2h | 92% |
| **TOTAL** | - | 54h | 51h | 3h | 94% |

**Cíl utilization:** 80-90%. Výsledek: 94% (mírně vysoký, ale akceptovatelný pro sprint s jasným scope).

## Rollover z předchozího sprintu

| Task | Sprint 1 Est. | Sprint 1 Actual | Reason | Status in Sprint 2 |
|------|-------------|----------------|--------|------------------|
| T-051 | S (7h) | 11h | Underestimated; spec change mid-sprint | Moved to Sprint 3 (DESIGN) |
| T-062 | BLOCKED | BLOCKED | Waiting on external firm security audit | Carry-over; lowest priority |

**Lessons:** Estimation method needs refinement. Pair estimation sessions recommended pro Sprint 3.

## Definition of Done

Sprint 2 je DONE když VŠECHNY tyto kritéria platí:

### Code Quality
- [ ] All tests PASS: `pytest -q` exit 0 on main after all merges
- [ ] Linting PASS: `ruff check src tests` exit 0
- [ ] Coverage ≥ 70% for modified modules (test_capture.py, test_triage.py)
- [ ] No stubs in DONE tasks (T-TRI-01 through T-CAP-01 fully implemented)

### Review & Design
- [ ] All PRs have CLEAN verdict from fabric-review
- [ ] Design decisions documented in decisions/ (if applicable)
- [ ] All PR comments resolved

### Documentation
- [ ] /capture and /recall endpoints documented with curl examples
- [ ] CHANGELOG updated with T-TRI-01, T-TRI-02 changes
- [ ] README updated if behavior changes

### Operational
- [ ] All target items marked DONE in backlog/
- [ ] No P0 bugs introduced (verified via integration tests)
- [ ] Triage patterns tested under load (100 secret/PII examples)

### Security Gate (Sprint-Specific)
- [ ] T-TRI-01/02: Secret detection catches OpenAI/GitHub/AWS keys
- [ ] T-TRI-01/02: PII detection catches emails/phones/SSNs
- [ ] T-CAP-01: Secrets are masked in non-secret items
- [ ] No hardcoded secrets in code/docs/tests

## Task Queue

| Order | ID | Type | Status | Estimate | Description |
|-------|----|------|--------|----------|-------------|
| 1 | T-TRI-01 | Task | READY | M (12h) | Design triage heuristics for secret/PII/preference/decision detection |
| 2 | T-TRI-02 | Task | READY | M (12h) | Implement heuristics module with regex patterns in triage/patterns.py |
| 3 | T-CAP-01 | Task | READY | S (7h) | Integrate triage() call into CaptureService.process_event() |
| 4 | T-TEST-01 | Task | READY | M (12h) | Add unit tests: test_secret_detection, test_pii_detection, test_edge_cases |
| 5 | T-DOC-01 | Chore | DESIGN | S (7h) | Document triage API (docstrings + examples) — optional, carry-over OK |
```

---

## Příklad 2: Sprint 3 pro LLMem — API Security & Documentation

**Kontext:** Sprint 3 je zaměřen na API security (input validation, rate limiting) a dokumentaci.

**File:** `{WORK_ROOT}/sprints/sprint-3.md`

```yaml
---
schema: fabric.report.v1
kind: sprint-plan
version: "1.0"
sprint_number: 3
start_date: "2026-03-17"
end_date: "2026-03-21"
goal: "Secure the API with input validation and rate limiting; improve test coverage above 70% for core modules."
max_tasks: 8
capacity_effort_hours: 54
---

# Sprint 3 Plan — API Security

## Sprint Targets (Selected by fabric-prio)

| Priority | ID | Type | Title | Status | Effort | Confidence |
|----------|----|----|-------|--------|--------|-----------|
| 1 | T-101 | Task | Add Pydantic validation to /capture endpoint | READY | S | High |
| 2 | T-102 | Task | Implement rate limiting middleware | READY | S | High |
| 3 | T-103 | Task | Add integration tests for /capture flow | READY | M | Medium |
| 4 | T-104 | Bug | Fix async embedder NotImplementedError stub | READY | XS | High |
| 5 | T-105 | Chore | Update API docs with /capture and /recall examples | DESIGN | M | Medium |
| 6 | T-106 | Task | Add coverage reporting to CI pipeline | READY | S | High |

## Sprint Goal Justification

T-101 + T-102 (security), T-103 (test coverage), T-104 (removes blocker pro semantic embeddings spike) jsou kritické pro next phase. T-105/T-106 improve operational excellence.

## Dependency Graph

| Task ID | Depends On | Blocks | Critical Path |
|---------|-----------|--------|---------------|
| T-101 | None | T-103 | YES (security gate) |
| T-102 | None | T-103 | YES (security gate) |
| T-103 | T-101, T-102 | None | YES (test gate) |
| T-104 | None | T-107 (future spike) | NO |
| T-105 | None | None | NO |
| T-106 | None | None | NO |

**Critical Path Length:** T-101 → T-103 = 2 tasks (fits v 5-day sprint comfortably).

## Risk Assessment

| Task | Risk Level | Mitigation |
|------|-----------|-----------|
| T-101 | LOW | Pydantic je standard pattern, dobře dokumentovaný |
| T-102 | MEDIUM | Async middleware complexity; pair program s Alice |
| T-103 | MEDIUM | Může odhalit existující bugs; run tests in isolation first |
| T-104 | LOW | Stub removal je straightforward |
| T-105 | LOW | Documentation only; no runtime risk |
| T-106 | LOW | CI change, isolated scope |

**Akce:** No HIGH-risk items; sprint je well-balanced.

## Capacity Planning

| Dev | Availability | Max Hours | Assigned | Headroom | Utilization |
|-----|--------------|-----------|----------|----------|------------|
| Alice | 100% | 30h | 29h (T-101, T-102, T-103 lead) | 1h | 97% |
| Bob | 80% (Fri off) | 24h | 22h (T-103, T-104, T-106) | 2h | 92% |
| **TOTAL** | - | 54h | 51h | 3h | 94% |

**Utilization Target:** 80-90%. Result: 94% (slightly high but acceptable).

## Rollover from Sprint 2

| Task | Sprint 2 Est. | Sprint 2 Actual | Reason | Status in Sprint 3 |
|------|-------------|----------------|--------|------------------|
| T-051 | S (7h) | 11h | Underestimated; spec change mid-sprint | Moved to Sprint 4 (DESIGN) |
| T-062 | BLOCKED | BLOCKED | Waiting on external firm security audit | Carrying over; lowest priority |

**Lessons:** Estimation method needs refinement; pair estimation sessions recommended for next sprint.

## Definition of Done

Sprint 3 je DONE když:

### Code Quality
- [ ] All tests PASS: `pytest -q` exit 0 on main
- [ ] Linting PASS: `ruff check src tests` exit 0
- [ ] Coverage ≥ 70% for modified modules (test_capture.py, test_rate_limit.py)
- [ ] No stubs in DONE code

### Review & Design
- [ ] All PRs have CLEAN verdict
- [ ] Design decisions documented
- [ ] All PR comments resolved

### Documentation
- [ ] /capture and /recall endpoints documented with curl examples
- [ ] CHANGELOG updated
- [ ] README updated if behavior changes

### Operational
- [ ] All target items marked DONE
- [ ] No P0 bugs introduced
- [ ] Rate limiting works under load (stress test: 1000 req/min)

### Security Gate
- [ ] T-101: Pydantic validation guards all user inputs
- [ ] T-102: Rate limiter enforces 100 req/min per client
- [ ] No hardcoded secrets

## Task Queue

| Order | ID | Type | Status | Estimate | Description |
|-------|----|------|--------|----------|-------------|
| 1 | T-101 | Task | READY | S (7h) | Add Pydantic validation to /capture endpoint |
| 2 | T-102 | Task | READY | S (8h) | Implement rate limiting middleware |
| 3 | T-103 | Task | DESIGN | M (14h) | Add integration tests for /capture flow |
| 4 | T-104 | Bug | READY | XS (3h) | Fix async embedder NotImplementedError stub |
| 5 | T-105 | Chore | DESIGN | M (12h) | Update API docs with examples |
| 6 | T-106 | Task | READY | S (6h) | Add coverage reporting to CI pipeline |
```

---

## Příklad 3: Sprint Report — Filled

**File:** `{WORK_ROOT}/reports/sprint-2-2026-03-14.md`

```yaml
---
schema: fabric.report.v1
kind: sprint
run_id: "sprint-2-1710429600"
created_at: "2026-03-14T16:30:00Z"
status: PASS
---

# Sprint 2 Report — 2026-03-14

## Souhrn

Výběr 5 targetů (T-TRI-01, T-TRI-02, T-CAP-01, T-TEST-01, T-DOC-01) zaměřených na implementaci triage heuristics a 70% test coverage. Společný cíl: "Implement deterministic triage with secret/PII/preference detection; 70% test coverage on triage module."

Kapacita: 54 person-hours na 2 dev (Alice 100%, Bob 80%). Vybrané targetů mají 51h estimated effort (94% utilization). Критична path: 3 tasks, vejde se do 5-day sprintu.

## Sprint Targets vybrané

| Priority | ID | Type | Title | Status | Effort | Confidence |
|----------|----|----|-------|--------|--------|-----------|
| 1 | T-TRI-01 | Task | Design triage heuristics | READY | M | High |
| 2 | T-TRI-02 | Task | Implement triage heuristics module | READY | M | High |
| 3 | T-CAP-01 | Task | Integrate triage into CaptureService | READY | S | High |
| 4 | T-TEST-01 | Task | Add triage unit tests | READY | M | High |
| 5 | T-DOC-01 | Chore | Document triage heuristics API | DESIGN | S | Medium |

## Rizika a Mitigace

| Task | Risk Level | Mitigation |
|------|-----------|-----------|
| T-TRI-02 | MEDIUM | Pair programming s Alice; code review zaměřená na regex correctness |
| T-TEST-01 | MEDIUM | Run tests in isolation pro detection false positives; mock secret data |

Ostatní: LOW risk. Žádné HIGH-risk items.

## Capacity Analysis

Total capacity: 54h (Alice 30h + Bob 24h, accounting for PTO)
Total assigned: 51h (94% utilization)
Headroom: 3h (6%)

Cíl utilization: 80-90%. Výsledek: 94% (akceptovatelný, ale těsný margin).

## Rollover z Sprint 1

- T-051 (S, 11h actual vs 7h est) → Moved to Sprint 3
- T-062 (BLOCKED) → Carrying over

Lessons: Estimation chyba ~50%. Pair estimation sessions pro Sprint 3.

## Intake items vytvořené

Žádné (všechny preconditions OK, žádné blocker problémy).

## Warnings

1. ⚠️ Utilization na 94% (těsný margin pro unexpected issues)
2. ⚠️ T-DOC-01 je v DESIGN status — carry-over risk pokud T-TRI-02 slip
3. ⚠️ Estimation accuracy z Sprint 1 byla nízká — zvážit refinement pro Sprint 3
```

---

## Příklad 4: Sprint Plan s Extended DoD a Metrics

**Kontext:** Sprint se zaměřuje na API security a includes explicitní security gate.

```yaml
---
schema: fabric.report.v1
kind: sprint-plan
version: "1.0"
sprint_number: 4
start_date: "2026-03-24"
end_date: "2026-03-28"
goal: "Complete API security hardening and achieve 80% coverage on all core modules."
max_tasks: 6
capacity_effort_hours: 48
---

# Sprint 4 Plan — API Hardening

## Sprint Targets

| Priority | ID | Type | Title | Status | Effort |
|----------|----|----|-------|--------|--------|
| 1 | T-201 | Task | Implement request rate limiting (per-client, per-endpoint) | READY | M |
| 2 | T-202 | Task | Add input validation schemas (Pydantic v2) | READY | M |
| 3 | T-203 | Task | Security testing suite (fuzzing, boundary conditions) | READY | M |
| 4 | T-204 | Chore | Update SECURITY.md with rate limit config | DESIGN | S |
| 5 | T-205 | Bug | Fix async event handling race condition (T-TEST-01 discovered) | READY | S |

## Definition of Done

### Code Quality Checks
- [ ] `pytest -q` exit 0 on main (all tests)
- [ ] `ruff check --select=E,W,F` exit 0 (enforce strict linting)
- [ ] Coverage report: `coverage report --min-coverage=80` for src/llmem/api/
- [ ] No warnings in mypy: `mypy src/llmem/`
- [ ] No stubs or `pass` placeholders in DONE code (T-201 through T-203)

### Security Checks
- [ ] T-201: Rate limiter enforces 100 req/min per client (verified via integration test)
- [ ] T-202: All /capture and /recall inputs validated per schema
- [ ] T-203: Fuzzing suite runs 10k random inputs without crash
- [ ] T-205: Race condition in async handling fixed (test covers regression)
- [ ] No hardcoded secrets in code/docs/tests (grep -r "password\|secret\|token" — zero matches)

### Design & Review
- [ ] All PRs merged via `fabric-review` with CLEAN verdict
- [ ] ADR-005 (rate limiting policy) updated if applicable
- [ ] Design decisions documented in fabric/decisions/ or PR body

### Documentation & Changelog
- [ ] README updated: security requirements section
- [ ] CHANGELOG.md entry: "Security: rate limiting, input validation"
- [ ] T-204: SECURITY.md updated with rate limit config and examples

### Operational Verification
- [ ] All backlog items (T-201 through T-205) status updated to DONE
- [ ] No P0 or P1 bugs introduced (QA sign-off)
- [ ] Performance regression test: `time curl -X POST /capture -d {...}` vs baseline (max +5% latency)
- [ ] Integration test suite passes: `pytest tests/e2e/ -v`

### Rollout Readiness
- [ ] Rate limiting config is documented and configurable (env vars, config.md)
- [ ] Deployment guide updated (if needed)
- [ ] Runbook for rate limit troubleshooting created

## Effort Estimation Detail

| Task | Files Modified | Tests Added | Complexity | Effort Calc | Hours |
|------|--------|-----------|-----------|-----------|-------|
| T-201 | 2 (middleware, config) | 5 (unit + integration) | 8 (stateful counter) | M | 12 |
| T-202 | 3 (routes, models, validation) | 6 (schema tests) | 7 (pydantic patterns) | M | 12 |
| T-203 | 2 (test utils, test suite) | 8 (fuzzing, edge cases) | 6 (deterministic fuzzer) | M | 14 |
| T-204 | 1 (SECURITY.md) | 0 | 1 (docs only) | S | 5 |
| T-205 | 2 (event handler, test) | 1 (regression test) | 5 (race condition fix) | S | 6 |
| **TOTAL** | 10 files | 20 tests | Avg 6.4 | **5 × M/S** | **49h** |

Budget vs Capacity:
- Estimated: 49h
- Capacity (Alice 30h + Bob 24h): 54h
- Utilization: 49/54 = 91% ✓

## Critical Path Analysis

```
T-201 (rate limiting) → T-203 (must test rate limiting)
T-202 (input validation) → T-203 (must test validation)
T-203 (security tests) → [integration verification]
T-205 (async fix) → [independent, parallel with above]
T-204 (docs) → [independent, can slip]

Longest path: T-201 → T-203 (2 tasks, ~26h)
Sprint duration: 5 days × 6h = 30h per dev
Fits comfortably within 5-day sprint ✓
```

## Per-Developer Assignment (Capacity Plan)

| Developer | Availability | Max Hours | Assigned | Task Assignment | Headroom |
|-----------|--------------|-----------|----------|-----------------|----------|
| Alice | 100% | 30h | 28h | T-201 lead (12h), T-203 (8h), code review (8h) | 2h |
| Bob | 85% (Thu PTO) | 25h | 21h | T-202 lead (12h), T-205 (6h), T-204 (3h) | 4h |

Utilization: (28+21) / (30+25) = 49/55 = 89% ✓ (target range 80-90%)

## Rollover Tracking (from Sprint 3)

| Task | Est. Sprint 3 | Actual Sprint 3 | Reason | Status Sprint 4 |
|------|-------------|-----------------|--------|-----------------|
| T-051 | S (7h) | 13h | Underestimate + scope creep | Moved to Sprint 5 (DESIGN) |
| T-062 | BLOCKED | BLOCKED | External audit pending | Carrying over; de-prioritized |

**Analysis:** Pattern of underestimation (Sprint 1: +57%, Sprint 2: +50%, Sprint 3: +86%). Recommendation: Use 1.3× multiplier for new task categories going forward. Pair estimation sessions starting Sprint 5.
```

---

## Příklad 5: Failure Report — Sprint Failed Pre-Gate

**Context:** Sprint selection process encountered blockers. Illustrates how failures are reported.

```yaml
---
schema: fabric.report.v1
kind: sprint
run_id: "sprint-5-FAILED-1710516000"
created_at: "2026-03-15T10:00:00Z"
status: FAIL
---

# Sprint 5 Report — PRE-GATE FAILURE

## Summary

Sprint 5 selection process FAILED at Pre-Sprint Validation Gate (§9 in SKILL.md). Root cause: insufficient capacity for selected targets.

**Utilization: 98%** (threshold: ≤90%)

**Resolution:** Removed 2 tasks (T-310, T-311) to bring utilization to 87%.

## Details

### Gate Failure Analysis

**Gate 1: Capacity Check**
- Total effort estimated: 53h (7 tasks × M/S estimate)
- Team capacity: 54h (Alice 30h + Bob 24h)
- Calculated utilization: 98%
- **FAIL:** 98% > 90% threshold

### Removed Tasks (to resolve capacity)

| Task ID | Type | Effort | Reason for Removal | Next Sprint |
|---------|------|--------|------------------|------------|
| T-310 | Task | M (12h) | Lowest priority in target set; dependency on T-305 (next sprint) | Sprint 6 |
| T-311 | Chore | M (12h) | Documentation — can slip without blocking implementation | Sprint 6 |

### Revised Sprint 5 Targets

| ID | Title | Effort |
|----|-------|--------|
| T-301 | Implement caching layer | M |
| T-302 | Add cache invalidation logic | M |
| T-303 | Test caching under load | M |
| T-304 | Update docs (DESIGN status, may slip) | S |
| T-305 | Fix memory leak in observation log | S |

**Revised effort:** 49h / 54h = 91% utilization ✓ PASS

## Intake Items Created

1. **intake/sprint-capacity-resolved-2026-03-15.md**
   - Source: fabric-sprint
   - Title: "Sprint 5 capacity overage resolved — tasks T-310, T-311 deferred to Sprint 6"
   - Type: Chore
   - Priority: 3 (informational)

## Warnings

1. ⚠️ Pattern: 3 consecutive sprints with high utilization (94%, 94%, 91%). Team may be overcommitted.
2. ⚠️ T-304 is in DESIGN status and high risk of slip — may want to exclude from sprint or allocate contingency.
3. ⚠️ Estimation accuracy remains low (avg +70% overrun Sprint 1-3). Recommend refined estimation process for Sprint 6.

## Recovery Actions

1. ✓ Removed lowest-priority tasks
2. ✓ Re-validated preconditions: capacity OK, no cycles, all estimates present, DoD complete
3. ✓ Created intake item for deferred tasks
4. ✓ Document lessons for future sprints

**Status:** Pre-gate resolved. Sprint 5 can proceed with revised target list.
```

---

## Příklad 6: Capacity Overage Detection Script Output

**Kontext:** Real output z fabric-sprint pre-gate validation.

```bash
=== PRE-SPRINT VALIDATION GATE ===

Gate 1: Capacity Check
--------
Selected targets: 7 tasks
Effort mapping:
  T-301: M (12h)
  T-302: M (12h)
  T-303: M (12h)
  T-304: S (7h)
  T-305: S (7h)
  T-310: M (12h)
  T-311: M (12h)
Total effort: 74h
Team capacity: Alice 30h + Bob 24h = 54h
Utilization: 74h / 54h = 137%
FAIL: Sprint utilization is 137% (>90%). Remove items or reduce scope.

→ Removing 2 lowest-priority tasks: T-310, T-311 (24h)
  Recalculated: 50h / 54h = 93%
  Still borderline. Removing T-304 (DESIGN, optional): 43h / 54h = 80%
  ...user decides to keep T-304 with carry-over risk acknowledged.
  Final: 50h / 54h = 93% — marginal, but accepted with WARNING.

Gate 2: Dependency Cycles
--------
Topological sort of 5 remaining tasks...
  T-301 (no deps)
  T-302 (depends on T-301)
  T-303 (depends on T-301, T-302)
  T-304 (no deps)
  T-305 (no deps)
Cycle detection: PASS (no cycles found)

Gate 3: Effort Estimates
--------
Checking all 5 tasks have estimates...
  T-301: M ✓
  T-302: M ✓
  T-303: M ✓
  T-304: S ✓
  T-305: S ✓
PASS: All tasks have estimates

Gate 4: Definition of Done
--------
Counting DoD checkboxes in sprint plan...
  Code Quality: 4 checkboxes
  Review & Design: 3 checkboxes
  Documentation: 3 checkboxes
  Operational: 3 checkboxes
  Sprint-Specific: 2 checkboxes
Total: 15 checkboxes
PASS: DoD complete (15 ≥ 5 minimum)

=== PRE-SPRINT GATE RESULT ===
Status: PASS (with WARNING on utilization)
Reason: Removed lowest-priority items to fit capacity
New utilization: 93% (acceptable with tight margin)

→ Sprint 5 can proceed.
```

---

## Příklad 7: Backlog Snapshot (FAST PATH Output)

**Kontext:** fabric.py backlog-scan output — JSON snapshot pro reproducible selection.

```json
{
  "run_date": "2026-03-10",
  "total_items": 42,
  "status_breakdown": {
    "DONE": 8,
    "IN_PROGRESS": 2,
    "IN_REVIEW": 3,
    "READY": 14,
    "DESIGN": 12,
    "BLOCKED": 3
  },
  "top_priority_candidates": [
    {
      "id": "T-TRI-01",
      "priority": 10,
      "type": "Task",
      "status": "READY",
      "estimated_effort": "M",
      "title": "Design triage heuristics (secret, PII, pref, decision)"
    },
    {
      "id": "T-TRI-02",
      "priority": 9,
      "type": "Task",
      "status": "READY",
      "estimated_effort": "M",
      "title": "Implement triage heuristics module"
    },
    {
      "id": "T-CAP-01",
      "priority": 8,
      "type": "Task",
      "status": "READY",
      "estimated_effort": "S",
      "title": "Integrate triage into CaptureService"
    },
    {
      "id": "T-TEST-01",
      "priority": 8,
      "type": "Task",
      "status": "READY",
      "estimated_effort": "M",
      "title": "Add triage unit tests (patterns, edge cases)"
    },
    {
      "id": "T-DOC-01",
      "priority": 5,
      "type": "Chore",
      "status": "DESIGN",
      "estimated_effort": "S",
      "title": "Document triage heuristics API"
    }
  ],
  "selection_summary": {
    "selected_count": 5,
    "total_effort_hours": 51,
    "team_capacity_hours": 54,
    "utilization_percent": 94,
    "critical_path_length": 3
  }
}
```

---

## Shrnutí: Od backlog-scan do Sprint Plan

```
backlog-scan.json
    ↓
fabric-sprint reads top_priority_candidates[]
    ↓
Effort estimation per task
    ↓
Dependency extraction & topological sort
    ↓
Risk assessment (HIGH/MEDIUM/LOW)
    ↓
Anti-pattern detection
    ↓
Pre-sprint gate validation
    ├─ Capacity ≤ 90%? ✓
    ├─ No cycles? ✓
    ├─ All estimates? ✓
    └─ DoD complete? ✓
    ↓
Definition of Done (checklist)
    ↓
Capacity planning table (per-dev allocation)
    ↓
Rollover tracking (from previous sprint)
    ↓
Sprint plan YAML file created
    ├─ Sprint Targets table
    ├─ Dependency Graph
    ├─ Risk Assessment
    ├─ Capacity Plan
    ├─ Definition of Done
    └─ Task Queue (topologically ordered)
    ↓
Update state.md (sprint_started, sprint_ends, sprint_goal)
    ↓
Create report (summary, findings, warnings)
    ↓
Log END event to protocol
```

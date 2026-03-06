# fabric-vision — Příklady s reálnými daty (LLMem)

## Kompletní příklad — LLMem Vision Analysis Report

**File:** `{WORK_ROOT}/reports/vision-2026-03-06.md`

```yaml
---
schema: fabric.report.v1
kind: vision
version: "1.0"
run_id: "vision-2026-03-06-a1b2c3d4"
created_at: "2026-03-06T09:00:00Z"
status: "PASS"
---

# LLMem Vision Analysis Report — 2026-03-06

## Executive Summary

Vision is clear and measurable: Local-first memory infrastructure for agents with fail-open deployment. Principles well-defined (event-sourced, deterministic, replaceable). Success metrics are specific (latency <100ms by Q2, 70% docstring coverage). Assessment: **REALISTIC** with **PASS** on quality gates. No conflicts detected between core vision and sub-visions.

## Extracted Artifacts

### Purpose/Mission

LLMem is a local-first long-term memory infrastructure for AI agents. Captures observations from agent runtimes, triages them using deterministic heuristics (no LLM in hot path), and provides a recall API returning budgeted XML injection blocks.

### Pillars (3 total)

1. **Core Memory System** — Storage, triaging, recall; event-sourced, deterministic
2. **Integration & Operations** — Deployability, monitoring, health checks
3. **Extensibility** — Pluggable backends, custom patterns, modular design

### Goals by Pillar

#### Pillar 1: Core Memory System (5 goals)
- Event-sourced JSONL log as source of truth for observability (✓ implemented)
- Deterministic IDs from content_hash for idempotency (✓ implemented)
- Masked secrets, hashed PII in storage (✓ implemented)
- Sub-100ms recall latency for 95% queries by Q2 2026
- Support for 2+ backend implementations (InMemory, Qdrant)

#### Pillar 2: Integration & Operations (4 goals)
- Docker + systemd deployment ready by Q1 2026
- Structured JSON logging + request tracing
- Admin API for memory inspection + deletion
- Health endpoint returning service status + version

#### Pillar 3: Extensibility (3 goals)
- Pluggable embedder interface (not just hash-based)
- Custom triage patterns (regex-based, extensible)
- Backend interface: new backends without code fork

### Principles (4 total)

1. **Deterministic** — Reproducible results across rebuilds; UUIDs stable from content_hash
2. **Fail-open** — Memory system optional; errors log warnings, never block agent
3. **Local-first** — All data persisted locally; optional cloud sync only in roadmap
4. **No LLM in hot path** — Triage uses regex patterns, not language models

### Non-Goals (3 total)

1. **NOT: Real-time collaborative editing** (too complex for MVP; revisit Q3 if agent demand grows)
2. **NOT: Semantic search using embeddings** (Phase 2; MVP uses hash-based matching + deterministic order)
3. **NOT: Multi-tenant isolation** (single agent per instance; revisit Q4 if co-hosting needed)

### Success Metrics (4 total, 75% measurable)

1. Recall latency <100ms for 95th percentile of queries by Q2 2026
2. Docstring coverage ≥70% across public API by end of Q1 2026
3. Support 2+ production-grade backends (Qdrant + compatible alternative)
4. Fail-open design: zero blocking errors in production; all errors logged + recoverable

## Quality Gate Assessment

### Structural Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Principles ≥3 | ✓ PASS | Found 4 principles |
| Goals ≥1 | ✓ PASS | Found 12 goals (5+4+3 across pillars) |
| Non-goals ≥1 | ✓ PASS | Found 3 non-goals with reasoning |
| Constraints ≥1 | ✓ PASS | Found 2 constraints (latency <500ms, max 1GB memory) |

**Structural Score: 4/4** ✓

### Metrics Quality

**3/4 metrics are measurable + time-bound:**

- ✓ GOOD: "Recall latency <100ms for 95th percentile of queries by Q2 2026"
  - Measurement: milliseconds
  - Quantile: 95th percentile (realistic)
  - Deadline: Q2 2026

- ✓ GOOD: "Docstring coverage ≥70% across public API by end of Q1 2026"
  - Measurement: percentage (70%)
  - Scope: public API (clear)
  - Deadline: Q1 2026

- ✓ GOOD: "Support 2+ production-grade backends (Qdrant + compatible alternative)"
  - Measurement: count (2+)
  - Scope: production-grade (defined)

- ⚠ WEAK: "Fail-open design: zero blocking errors in production"
  - Issue: "zero" is hard to verify empirically
  - Suggestion: "≥99.9% error recovery rate; ≤1 unrecoverable error per 10,000 events"

**Metrics Quality: 75% (3/4 good)** — Exceeds minimum 50% threshold ✓

### Non-Goals Reasoning

**3/3 non-goals have explicit reasoning:**

All three include parenthetical rationale:
- "too complex for MVP" (complexity argument)
- "Phase 2" (timeline argument)
- "revisit Q3" (future planning indicator)

**Non-Goals Reasoning: 100%** ✓

### Constraints Evidence

**2/2 constraints are measurable + reasoned:**

1. "Latency <500ms for worst-case query due to agent timeout sensitivity"
   - Measurement: milliseconds (500ms)
   - Rationale: agent timeout sensitivity (explicit reasoning)

2. "Memory ≤1GB per instance due to embedded device cost constraint"
   - Measurement: gigabytes (1GB)
   - Rationale: embedded cost constraint (explicit reasoning)

**Constraints Evidence: 100%** ✓

**Quality Gate Verdict: PASS ✓** — All sections present, 75% metrics concrete, 100% non-goals reasoned, 100% constraints evidence-based. Structural Score 4/4.

## Vision Realism Assessment

- **Pillar count:** 3 (target: ≤7) → ✓ OK
- **Max goals per pillar:** 5 (target: ≤10) → ✓ OK
- **Conflicting goals:** None detected (local-first not contradicted by any pillar) → ✓ None
- **Timeline estimate:** ~12 total goals → ~3 epics per sprint → ~4 sprints (~8-10 weeks) → ✓ OK

**Realism Verdict: REALISTIC** ✓

---

## Per-Pillar Assessment

| Pilíř | Total Goals | Backlog Coverage | DONE Items | Coverage % | Implementation % | Last Activity | Drift | Verdict |
|-------|---|---|---|---|---|---|---|---|
| Core Memory System | 5 | 5 | 3 | 100% | 60% | 1 day ago | LOW | ON_TRACK |
| Integration & Operations | 4 | 2 | 0 | 50% | 0% | 2 weeks ago | HIGH | DEVIATION |
| Extensibility | 3 | 2 | 0 | 67% | 0% | 3 weeks ago | HIGH | CAUTION |

**Overall Assessment:** 1 pillar ON_TRACK, 1 CAUTION, 1 DEVIATION

### Pillar Deep Dives

#### Pillar 1: Core Memory System — ON_TRACK

**Coverage Analysis (100%):**
- Goal 1: Event-sourced JSONL log → Backlog item: LLMEM-005 (✓)
- Goal 2: Deterministic IDs → Backlog item: LLMEM-006 (✓)
- Goal 3: Secret masking → Backlog item: LLMEM-007 (✓)
- Goal 4: Sub-100ms latency → Backlog item: LLMEM-042 (✓)
- Goal 5: 2+ backends → Backlog item: LLMEM-043 (✓)

All 5 goals have backlog items. DONE: 3 (LLMEM-005, LLMEM-006, LLMEM-007).

**Implementation %:** 60% (3 DONE out of 5 goals)

**Last Activity:** 1 day ago (LLMEM-005 merge on 2026-03-05)

**Drift:** LOW — Regular progress, completed items in last week

**Verdict:** ON_TRACK — Good coverage, clear progress, no stalled goals

#### Pillar 2: Integration & Operations — DEVIATION

**Coverage Analysis (50%):**
- Goal 1: Docker + systemd → Backlog item: LLMEM-051 (✓)
- Goal 2: JSON logging → Not in backlog (✗)
- Goal 3: Admin API → Backlog item: LLMEM-052 (✓)
- Goal 4: Health endpoint → Not in backlog (✗)

Only 2/4 goals have backlog coverage. DONE: 0.

**Implementation %:** 0% (0 DONE out of 4 goals)

**Last Activity:** 2 weeks ago (LLMEM-051 created on 2026-02-20, not started)

**Drift:** HIGH — No progress in 14 days; items not yet started

**Verdict:** DEVIATION — Low coverage, no implementation, stalled items

**Mitigation required:** Prioritize LLMEM-051 and LLMEM-052 in next sprint. Create intake for missing Goals 2 & 4.

#### Pillar 3: Extensibility — CAUTION

**Coverage Analysis (67%):**
- Goal 1: Pluggable embedder → Backlog item: LLMEM-061 (✓)
- Goal 2: Custom triage patterns → Backlog item: LLMEM-062 (✓)
- Goal 3: Backend interface → Not in backlog (✗)

2/3 goals covered. DONE: 0.

**Implementation %:** 0% (0 DONE out of 3 goals)

**Last Activity:** 3 weeks ago (LLMEM-061 created on 2026-02-13, not yet started)

**Drift:** HIGH — No progress; goals created but not started

**Verdict:** CAUTION — Reasonable coverage, but delayed start; watch for further stall

**Mitigation required:** Start LLMEM-061 within next 3 days. Add Goal 3 (Backend interface) to backlog.

---

## Sub-Vision Alignment

### Identified Sub-Visions

- `{VISIONS_ROOT}/storage-backends.md` → Develops: Pillar 1 (Core Memory System)
  - Covers: InMemoryBackend, QdrantBackend design; performance trade-offs; testing

- `{VISIONS_ROOT}/determinism-and-reproducibility.md` → Develops: Pillar 1 (Core Memory System)
  - Covers: UUIDv7 from content_hash; event-sourcing guarantees; rebuild process

- `{VISIONS_ROOT}/security-policy.md` → Develops: Pillar 1 (Core Memory System) + Pillar 2
  - Covers: Secret masking, PII hashing, allow_secrets gating; audit logging

- `{VISIONS_ROOT}/roadmap.md` → Develops: All pillars (high-level timeline)
  - Covers: T0 (MVP), T1 (Production), T2 (Extensibility) phases; quarterly goals

### Conflict Detection

**No conflicts detected** between core vision and sub-visions.

- Sub-vision storage-backends.md emphasizes "deterministic backends" → Aligns with core principle "Deterministic" ✓
- Sub-vision security-policy.md emphasizes "fail-open error recovery" → Aligns with core principle "Fail-open" ✓
- Sub-vision roadmap.md emphasizes "local-first MVP, optional cloud later" → Aligns with core principle "Local-first" ✓

**Sub-vision keyword analysis:**
- Core keywords: deterministic, fail-open, local-first, heuristics, reproducible
- All sub-visions use aligned keywords; no contradictions detected

### Orphaned Artifacts

**Pillars without sub-visions:**
- None — All 3 core pillars are developed by sub-visions

**Sub-visions without core reference:**
- None — All sub-visions are referenced from vision.md with explicit links

---

## Top 5 Risks & Gaps

1. **Risk: Pillar 2 (Integration & Ops) DEVIATION for 2+ weeks**
   - Impact: Operations team lacks deployment guidance; no health monitoring
   - Mitigation: Prioritize LLMEM-051 (Docker) + LLMEM-052 (Admin API) in sprint starting 2026-03-10. Assign ops engineer. Schedule design review by 2026-03-08.
   - Owner: DevOps Lead
   - Target: ON_TRACK status by 2026-04-01

2. **Risk: Qdrant backend integration not yet started (Goal 5)**
   - Impact: Single-backend lock-in; can't validate "2+ backends" success metric by Q2
   - Mitigation: Spike task LLMEM-043 should start by 2026-03-17 (within 2 weeks). Define Qdrant schema + indexing strategy in parallel with InMemory completion.
   - Owner: Core Team
   - Target: Qdrant prototype by end of Q1 2026

3. **Gap: Missing Goal (Integration & Ops) — Structured JSON logging**
   - Impact: No observability; debugging production issues becomes blind
   - Mitigation: Create backlog item for JSON logging middleware. Scope: ≤8h. Add to sprint 2026-03-10.
   - Owner: Ops Team
   - Target: In sprint by 2026-03-10

4. **Gap: Missing Goal (Integration & Ops) — Health endpoint**
   - Impact: Container orchestration (K8s, systemd) can't auto-restart stale instances
   - Mitigation: Create backlog item for /healthz endpoint. Scope: ≤4h. Bundle with LLMEM-051 (Docker task).
   - Owner: DevOps
   - Target: In sprint by 2026-03-10

5. **Risk: "Fail-open" metric is qualitative (zero blocking errors)**
   - Impact: Success metric not empirically verifiable; hard to validate at production scale
   - Mitigation: Refine metric to "≥99.9% error recovery rate; log all errors; maintain agent continuity". Add test case: inject 1000 malformed events, verify <1 recovery failure.
   - Owner: Core Team
   - Target: Metric refinement by 2026-03-13

---

## Backlog Implications & Priorities

Based on this vision analysis, recommended backlog priorities (for next 2 sprints):

### Sprint 1 (2026-03-10 to 2026-03-24) — IMMEDIATE

1. **LLMEM-051: Docker + systemd deployment** — Reason: Pillar 2 high drift; needed for health checks
2. **LLMEM-042: Sub-100ms recall latency** — Reason: Q2 critical metric; must start performance testing
3. **LLMEM-052: Admin API** — Reason: Ops visibility; supports Pillar 2 recovery
4. **Intake: Missing Goal — JSON Logging** — Reason: Ops observability gap; unblock LLMEM-051
5. **Intake: Missing Goal — Health Endpoint** — Reason: Container orchestration dependency; pair with LLMEM-051

### Sprint 2 (2026-03-25 to 2026-04-07) — FOLLOW-UP

6. **LLMEM-043: Qdrant backend prototype** — Reason: Multi-backend success metric (Q2 deadline)
7. **LLMEM-061: Pluggable embedder interface** — Reason: Pillar 3 extensibility; unblock later semantic search
8. **LLMEM-062: Custom triage patterns** — Reason: Pillar 3 goal; enables user-defined rules

---

## Intake Items Generated

### 1. vision-improve-201

**Status:** Created 2026-03-06
**Reason:** Pillar 2 (Integration & Ops) has 2 goals not yet in backlog

```md
---
schema: fabric.intake_item.v1
title: "Add missing Integration & Ops goals to backlog"
source: fabric-vision
initial_type: Task
raw_priority: 8
status: new
linked_vision_goal: "Pillar 2: Integration & Ops"
created: 2026-03-06
---

## Problem
Vision defines 4 goals for Pillar 2 (Integration & Ops), but only 2 have backlog items:
- ✓ Goal 1: Docker + systemd → LLMEM-051
- ✗ Goal 2: JSON logging → MISSING
- ✓ Goal 3: Admin API → LLMEM-052
- ✗ Goal 4: Health endpoint → MISSING

## Required Actions
1. Create backlog item: "Implement structured JSON logging middleware"
   - Scope: ≤8h
   - Acceptance: All requests logged as JSON; includes timestamp, request_id, endpoint, status

2. Create backlog item: "Implement /healthz health check endpoint"
   - Scope: ≤4h
   - Acceptance: GET /healthz returns 200 OK + JSON: {status, version, uptime_seconds}

## Acceptance Criteria
- [ ] Both items created in backlog/
- [ ] Both linked to Pillar 2
- [ ] Both scheduled for sprint starting 2026-03-10
```

### 2. vision-improve-202

**Status:** Created 2026-03-06
**Reason:** Success metric "zero blocking errors" is not quantitative

```md
---
schema: fabric.intake_item.v1
title: "Quantify fail-open error recovery metric"
source: fabric-vision
initial_type: Chore
raw_priority: 6
status: new
linked_vision_goal: "Success Metrics"
created: 2026-03-06
---

## Problem
Current metric: "Fail-open design: zero blocking errors in production"

Issues:
- "Zero" is unverifiable at scale
- No clear definition of "blocking" vs "recoverable"
- No test strategy to validate claim

## Required Actions
1. Refine metric to: "≥99.9% error recovery rate; zero unrecoverable errors in 10,000+ event batch"
   - Definition: Unrecoverable = error that halts agent callback

2. Add test case:
   - Inject 10,000 events: 99% good, 1% malformed
   - Verify: All 10,000 events processed; agent never halted; all errors logged

3. Update vision.md with new metric

## Acceptance Criteria
- [ ] Metric refined and quantified
- [ ] Test case written and passing
- [ ] vision.md updated
```

---

## Downstream Contract Verification

✓ **fabric-gap** can read from this report:
- `Per-Pillar Assessment` table has all required columns: Coverage %, Implementation %, Done Items
- `Top 5 Risks & Gaps` section is populated with 5 specific risks
- `Vision Realism Verdict` is REALISTIC (not UNREALISTIC)

✓ **fabric-sprint** can read from this report:
- `Per-Pillar Assessment.Verdict` column has values: ON_TRACK, CAUTION, DEVIATION
- `Success Metrics` section has deadline field: "by Q2 2026", "by end of Q1 2026"
- Pillar ordering is implicit: Core (highest priority), Ops (highest drift), Extensibility (lower priority)

---

**Generated:** 2026-03-06T09:00:00Z
**Status:** PASS (All quality gates passed; no critical blockers)
```

---

## Example 2: Vision Report with FAILURES (Intake generation example)

This example shows what a report looks like when quality gates FAIL, triggering intake item generation.

### Scenario: Incomplete vision with vague metrics

**File:** `{WORK_ROOT}/reports/vision-2026-03-05-bad.md`

```yaml
---
schema: fabric.report.v1
kind: vision
version: "1.0"
run_id: "vision-2026-03-05-x9y8z7"
created_at: "2026-03-05T10:00:00Z"
status: "FAIL"
---

# Vision Analysis Report — 2026-03-05 (INCOMPLETE)

## Executive Summary

Vision is incomplete: Missing explicit Constraints section. Metrics are largely qualitative without numbers or deadlines. Non-goals lack reasoning. Assessment: **UNREALISTIC** — scope too broad without phased approach. Quality gate FAIL.

## Quality Gate Assessment

### Structural Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Principles ≥3 | ⚠ FAIL | Found 2 principles (need ≥3) |
| Goals ≥1 | ✓ PASS | Found 8 goals |
| Non-goals ≥1 | ✓ PASS | Found 2 non-goals (but no reasoning) |
| Constraints ≥1 | ✗ FAIL | Found 0 constraints |

**Structural Score: 2/4** ✗ FAIL

### Metrics Quality

**0/5 metrics are measurable + time-bound:**

- ⚠ WEAK: "Improve latency" (no number, no deadline)
- ⚠ WEAK: "Better user experience" (qualitative)
- ⚠ WEAK: "Enhance security" (abstract)
- ⚠ WEAK: "Scalable deployment" (no target, no deadline)
- ⚠ WEAK: "100% test coverage" (deadline missing; unclear scope)

**Metrics Quality: 0% (0/5 good)** ✗ FAIL

### Non-Goals Reasoning

**0/2 non-goals have explicit reasoning:**

- ⚠ WEAK: "NOT: Advanced features" (no reason)
- ⚠ WEAK: "NOT: Mobile app" (no reason)

**Non-Goals Reasoning: 0%** ✗ FAIL

### Constraints Evidence

**0/0 constraints** (none found) ✗ FAIL

**Quality Gate Verdict: FAIL ✗** — Structural score 2/4 (missing Principles, Constraints). 0% metrics quantified. 0% non-goals reasoned. UNREALISTIC scope.

## Vision Realism Assessment

- **Pillar count:** 9 (target: ≤7) → ⚠ HIGH RISK
- **Max goals per pillar:** 3-7 goals per pillar → ✓ OK
- **Conflicting goals:** "Lightweight + enterprise-grade" detected → ✗ CONFLICT
- **Timeline estimate:** ~50+ goals → ~12-15 epics → ~18-20 sprints (>12 month warning) → ⚠ RISKY

**Realism Verdict: UNREALISTIC** ✗ — Too many pillars (9 vs. target ≤7); conflicting goals (lightweight vs. enterprise); timeline >12 sprints.

## Per-Pillar Assessment

| Pilíř | Total Goals | Backlog Coverage | DONE Items | Coverage % | Implementation % | Drift | Verdict |
|-------|---|---|---|---|---|---|---|
| System Core | 6 | 2 | 0 | 33% | 0% | HIGH | DEVIATION |
| UI/UX | 4 | 1 | 0 | 25% | 0% | HIGH | DEVIATION |
| Analytics | 5 | 0 | 0 | 0% | 0% | N/A | DEVIATION |
| ... (6 more pillars) | ... | ... | ... | ... | ... | ... | ... |

---

## Intake Items Generated

### intake/vision-improve-critical-1

```md
---
schema: fabric.intake_item.v1
title: "CRITICAL: Reduce vision scope and add missing sections"
source: fabric-vision
initial_type: Task
raw_priority: 10
status: new
created: 2026-03-05
---

## Problem

Vision fails 4/4 quality gates and is UNREALISTIC:

1. **Structural deficiency:**
   - Missing: ≥3 Principles (found 2)
   - Missing: Constraints section (found 0)

2. **Metrics are 100% vague:**
   - "Improve latency" → Need: "<100ms by Q2 2026"
   - "Better UX" → Need: "Measure via user satisfaction ≥4/5 by Q1"
   - All 5 metrics lack numbers + deadlines

3. **Non-goals lack reasoning:**
   - "NOT: Advanced features" → Need: "too complex for MVP (revisit Q2)"
   - "NOT: Mobile app" → Need: "not on roadmap; out-of-scope for first 2 years"

4. **Scope is unrealistic:**
   - 9 pillars detected (target: ≤7)
   - 50+ total goals (timeline: >18 sprints vs. target <12)
   - Conflict: "lightweight" vs. "enterprise-grade"

## Required Actions

### Phase 1: Scope & Priorities (by 2026-03-12)

1. Reduce to ≤7 pillars by:
   - Merging similar pillars (e.g., "UI/UX" + "Accessibility" → "User Experience")
   - Moving stretch pillars to "Future Roadmap" (Phase 2)

2. Resolve conflict "lightweight vs. enterprise":
   - Choose: MVP is lightweight (enterprise deferred to Phase 2)
   - OR: Define tiers (basic lightweight, enterprise paid)
   - Document decision in Principles section

### Phase 2: Add Missing Sections (by 2026-03-15)

1. **Principles section:** Add ≥3 core principles
   - Example: "Fail-open design" "Local-first" "User control"

2. **Constraints section:** Add ≥1 constraint with evidence
   - Example: "Latency <500ms (user timeout expectations)"
   - Example: "Memory <1GB (embedded deployment constraint)"

### Phase 3: Quantify Metrics (by 2026-03-20)

For each metric, ensure: number + unit + deadline

- "Improve latency" → "Recall latency <100ms for 95% queries by Q2 2026"
- "Better UX" → "User satisfaction ≥4/5 (Likert scale) by end of Q1 2026"
- "Enhance security" → "Zero unpatched CVEs in dependencies by Q1; audit trail for all PII access"
- "Scalable" → "Support 100k+ events/day per instance with <10% latency increase"
- "Test coverage" → "≥70% coverage on public API; ≥90% on triage logic"

### Phase 4: Reasoning for Non-Goals (by 2026-03-20)

For each non-goal, add parenthetical reason:

- "NOT: Advanced features" → "(too complex for MVP; focus on core reliability first; revisit Q2)"
- "NOT: Mobile app" → "(not on roadmap; out-of-scope for first 2 years; revisit if API demand warrants)"

## Acceptance Criteria

- [ ] Pillar count ≤7
- [ ] No conflicting goals (lightweight vs. enterprise resolved)
- [ ] Timeline estimate <12 sprints
- [ ] Structural score ≥3/4 (Principles + Constraints added)
- [ ] 100% of metrics quantified (number + deadline)
- [ ] 100% of non-goals have reasoning
- [ ] Re-run fabric-vision; report status should be PASS

## Success Metric

Vision analysis report shows:
- Status: PASS
- Quality Gate Verdict: PASS ✓
- Realism Verdict: REALISTIC
```

---

## Example 3: Conflict Detection Output

### Scenario: Core vision conflicts with sub-vision

**Core vision.md:**
```md
## Principles
- Local-first: All data stored locally; optional cloud sync only in roadmap
- Deterministic: Reproducible across rebuilds; UUIDs from content_hash
```

**Sub-vision: {VISIONS_ROOT}/scalability.md:**
```md
## Goals
- Support cloud-native deployment with multi-region replication
- Implement eventual consistency across cloud zones
- Enable real-time sync to central analytics service
```

**Conflict detection bash output:**
```
CRITICAL CONFLICT in scalability.md:
  Core principle: "Local-first" emphasizes local persistence
  Sub-vision goal: "cloud-native deployment" + "multi-region replication"

  → Recommendation: Either (a) move cloud goals to "Future Roadmap" section,
    or (b) clarify "Local-first MVP + Optional cloud extension"
```

**Intake item generated:**
```md
---
title: "Resolve core vision vs. scalability sub-vision conflict"
source: fabric-vision
initial_type: Task
raw_priority: 9
---

## Problem
Core vision emphasizes "Local-first", but sub-vision/scalability.md lists "cloud-native deployment" as a goal. These conflict.

## Resolution Options

Option A: Move cloud goals to Phase 2
- Update sub-vision/scalability.md: Move multi-region/central-sync goals to "Future Phase 2"
- Keep MVP as local-first
- Add timeline: "Cloud extension planned for Q3 2026"

Option B: Clarify tiered approach
- Update core vision Principles: "Local-first MVP with optional cloud extension for enterprise tier"
- Update sub-vision/scalability.md: "Phase 1 local deployment, Phase 2 optional cloud replication"
- Both approaches supported; default is local-first

## Acceptance Criteria
- [ ] One option chosen
- [ ] vision.md + sub-vision updated to reflect choice
- [ ] No conflicting keywords remain (re-run conflict detection)
```

---

## Summary: When to Generate Intake Items

| Condition | Severity | Intake Type | Priority |
|-----------|----------|------------|----------|
| STRUCTURAL_SCORE < 4 | HIGH | Task (add missing sections) | 9-10 |
| METRICS < 50% measurable | HIGH | Task (quantify metrics) | 8-9 |
| NON_GOALS < 50% reasoned | MEDIUM | Chore (add reasoning) | 6-7 |
| CONFLICT detected | CRITICAL | Task (resolve conflict) | 9-10 |
| UNREALISTIC verdict | HIGH | Task (reduce scope) | 9-10 |
| ANY pillar DEVIATION for 3+ sprints | MEDIUM | Task (investigate/recover) | 7-8 |
| Missing sub-vision for pillar | LOW | Task (create sub-vision) | 5-6 |

All CRITICAL/HIGH items should block sprint planning until addressed.

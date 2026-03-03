---
# Technical Specification (SPEC)
# Lightweight but enforceable contract for implementation.
# Statuses: draft, active, deprecated, superseded

id: "SPEC-{NNN}"
schema: fabric.spec.v1
title: "{SPEC_TITLE}"
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"

# draft -> active -> (deprecated | superseded)
status: "draft"

owners: ["{AUTHOR_NAME_OR_AGENT}"]

# Link to ADRs that constrain this spec (optional but recommended)
decisions: ["{ADR-0000_OR_EMPTY}"]

# If this spec supersedes another spec, link it here (optional)
supersedes: "{SPEC-0000_OR_EMPTY}"
superseded_by: "{SPEC-0000_OR_EMPTY}"

# Scope hint (optional): project | service | module | library | infra
scope: "{SCOPE_OR_EMPTY}"
---

# {SPEC_TITLE}

## Purpose
{PURPOSE}

## Non-goals
- {NON_GOAL_1}
- {NON_GOAL_2}

## Requirements
- {REQUIREMENT_1}
- {REQUIREMENT_2}

## Constraints
> Explicitly list which **Decisions (ADR)** and **Specs** constrain this work.

- Decisions: {ADR_LIST}
- Specs: {SPEC_LIST}
- Hard constraints (security/compliance/perf/latency/cost): {HARD_CONSTRAINTS}

## Design
### High-level approach
{HIGH_LEVEL_APPROACH}

### Interfaces / API
{API_AND_CONTRACTS}

### Data model
{DATA_MODEL}

### Failure modes & retries
{FAILURE_MODES}

## Acceptance criteria
- [ ] {AC_1}
- [ ] {AC_2}

## Testing strategy
- Unit: {UNIT_TESTS}
- Integration: {INTEGRATION_TESTS}
- E2E: {E2E_TESTS_OR_EMPTY}

## Observability
- Logs: {LOGS}
- Metrics: {METRICS}
- Traces: {TRACES}

## Security & privacy
{SECURITY_CONSIDERATIONS}

## Rollout / migration
{ROLLOUT_PLAN}

## Open questions
- {OPEN_QUESTION_1}
- {OPEN_QUESTION_2}

## References
- {LINK_1}
- {LINK_2}

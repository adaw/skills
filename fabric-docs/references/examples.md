# fabric-docs — Příklady a šablony

Realistické příklady z LLMem projektu a ostatních domén.

---

## Příklad 1: Kompletní docs sync report (LLMem)

```markdown
---
schema: fabric.report.v1
kind: docs
run_id: "docs-2026-03-06-xyz789"
created_at: "2026-03-06T15:45:00Z"
status: PASS
version: "1.0"
---

# docs — Report 2026-03-06

## Souhrn
Zpracováno 8 merged items: 5 MUST_DOCUMENT + 3 SHOULD_DOCUMENT. Aktualizováno 6 dokumentačních souborů. ADR-005 vytvořen pro nový recall scoring. Docstring coverage 87% (target: ≥80%).

## Merged items
| ID | Title | Classification | Files Changed | Updated Docs |
|----|-------|-----------------|----------------|--------------|
| ITEM-42 | Add /recall endpoint with budgeting | MUST_DOCUMENT | src/llmem/api/routes/recall.py (78 lines) | docs/api/recall.md |
| ITEM-43 | Add tombstone soft-delete method | MUST_DOCUMENT | src/llmem/services/memory.py (42 lines) | docs/api/memory.md |
| ITEM-44 | Support budget_tokens parameter | MUST_DOCUMENT | src/llmem/api/routes/recall.py (12 lines) | docs/api/recall.md |
| ITEM-45 | Refactor score combine logic | SHOULD_DOCUMENT | src/llmem/recall/scoring.py (120 lines) | docs/architecture/recall-pipeline.md |
| ITEM-46 | Fix edge case in cosine similarity | SHOULD_DOCUMENT | src/llmem/embeddings/hash.py (8 lines) | — |
| ITEM-47 | Add retry logic to storage backend | SHOULD_DOCUMENT | src/llmem/storage/backends.py (45 lines) | docs/deployment/reliability.md |
| ITEM-48 | Lint formatting cleanup | SKIP | tests/, src/ (formatting only) | — |
| ITEM-49 | Update README with new features | MUST_DOCUMENT | README.md, docs/quickstart.md | docs/quickstart.md |

## API Surface Delta

### New Endpoints
- **POST /memories/{instance_id}** — Create memory directly (replaces internal triage-only path)
  - Parameters: content (string), memory_type (MemoryType), sensitivity (Sensitivity)
  - Response: {memory_id, created_at}

- **POST /memories/{instance_id}/{memory_id}/tombstone** — Soft-delete memory
  - Preserves audit trail, doesn't hard-delete
  - Response: {memory_id, tombstoned_at}

### Changed Endpoints
- **GET /recall** — Added budget_tokens parameter
  - Old: `GET /recall?query=...&scope=...` (budget hardcoded)
  - New: `GET /recall?query=...&scope=...&budget_tokens=2000` (customizable)
  - Backward compatible (default: 2000)

### Removed Endpoints
- N/A (no breaking removals this sprint)

### Deprecated (but still functional)
- `POST /quick-recall` — Use `/recall` with budget_tokens instead (EOL: 2026-05-01)

## Updated Files

| File | Change | Code Reference | Status |
|------|--------|-----------------|--------|
| docs/api/recall.md | Added /recall endpoint spec, budget_tokens param | src/llmem/api/routes/recall.py:L42-L78 | ✓ |
| docs/api/memory.md | Added POST /memories and tombstone endpoint | src/llmem/services/memory.py:L120-L165 | ✓ |
| docs/architecture/recall-pipeline.md | Updated scoring logic with new combine_score signature | src/llmem/recall/scoring.py:L15-L52 | ✓ |
| docs/deployment/reliability.md | Added retry logic for Qdrant backend | src/llmem/storage/backends.py:L200-L245 | ✓ |
| docs/quickstart.md | Added examples for new endpoints | README.md:L50-L120 | ✓ |
| CHANGELOG.md | [Unreleased] entries added | — | ✓ |

## Docstring Quality Distribution
| Quality | Count | % | Target | Status |
|---------|-------|---|--------|--------|
| GOOD (2pts) | 32 | 68% | ≥60% | ✓ PASS |
| ACCEPTABLE (1pt) | 12 | 25% | ≥30% | ✓ PASS |
| BAD (0pts) | 3 | 7% | ≤10% | ✓ PASS |
| **Average Score** | — | **163%** | **≥150%** | **✓ PASS** |

## Documentation Coverage (by module)
| Module | Public Items | Documented | Coverage | Status |
|--------|--------------|-------------|----------|--------|
| llmem.api.routes | 8 | 8 | 100% | ✓ |
| llmem.services | 12 | 11 | 92% | ✓ |
| llmem.triage | 6 | 5 | 83% | ⚠️ WARN |
| llmem.storage | 10 | 10 | 100% | ✓ |
| llmem.embeddings | 4 | 4 | 100% | ✓ |
| **TOTAL** | **40** | **38** | **95%** | **✓ PASS** |

## Validation Results
- ✓ Broken markdown links: 0
- ✓ Orphaned doc files: 0
- ✓ Code examples with syntax errors: 0
- ✓ API docs vs code mismatches: 0
- ⚠️ Undocumented public items: 1 (llmem.triage.utils._private_helper — acceptable as private)

## Coverage Check
- Docstring coverage: 95% (target: ≥80%) — **PASS**
- README.md: Updated for new API — **OK**
- CHANGELOG.md: [Unreleased] entries added — **OK**
- API endpoint coverage: 100% — **PASS**

## ADR
- **ADR-005: New Recall Scoring Mechanism** — Status: Accepted
  - File: docs/adr/0005-recall-scoring.md
  - Decision: Use three-tier boosting (tier_boost + scope_boost + recency_boost) for recall ranking
  - Rationale: Deterministic, no LLM in hot path, measurable weights
  - Consequences: Requires tuning of boost weights per use case (future work)

## TODO
- ITEM-46 (cosine edge case): Document in docs/deployment/performance.md once benchmark is ready (blocking on ITEM-50)
- Update docs/api/memory.md with tombstone lifecycle diagram (nice-to-have)

## Checklist
- [x] All MUST_DOCUMENT items have updated docs (5/5)
- [x] Code examples validated for syntax (3 examples, all valid Python)
- [x] Broken links checked (0 broken, 2 redirects fixed)
- [x] Docstring quality scored (95% ≥80% target)
- [x] API coverage ≥80% (100%)
- [x] CHANGELOG updated (5 entries in [Unreleased])
- [x] ADR created and validated (ADR-005 complete)
- [x] All doc changes have code references (40/40 checked)
```

---

## Příklad 2: CHANGELOG entry (Keep a Changelog)

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New memory recall endpoint with budgeted XML injection ([ITEM-42](https://github.com/anthropic-labs/llmem/issues/42))
  - POST /memories/{instance_id} — Create memory directly
  - POST /memories/{instance_id}/{memory_id}/tombstone — Soft-delete with audit trail
- Configuration option for secret sensitivity gating on recall
  - Environment variable: `LLMEM_ALLOW_SECRETS` (default: false)
- Python 3.12 support (tested in CI)

### Changed
- GET /recall now accepts optional `budget_tokens` parameter
  - Backward compatible (default: 2000 tokens)
  - Enables fine-grained control of recall size
- Refactored recall scoring to use deterministic three-tier boosting ([ADR-005](./docs/adr/0005-recall-scoring.md))
  - tier_boost: 1.5x for higher memory tiers
  - scope_boost: 1.2x for matching scope
  - recency_boost: computed from days since creation

### Fixed
- Edge case in cosine similarity scoring for zero-vector embeddings
  - Previously returned NaN, now correctly handled as 0.0
- Storage backend retry logic for transient Qdrant connection errors
  - Max 3 retries with exponential backoff (100ms → 400ms)

### Removed
- Quick-recall /quick_recall endpoint (deprecated in v0.1.0)
  - Migrate to `/recall?budget_tokens=1000` for similar behavior
  - Final removal: 2026-05-01

### Deprecated
- InMemoryBackend for production (use QdrantBackend instead)
  - InMemoryBackend retained for testing only
  - Warning added to logs if used outside test mode

## [0.2.0] — 2026-03-01

### Added
- Initial Qdrant HNSW vector store backend
- Persistent event-sourced JSONL log for all observations
- Deterministic UUIDv7 IDs based on content hash
- Secret masking in non-secret memory tiers

### Changed
- `capture_event()` signature: added `instance_id` parameter

### Fixed
- Memory deduplication accuracy improved from 87% to 94%

---

## §Notes

- Each version section should have: Added, Changed, Fixed, Removed, Deprecated (if applicable)
- Keep [Unreleased] at the top for ongoing work
- Use semantic versioning: MAJOR.MINOR.PATCH
- Link to GitHub issues/PRs when available
- Group changes by significance (Added/Changed/Fixed/Removed/Deprecated)
```

---

## Příklad 3: ADR (Architecture Decision Record)

```markdown
# ADR-005: Deterministic Recall Scoring with Three-Tier Boosting

**Date:** 2026-03-05
**Status:** Accepted
**Author:** alice@example.com
**Related Issue:** [ITEM-45](https://github.com/anthropic-labs/llmem/issues/45)

## Context

The recall pipeline selects relevant memories from candidates using a scoring function. Previously, we combined cosine similarity + simple boost heuristics without clear weighting or determinism.

**Problem:**
- Score weights were implicit and hardcoded (unmaintainable)
- Scores were not deterministic across reruns (small floating-point variations)
- Tuning scores required code changes (not configurable)
- No clear ranking for memories at same relevance tier (lottery-like behavior)

**Business driver:**
- Agents need predictable, deterministic memory selection
- Different use cases need different tradeoffs (e.g., recency vs relevance)
- Transparent scoring improves explainability

## Decision

Implement deterministic scoring with three explicit boosting dimensions:

1. **Tier boost** (memory importance): multiply by 1.0–1.5 based on MemoryTier
2. **Scope boost** (query-memory alignment): multiply by 1.0–1.2 if scopes match
3. **Recency boost** (freshness): multiply by 1.0–1.1 based on age (capped at 30 days)

```
score = cosine_similarity * tier_boost * scope_boost * recency_boost
```

**Weights (configurable via env or config.md):**
- TIER_WEIGHTS: {HIGH: 1.5, MEDIUM: 1.2, LOW: 1.0}
- SCOPE_MATCH_BOOST: 1.2
- RECENCY_HALFLIFE: 7 days (boost halves after 7d)

## Rationale

**Why three tiers instead of single weighted sum?**
- Multiplicative boosting preserves rank order (unlike additive)
- Each dimension is interpretable: importance, relevance, freshness
- Easier to tune: adjust one dimension without cascading effects
- Matches human intuition: "I want important, relevant, recent memories"

**Why deterministic?**
- No floating-point variance in outputs (testable, reproducible)
- Enables caching of scores (same query → same rank)
- Simplifies debugging (no spurious randomness)
- Faster: cache hit on repeated queries

**Why not ML-based (e.g., learn weights)?**
- No LLM in hot path (critical design constraint from ADR-001)
- Deterministic = no training overhead
- Simpler to audit and explain to users

## Consequences

### Positive
- ✓ Deterministic, reproducible recall ranking
- ✓ Configurable weighting per deployment
- ✓ Transparent scoring (users see formula)
- ✓ No LLM dependency (keep hot path fast)
- ✓ Enables caching and performance optimization

### Negative
- ✗ Requires tuning weights for each domain/use case (ongoing maintenance)
- ✗ Multiplicative boosting can over-penalize low-similarity items (mitigated by bounds)
- ✗ Hard to discover optimal weights without A/B testing
- ✗ Doesn't capture complex ranking patterns (e.g., "prefer recent AND similar" is not learnable)

## Alternatives Considered

### 1. Additive weighted sum
```
score = w1*similarity + w2*tier + w3*recency
```
- Pros: Traditional, simple to implement
- Cons: Rank order can flip with different scales (similarity: 0-1, tier: 0-100), harder to tune

### 2. Learning-based (neural network)
```
score = neural_net(similarity, tier, recency, scope, age)
```
- Pros: Automatically discover optimal weights
- Cons: Violates "no LLM in hot path" (ADR-001), requires training data, harder to debug

### 3. Percentile-based boosting
```
score = similarity * (percentile_tier(tier) * percentile_recency(recency))
```
- Pros: Data-driven, adapts to distribution of memories
- Cons: Requires computing percentiles (expensive), non-deterministic if distribution changes

## Alternatives Rejected
- **Machine learning**: Violates ADR-001 (no ML in hot path)
- **Heuristic rules** (if-else chains): Unmaintainable as use cases grow

## Implementation Details

**File:** src/llmem/recall/scoring.py
**Function:** `combine_score(similarity, tier, scope, age_days)`

```python
def combine_score(
    similarity: float,
    tier: MemoryTier,
    scope_match: bool,
    age_days: int,
    config: ScoringConfig = DEFAULT_CONFIG
) -> float:
    """
    Deterministic recall scoring with three-tier boosting.

    Args:
        similarity: Cosine similarity [0.0, 1.0]
        tier: Memory importance tier (HIGH, MEDIUM, LOW)
        scope_match: Whether memory scope matches query scope
        age_days: Days since memory creation (min: 0)
        config: Scoring configuration with weights

    Returns:
        Combined score [0.0, max_boost] where max_boost = 1.5 * 1.2 * 1.1
    """
    # Tier boost
    tier_weight = config.tier_weights[tier]

    # Scope boost (binary)
    scope_boost = config.scope_match_boost if scope_match else 1.0

    # Recency boost (exponential decay)
    days_since_create = max(0, age_days)
    recency_boost = 2 ** (-days_since_create / config.recency_halflife)
    recency_boost = min(recency_boost, config.max_recency_boost)

    combined = similarity * tier_weight * scope_boost * recency_boost
    return min(combined, config.max_combined_score)  # cap at ~1.9
```

## Testing Strategy

1. **Unit tests**: Test each boost dimension independently
2. **Determinism test**: Run same query 100x, verify identical scores
3. **Regression test**: Compare output with old heuristic (on LLMem real data)
4. **Edge cases**: zero similarity, very old memories, scope mismatch

## Related ADRs

- [ADR-001: Event-Sourced Memory Storage](./0001-event-sourced.md) — "no LLM in hot path"
- [ADR-003: Deterministic IDs from Content Hash](./0003-deterministic-ids.md) — related to reproducibility

## Migration Path

No breaking changes (additive). Old code using `old_score()` continues to work.
New code should use `combine_score()` with explicit parameters.

## Future Considerations

- Dynamic weight tuning based on query performance metrics (optional follow-up)
- Per-use-case weight profiles (e.g., "RAG mode" vs "conversation mode")
- A/B testing framework for weight optimization
```

---

## Příklad 4: Dokumentační šablona pro nový endpoint

```markdown
## /recall — Budgeted Memory Retrieval

Retrieve relevant memories for a query with configurable token budget.

**Source:** [RecallService.recall()](../../src/llmem/services/recall.py#L42)
**Introduced:** ITEM-42 (2026-03-06)

### Endpoint
```
GET /recall
```

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | yes | — | Natural language query |
| `scope` | string | no | "global" | Memory scope filter (e.g., "conversation_5", "global") |
| `budget_tokens` | integer | no | 2000 | Max tokens in response (affects number of memories) |
| `tier_minimum` | MemoryTier | no | LOW | Minimum memory importance tier (HIGH, MEDIUM, LOW) |

### Request Example

```bash
curl -X GET "http://127.0.0.1:8080/recall?query=how%20do%20I%20use%20Qdrant&scope=global&budget_tokens=1500" \
  -H "Content-Type: application/json"
```

Python:
```python
import requests

response = requests.get(
    "http://127.0.0.1:8080/recall",
    params={
        "query": "how do I use Qdrant",
        "scope": "global",
        "budget_tokens": 1500,
        "tier_minimum": "HIGH"
    }
)
print(response.json())
```

### Response Format

```json
{
  "query": "how do I use Qdrant",
  "scope": "global",
  "memories_recalled": 3,
  "tokens_used": 1245,
  "injection_block": "<!-- MEMORY CONTEXT START -->\n<memories>...",
  "details": [
    {
      "memory_id": "mem_abc123",
      "content": "Qdrant is a vector database for semantic search",
      "type": "fact",
      "tier": "HIGH",
      "relevance_score": 0.92,
      "age_days": 2
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Echo of input query |
| `scope` | string | Filter scope used |
| `memories_recalled` | integer | Number of memories returned |
| `tokens_used` | integer | Actual tokens in injection block (≤ budget_tokens) |
| `injection_block` | string | XML-formatted memory context for LLM |
| `details` | array | Per-memory metadata (optional, debug mode) |

### Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Memories retrieved |
| 400 | Bad request | Invalid budget_tokens (not numeric) |
| 404 | Not found | Scope/instance not found |
| 500 | Server error | Qdrant connection failed (retrying) |

### Behavior Notes

- **Budget enforcement**: If sum of memories exceeds budget_tokens, ranks by relevance and truncates
- **Empty recall**: If query matches no memories, returns `memories_recalled: 0` with empty `injection_block` (not an error)
- **Deterministic**: Same query → same memory ranking (uses deterministic scoring from ADR-005)
- **Scope matching**: Memories are ranked higher if memory.scope == query.scope (1.2x boost)

### Error Examples

**Request:**
```
GET /recall?budget_tokens=invalid
```

**Response (400):**
```json
{
  "error": "Bad Request",
  "message": "budget_tokens must be integer, got: 'invalid'",
  "code": "INVALID_PARAMETER"
}
```

### Integration with RecallService

The `/recall` endpoint delegates to `RecallService.recall()`:

```python
# From src/llmem/api/routes/recall.py
@app.get("/recall")
async def recall_endpoint(
    query: str,
    scope: str = "global",
    budget_tokens: int = 2000,
    tier_minimum: MemoryTier = MemoryTier.LOW
) -> RecallResponse:
    service = RecallService(backend=app.storage_backend)
    return service.recall(
        query=query,
        scope=scope,
        budget_tokens=budget_tokens,
        tier_minimum=tier_minimum
    )
```

See [RecallService API](./recall-service.md) for internals.

### Related Endpoints

- [POST /memories/{instance_id}](./memory.md#post-memories) — Create memory directly
- [GET /memories/{instance_id}](./memory.md#get-memories) — List all memories (paginated)
- [POST /memories/{instance_id}/{memory_id}/tombstone](./memory.md#post-tombstone) — Soft-delete memory

### Changelog

- **2026-03-06**: Added `budget_tokens` parameter (ITEM-44, backward compatible)
- **2026-03-05**: Endpoint created (ITEM-42)
```

---

## Příklad 5: Classification decision flow (bash)

```bash
#!/bin/bash
# Classify merged items (from close report or backlog)

CLOSE_REPORT="${1:-{WORK_ROOT}/reports/close-$(date +%Y-%m-%d).md}"

echo "=== CLASSIFICATION RESULTS ===" > /tmp/classification.txt

# Extract items from close report
grep -E "^\| ITEM-|^\| TASK-" "$CLOSE_REPORT" | tail -n +2 | while IFS='|' read -r _ ITEM_ID TITLE FILES _; do
  ITEM_ID=$(echo "$ITEM_ID" | xargs)
  TITLE=$(echo "$TITLE" | xargs)
  FILES=$(echo "$FILES" | xargs)

  # Classify using decision tree
  classify_merged_item "$ITEM_ID" "$TITLE" "$FILES"
done

cat /tmp/classification.txt
```

---

## Příklad 6: Self-check integration test (bash)

```bash
#!/bin/bash
# Quick validation that report is complete (run before END)

REPORT="{WORK_ROOT}/reports/docs-$(date +%Y-%m-%d).md"

if [ ! -f "$REPORT" ]; then
  echo "❌ REPORT NOT FOUND: $REPORT"
  exit 1
fi

# Check required sections
for SECTION in "Souhrn" "Merged items" "API Surface Delta" "Updated files" "Docstring Quality" "Coverage" "Validation Results" "ADR" "TODO" "Checklist"; do
  if ! grep -q "^## $SECTION\|^### $SECTION" "$REPORT"; then
    echo "❌ MISSING SECTION: $SECTION"
    exit 1
  fi
done

# Check frontmatter
if ! grep -q "^schema: fabric.report.v1" "$REPORT"; then
  echo "❌ INVALID FRONTMATTER"
  exit 1
fi

echo "✓ Report structure validated"

# Check that all MUST_DOCUMENT items have docs
UNDOCUMENTED=$(grep "MUST_DOCUMENT.*— *$\|MUST_DOCUMENT.*| —" "$REPORT" | wc -l)
if [ "$UNDOCUMENTED" -gt 0 ]; then
  echo "⚠️ WARNING: $UNDOCUMENTED MUST_DOCUMENT items without updated docs"
  exit 1
fi

echo "✓ All checks passed"
exit 0
```

---

## Příklad 7: Loop termination guard (K2 fix)

```bash
#!/bin/bash
# Guard against infinite loops in doc updates

MAX_DOC_UPDATES=${MAX_DOC_UPDATES:-500}
DOC_UPDATE_COUNTER=0

# Validate MAX_DOC_UPDATES is numeric
if ! echo "$MAX_DOC_UPDATES" | grep -qE '^[0-9]+$'; then
  MAX_DOC_UPDATES=500
  echo "WARN: MAX_DOC_UPDATES not numeric, reset to default (500)"
fi

# Process documentation files
while read -r doc_file; do
  DOC_UPDATE_COUNTER=$((DOC_UPDATE_COUNTER + 1))

  # Numeric validation of counter (strict)
  if ! echo "$DOC_UPDATE_COUNTER" | grep -qE '^[0-9]+$'; then
    DOC_UPDATE_COUNTER=0
    echo "WARN: counter corrupted, reset to 0"
  fi

  # Check termination
  if [ "$DOC_UPDATE_COUNTER" -ge "$MAX_DOC_UPDATES" ]; then
    echo "WARN: max documentation updates reached ($DOC_UPDATE_COUNTER/$MAX_DOC_UPDATES)"
    break
  fi

  # Process doc_file
  echo "Updating: $doc_file ($DOC_UPDATE_COUNTER/$MAX_DOC_UPDATES)"
  # ... actual update logic ...

done < <(find {DOCS_ROOT}/ -name "*.md" -type f)
```

---

## Příklad 8: Downstream contract — co čte kdo

**fabric-gap** reads:
- `reports/docs-*.md` field `coverage_pct` → porovnává s vision coverage target
- `reports/docs-*.md` field `missing_docs[]` → generuje intake items

**fabric-review** reads:
- `reports/docs-*.md` field `api_docs_status` → ověřuje API doc vs code sync
- `reports/docs-*.md` field `changelog_updated` → kontroluje changelog

**fabric-check** reads:
- `reports/docs-*.md` field `coverage_pct` → health check (min 60%)
- `reports/docs-*.md` field `stale_docs[]` → neaktualizované >30 dní

Report schema fields:
```yaml
coverage_pct: float          # 0-100
missing_docs: [string]       # undocumented modules
stale_docs: [string]         # docs not updated >30d
api_docs_status: PASS|WARN   # API doc vs code sync
changelog_updated: bool      # changelog reflects recent changes
```

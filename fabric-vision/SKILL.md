---
name: fabric-vision
description: "Analyze and validate the project vision documents. Extracts goals, pillars, constraints, success metrics, and decision principles. Produces a vision report and (if vision is incomplete/ambiguous) generates an intake item to improve the vision specification."
---

# VISION — Analýza vize + quality gates pro „směr“

## Účel

Zajistit, že agent ví:
- **proč** projekt existuje,
- **co** je cílem (a co není),
- **jak** poznáme úspěch,
- a jaké jsou principy rozhodování.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-vision" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-vision" --event end --status OK --report "{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).

## K10 Fix: Vision Analysis Example with Real LLMem Data

Here is a concrete example of a completed vision report for LLMem:

**File:** `{WORK_ROOT}/reports/vision-2026-03-06.md`

```yaml
---
schema: fabric.report.v1
kind: vision
version: "1.0"
created_at: "2026-03-06T09:00:00Z"
status: "COMPLETE"
---

# LLMem Vision Analysis Report

## Project Purpose

LLMem is a local-first long-term memory infrastructure for AI agents. It captures observations from agent runtimes, triages them into memories using deterministic heuristics, and provides a recall API returning budgeted XML injection blocks.

## Pillars & Assessment

### Pillar 1: Local-First Storage

**Goals:** ≥2 (MVP InMemoryBackend, Production Qdrant)
**Backlog Coverage:** 2/2 (100%)
**Done Items:** 1 (InMemoryBackend complete)
**Verdict:** ON_TRACK (Qdrant planned for T1)

### Pillar 2: Deterministic Triage

**Goals:** ≥4 (secret, PII, preference, decision detection)
**Backlog Coverage:** 4/4 (100%)
**Done Items:** 0 (Triage implementation is Sprint-2 target)
**Verdict:** ON_TRACK (Sprint-2 critical path)

### Pillar 3: Security & Governance

**Goals:** ≥3 (secrets gating, access control, audit logging)
**Backlog Coverage:** 3/3 (100%)
**Done Items:** 1 (secrets policy ADR-001 approved)
**Verdict:** CAUTION (Access control not yet designed)

## Success Metrics

| Metric | Target | Status | Deadline |
|--------|--------|--------|----------|
| Core API stable | MVP (4 endpoints) | 3/4 complete | Q1 2026 |
| Test coverage | ≥70% on core modules | 62% (triage: 0%) | Q1 2026 |
| Documentation | Full API + examples | 40% (design phase) | Q2 2026 |
| Performance | <100ms /recall latency | TBD (benchmark planned) | Q2 2026 |

## Risks & Mitigations

| Risk | Impact | Mitigation | Owner |
|------|--------|-----------|-------|
| Regex false positives in triage | LOW (false memory creation) | 97% precision target in test strategy | T-TRI team |
| Qdrant deployment complexity | MEDIUM (ops burden) | Docker compose template, E2E test | DevOps (T1) |
| Token budget exhaustion | HIGH (truncated recall) | Smart prioritization in recall/scoring.py | Core team |

## Vision Realism Verdict

REALISTIC — 5 foundational tasks (T-TRI, T-CAP, T-TEST, T-API, T-DOC) fit Sprint-2 (40h capacity). Track pillar 3 (security) closely — access control design needed by T1.
```

## Downstream Contract (WQ7 fix)

**Which downstream skills consume the vision report and which fields they read:**

- **fabric-gap** reads:
  - `Per-Pillar Assessment` table → columns: Total Goals, Backlog Coverage %, Done Items, Coverage %
  - `Vision Realism Verdict` field → to warn if scope too ambitious (UNREALISTIC = risk signal)
  - `Top 5 Risks & Gaps` section → to identify high-priority gaps for planning

- **fabric-sprint** reads:
  - `Per-Pillar Assessment.Verdict` column → (ON_TRACK/CAUTION/DEVIATION) to sequence sprint priorities
  - `Success Metrics` section → deadline field (Q1/Q2/etc) to set sprint goals
  - Pillar ordering (implicit) → to align sprint backlog with vision priorities

---

Bez kvalitní vize se backlog rozpadne na náhodnou práci.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` — core vize (purpose, pillars, principles, constraints)
- `{VISIONS_ROOT}/*.md` — sub-vize a rozšíření (ekonomika, bezpečnost, governance, architektonické vize, roadmap detaily…)

### Vztah core vision ↔ sub-vize

`vision.md` je **kořenový dokument** — definuje proč, co a jak. Sub-vize v `{VISIONS_ROOT}/` **rozvíjejí** jednotlivé pilíře nebo koncepty do hloubky. Core `vision.md` by měl na sub-vize odkazovat (PŘÍKLAD: `→ viz {VISIONS_ROOT}/<tema>.md`). Sub-vize NESMÍ odporovat core vizi — pokud je rozpor, je to finding do reportu.

---

## Výstupy

- `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md`
- volitelně intake item: `{WORK_ROOT}/intake/vision-improve-*.md` (pokud chybí klíčové části)

---

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

# --- Precondition 3: Vision dokument existuje ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "WARN: {WORK_ROOT}/vision.md not found — vision skill cannot validate non-existent vision"
  echo "STOP: Run fabric-init with vision template first"
  exit 1
fi

# --- Precondition 4: Visions directory exists (for sub-visions) ---
mkdir -p "{WORK_ROOT}/fabric/visions"
```

**Dependency chain:** `fabric-init` → [fabric-vision] → `fabric-gap` (and others)

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-vision. Expected: $EXPECTED_PHASES"
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
# validate_path "$VISION_FILE"
# validate_path "$VISION_REPORT"
```

### 1) Načti a strukturalizuj vizi — Operacionalizovaná extrakce

**A) Extrakce pilířů — Parsing rules:**

Pilíř je kterýkoliv z:
1. `## {Pillar Title}` (level-2 header) v `vision.md`
2. `### {Sub-pillar}` pod level-2 header v `vision.md`
3. `## {Pillar Title}` v jakémkoliv `{VISIONS_ROOT}/*.md`

**Bash extraction — pilíře z core vision.md:**
```bash
# Extract all level-2 headers (pillars)
PILLARS=$(grep "^## " vision.md | sed 's/^## //' | head -20)
PILLAR_COUNT=$(echo "$PILLARS" | wc -l)
echo "Detected $PILLAR_COUNT pillars from vision.md"
```

**B) Extrakce cílů per pilíř:**

Pod každý pilíř může být:
- Bullet points: `- {Goal description}` → počítej jako 1 cíl
- Sub-bullets: `  - {sub-goal}` → počítej do total

**Bash extraction — goals per pillar:**
```bash
# For each pillar section, count goal bullet points
PILLAR_NAME="Performance & Efficiency"
GOALS_IN_PILLAR=$(awk \
  "/^## $PILLAR_NAME/,/^## [^#]/ { if (/^- /) print }" \
  vision.md | wc -l)
echo "Pillar '$PILLAR_NAME' has $GOALS_IN_PILLAR goals"
```

**C) Extrakce z vision.md (core document):**

```bash
# Extract Purpose/Mission (first non-header, non-empty line)
PURPOSE=$(grep -A5 "^# " vision.md | grep -v "^#" | head -1)

# Extract Principles section
PRINCIPLES=$(awk '/^## Principles/,/^## [^P]/ { print }' vision.md | \
  grep "^- " | sed 's/^- //')

# Extract Constraints section
CONSTRAINTS=$(awk '/^## Constraints/,/^## [^C]/ { print }' vision.md | \
  grep "^- " | sed 's/^- //')

# Extract Non-goals section
NON_GOALS=$(awk '/^## Non-goals/,/^## [^N]/ { print }' vision.md | \
  grep "^- " | sed 's/^- //')

# Extract Success metrics section
METRICS=$(awk '/^## Success Metrics/,/^## [^S]/ { print }' vision.md | \
  grep "^- " | sed 's/^- //')
```

**D) Procesování sub-vize (`{VISIONS_ROOT}/*.md`):**

```bash
# List all sub-visions
for subviz in {VISIONS_ROOT}/*.md; do
  # Extract pillars from sub-vision
  SUB_PILLARS=$(grep "^## " "$subviz" | sed 's/^## //')

  # Check for new pillars not in core
  for pillar in $SUB_PILLARS; do
    if ! grep -q "^## $pillar" vision.md; then
      echo "WARN: New pillar in sub-vision: $pillar"
    fi
  done
done
```

**E) Detekce konfliktů — core vs. sub-vize:**

**Algoritmus:**
1. Extract keywords z core vision goals (filter: noun, adj, verb >4 char)
2. Extract keywords z sub-vision goals
3. Flag: IF sub-vision introduces contradictory keywords (opposite meaning)
4. Examples of contradictions:
   - Core: "simplicity", Sub-vision: "feature-rich complexity" → WARN
   - Core: "local-first", Sub-vision: "cloud deployment" → CRITICAL
   - Core: "minimal dependencies", Sub-vision: "integrate all frameworks" → WARN

```bash
# Simple keyword conflict detection
CORE_KEYWORDS=$(grep "^- " vision.md | grep -oE '\b(local|cloud|simple|complex|minimal|maximal)\b' | sort | uniq)
for subviz in {VISIONS_ROOT}/*.md; do
  SUB_KEYWORDS=$(grep "^- " "$subviz" | grep -oE '\b(local|cloud|simple|complex|minimal|maximal)\b' | sort | uniq)

  # Check for contradictions
  if echo "$CORE_KEYWORDS" | grep -q "local" && echo "$SUB_KEYWORDS" | grep -q "cloud"; then
    echo "CRITICAL: Sub-vision conflicts with core (local-first vs cloud)"
  fi
done
```

Všechny extrakce zaznamenej do "Extracted Artifacts" v reportu.

### 2) Vision quality gates — Scoring-based assessment

**A) Structural validation (automatizovatelná):**

```bash
# Automated validation script
SCORE=0

# Check 1: Principles section with ≥3 principles
PRINCIPLE_COUNT=$(awk '/^## Principles/,/^## [^P]/ { if (/^- /) count++ } END { print count }' vision.md)
if [ "$PRINCIPLE_COUNT" -ge 3 ]; then
  echo "✓ Principles: $PRINCIPLE_COUNT (PASS)"
  SCORE=$((SCORE + 1))
else
  echo "✗ Principles: $PRINCIPLE_COUNT (FAIL: need ≥3)"
fi

# Check 2: Goals section with ≥1 goal
GOALS_COUNT=$(awk '/^## Goals/,/^## [^G]/ { if (/^- /) count++ } END { print count }' vision.md)
if [ "$GOALS_COUNT" -ge 1 ]; then
  echo "✓ Goals: $GOALS_COUNT (PASS)"
  SCORE=$((SCORE + 1))
else
  echo "✗ Goals: $GOALS_COUNT (FAIL: need ≥1)"
fi

# Check 3: Non-goals section with ≥1 item
NON_GOALS_COUNT=$(awk '/^## Non-goals/,/^## [^N]/ { if (/^- /) count++ } END { print count }' vision.md)
if [ "$NON_GOALS_COUNT" -ge 1 ]; then
  echo "✓ Non-goals: $NON_GOALS_COUNT (PASS)"
  SCORE=$((SCORE + 1))
else
  echo "✗ Non-goals: $NON_GOALS_COUNT (FAIL: need ≥1)"
fi

# Check 4: Constraints section with ≥1 constraint
CONSTRAINTS_COUNT=$(awk '/^## Constraints/,/^## [^C]/ { if (/^- /) count++ } END { print count }' vision.md)
if [ "$CONSTRAINTS_COUNT" -ge 1 ]; then
  echo "✓ Constraints: $CONSTRAINTS_COUNT (PASS)"
  SCORE=$((SCORE + 1))
else
  echo "✗ Constraints: $CONSTRAINTS_COUNT (FAIL: need ≥1)"
fi

echo "Structural Score: $SCORE/4"
```

**B) Metrics quality (NOT just YES/NO):**

Pravidla:
- **GOOD metric** = (1) měřitelná (číslo + jednotka) AND (2) time-bound (deadline/sprint/quarter)
- **WEAK metric** = kvalitativní, bez čísla, bez deadlinu
- **MISSING metric** = žádné success metrics

Example GOOD: "Recall latency <100ms by Q2 2026"
Example WEAK: "Improve performance"

```bash
# Count metrics that are measurable + time-bound
METRICS=$(awk '/^## Success Metrics/,/^## [^S]/ { if (/^- /) print }' vision.md)
METRIC_COUNT=0
GOOD_METRIC_COUNT=0

while IFS= read -r metric; do
  METRIC_COUNT=$((METRIC_COUNT + 1))
  # Check if contains number and time reference
  if echo "$metric" | grep -qE '[0-9]+.*\(Q[0-9]|by.*20[0-9]{2}\)'; then
    GOOD_METRIC_COUNT=$((GOOD_METRIC_COUNT + 1))
  fi
done <<< "$METRICS"

echo "Metrics Quality: $GOOD_METRIC_COUNT/$METRIC_COUNT are GOOD (measurable + time-bound)"
if [ "$GOOD_METRIC_COUNT" -lt "$((METRIC_COUNT / 2))" ]; then
  echo "WARN: <50% of metrics are concrete. Need quantification + deadlines."
fi
```

**C) Non-goals quality (NOT just YES/NO):**

Pravidla:
- **GOOD non-goal** = Explicitní feature + reasoning (at least 1 reason)
- **WEAK non-goal** = Vágní ("budoucí práce") bez zdůvodnění

Example GOOD: "NOT: Real-time collaborative editing (too complex for MVP, revisit Q3)"
Example WEAK: "NOT: Advanced features"

```bash
# Check non-goals have reasoning (contain "because", "too", "revisit", etc.)
NON_GOALS=$(awk '/^## Non-goals/,/^## [^N]/ { if (/^- /) print }' vision.md)
NON_GOAL_COUNT=0
NON_GOAL_REASONED=0

while IFS= read -r goal; do
  NON_GOAL_COUNT=$((NON_GOAL_COUNT + 1))
  if echo "$goal" | grep -qiE '\(.*\)|because|too|revisit|future|later'; then
    NON_GOAL_REASONED=$((NON_GOAL_REASONED + 1))
  fi
done <<< "$NON_GOALS"

echo "Non-goals Quality: $NON_GOAL_REASONED/$NON_GOAL_COUNT have reasoning"
if [ "$NON_GOAL_REASONED" -lt 1 ]; then
  echo "CRITICAL: Non-goals lack reasoning. Add context for each."
fi
```

**D) Constraints quality (NOT just YES/NO):**

Pravidla:
- **GOOD constraint** = Measurable limit + rationale (e.g., "Latency <500ms due to user retention data")
- **WEAK constraint** = Abstract ("performance", "security") without evidence

```bash
# Check constraints have measurable values and rationale
CONSTRAINTS=$(awk '/^## Constraints/,/^## [^C]/ { if (/^- /) print }' vision.md)
CONSTRAINT_COUNT=0
CONSTRAINT_MEASURED=0

while IFS= read -r constraint; do
  CONSTRAINT_COUNT=$((CONSTRAINT_COUNT + 1))
  # Check for numbers or units (ms, GB, tokens, etc.)
  if echo "$constraint" | grep -qE '[0-9]+.*\(|due to|rationale'; then
    CONSTRAINT_MEASURED=$((CONSTRAINT_MEASURED + 1))
  fi
done <<< "$CONSTRAINTS"

echo "Constraints Quality: $CONSTRAINT_MEASURED/$CONSTRAINT_COUNT are measurable + reasoned"
if [ "$CONSTRAINT_MEASURED" -lt "$CONSTRAINT_COUNT" ]; then
  echo "WARN: Add evidence/rationale to abstract constraints."
fi
```

**QUALITY GATE VERDICT:**
```
STRUCTURAL_SCORE=4 (all sections present)
METRICS_GOOD_PCT = (GOOD_METRICS / TOTAL_METRICS) * 100
NON_GOALS_REASONED_PCT = (REASONED / TOTAL) * 100
CONSTRAINTS_MEASURED_PCT = (MEASURED / TOTAL) * 100

IF STRUCTURAL_SCORE = 4 AND METRICS >= 50% AND NON_GOALS >= 50% AND CONSTRAINTS >= 50%
  → QUALITY GATE = PASS ✓
ELSE
  → QUALITY GATE = FAIL ✗ (specify which section — WQ10 fix: make advisory checks BLOCKING)
```

**WQ10 enforcement:** CRITICAL findings MUST return FAIL status:
- STRUCTURAL_SCORE < 4 → **FAIL** (create intake item to add missing sections)
- METRICS_GOOD_PCT < 50% → **FAIL** (create intake item to quantify metrics)
- NON_GOALS_REASONED_PCT < 50% → **FAIL** (create intake item to add reasoning)
- ANY CRITICAL conflict detected → **FAIL** (create intake item to resolve)
- Realism verdict = UNREALISTIC → **FAIL** (create intake item to reduce scope or phased approach)

**Per-pillar kvantitativní assessment (POVINNÉ):**

Pro KAŻDY pilíř z vision.md vyhodnoť:

**Output format — Assessment table:**
```markdown
## Per-Pillar Assessment

| Pilíř | Total Goals | Backlog Coverage | DONE Items | Coverage % | Implementation % | Last Activity | Drift | Verdict |
|-------|---|---|---|---|---|---|---|---|
| Performance & Efficiency | 5 | 4 | 1 | 80% | 20% | 3 days ago | MEDIUM | CAUTION |
| Developer Experience | 6 | 3 | 2 | 50% | 33% | 2 weeks ago | HIGH | DEVIATION |
| Security & Compliance | 4 | 4 | 3 | 100% | 75% | 1 day ago | LOW | ON TRACK |
```

**A) Coverage % — konkrétní výpočet:**

```bash
# For each pillar, calculate coverage
PILLAR_NAME="Performance & Efficiency"

# Step 1: Count total goals in this pillar from vision.md
TOTAL_GOALS=$(awk \
  "/^## $PILLAR_NAME/,/^## [^#$PILLAR_NAME]/ { if (/^- /) count++ } END { print count+0 }" \
  vision.md)

# Step 2: Count backlog items linked to this pillar
# (search for files in backlog/ with metadata: pillar=<name> or linked_vision_goal matching pillar)
BACKLOG_ITEMS=$(find backlog/ -name "*.md" -type f | while read f; do
  if grep -q "pillar.*$PILLAR_NAME\|linked_vision.*$PILLAR_NAME" "$f"; then
    echo "$f"
  fi
done | wc -l)

# Step 3: Calculate coverage percentage
COVERAGE_PCT=$((BACKLOG_ITEMS * 100 / TOTAL_GOALS))
echo "Coverage for '$PILLAR_NAME': $COVERAGE_PCT% ($BACKLOG_ITEMS/$TOTAL_GOALS)"
```

**B) Implementation % — konkrétní výpočet:**

```bash
# For each pillar, calculate implementation progress

PILLAR_NAME="Performance & Efficiency"

# Step 1: Count backlog items linked to pillar (total)
TOTAL_PILLAR_ITEMS=$(find backlog/ -name "*.md" -type f | while read f; do
  if grep -q "pillar.*$PILLAR_NAME" "$f"; then
    echo "$f"
  fi
done | wc -l)

# Step 2: Count DONE items (status: DONE or status: Closed)
DONE_ITEMS=$(find backlog/ -name "*.md" -type f | while read f; do
  if grep -q "pillar.*$PILLAR_NAME" "$f" && grep -qE "status:\s*(DONE|Closed)" "$f"; then
    echo "$f"
  fi
done | wc -l)

# Step 3: Count IN_PROGRESS items
IN_PROGRESS_ITEMS=$(find backlog/ -name "*.md" -type f | while read f; do
  if grep -q "pillar.*$PILLAR_NAME" "$f" && grep -qE "status:\s*IN_PROGRESS" "$f"; then
    echo "$f"
  fi
done | wc -l)

# Step 4: Calculate implementation percentage
IMPL_PCT=$((DONE_ITEMS * 100 / TOTAL_PILLAR_ITEMS))
ACTIVE_PCT=$(((DONE_ITEMS + IN_PROGRESS_ITEMS) * 100 / TOTAL_PILLAR_ITEMS))

echo "Implementation for '$PILLAR_NAME':"
echo "  DONE: $DONE_ITEMS/$TOTAL_PILLAR_ITEMS = $IMPL_PCT%"
echo "  ACTIVE (DONE + IN_PROGRESS): $ACTIVE_PCT%"
```

**C) Drift detection — konkrétní kritéria:**

```bash
# Assess drift for pillar

PILLAR_NAME="Performance & Efficiency"
CURRENT_SPRINT="2026-03-06"  # Use current date
SPRINT_DURATION_DAYS=14

# HIGH Drift: 0 DONE items in last 2 sprints (28 days)
DONE_LAST_2_SPRINTS=$(find backlog/ -name "*.md" -type f | while read f; do
  if grep -q "pillar.*$PILLAR_NAME" "$f" && grep -qE "status:\s*(DONE|Closed)" "$f"; then
    COMPLETED_DATE=$(grep "completed_date:" "$f" | head -1 | awk '{print $2}')
    if [ ! -z "$COMPLETED_DATE" ]; then
      # Check if within last 28 days
      DAYS_DIFF=$(($(date -d "$CURRENT_SPRINT" +%s) - $(date -d "$COMPLETED_DATE" +%s)))
      DAYS_DIFF=$((DAYS_DIFF / 86400))
      if [ "$DAYS_DIFF" -lt 28 ]; then
        echo "$f"
      fi
    fi
  fi
done | wc -l)

if [ "$DONE_LAST_2_SPRINTS" -eq 0 ]; then
  DRIFT="HIGH"
elif [ "$IMPL_PCT" -lt 30 ]; then
  DRIFT="MEDIUM"
elif [ "$IMPL_PCT" -ge 30 ] && [ "$DONE_LAST_2_SPRINTS" -gt 0 ]; then
  DRIFT="LOW"
else
  DRIFT="MEDIUM"
fi

echo "Drift for '$PILLAR_NAME': $DRIFT"
echo "  (DONE in last 2 sprints: $DONE_LAST_2_SPRINTS, Overall IMPL: $IMPL_PCT%)"
```

**D) Verdict logic:**

```bash
# Assign verdict based on metrics

if [ "$COVERAGE_PCT" -ge 70 ] && [ "$IMPL_PCT" -ge 50 ] && [ "$DRIFT" = "LOW" ]; then
  VERDICT="ON_TRACK"
elif [ "$COVERAGE_PCT" -ge 40 ] || [ "$IMPL_PCT" -ge 30 ] || [ "$DRIFT" = "MEDIUM" ]; then
  VERDICT="CAUTION"
else
  VERDICT="DEVIATION"
fi

echo "Verdict for '$PILLAR_NAME': $VERDICT"
echo "  Coverage: $COVERAGE_PCT% | Implementation: $IMPL_PCT% | Drift: $DRIFT"
```

**Anti-patterns with detection & fix procedures (WQ4):**

**Anti-pattern A: Vágní non-goal bez zdůvodnění**
- Detection bash: `grep "^- NOT:" vision.md | grep -v '(.*)' | head -20`
- Example WEAK: `- NOT: Advanced features` (no reason)
- Fix procedure:
  1. For each unflagged non-goal, add parenthetical reason:
     - "(too complex for MVP)"
     - "(scheduled for Q3 2026)"
     - "(conflicts with principle: X)"
     - "(requires Y infrastructure)"
  2. Verify: `grep "^- NOT:" vision.md | wc -l` should equal `grep "^- NOT:" vision.md | grep '(.*' | wc -l`

**Anti-pattern B: Hardcoded success metric without deadline**
- Detection bash: `grep "^- " vision.md | grep -E '^- (Improve|Enhance|Better)' || grep "^- " vision.md | grep -v 'Q[1-4].*20[0-9][0-9]|by (January|February|March|April|May|June|July|August|September|October|November|December) 20[0-9][0-9]'`
- Example WEAK: `- Improve latency` (no number, no deadline)
- Fix procedure:
  1. Identify measurable unit (ms, %, queries/sec)
  2. Find deadline (by month/quarter)
  3. Rewrite: "Recall latency <100ms for 95% queries by Q2 2026"
  4. Validate bash: `grep "^- " vision.md | grep -E '[0-9]+.*Q[1-4].*20[0-9][0-9]' | wc -l`

**Anti-pattern C: Conflicting goals (local-first vs cloud, simple vs feature-rich)**
- Detection bash: keyword extraction (section 3, lines 485-546)
- Example: Core principle "local-first" but goal lists "cloud deployment capability"
- Fix procedure:
  1. Run conflict detection script (§3 step E)
  2. For each conflict, choose: (a) clarify goal wording, (b) move to non-goals, (c) add "future phase" note
  3. Retest: `bash` conflict script should report 0 CRITICAL conflicts

**Anti-pattern D: "Alle pilíře ON TRACK" without concrete numbers**
- Detection: grep "ON_TRACK\|CAUTION\|DEVIATION" vision report without % columns filled
- Example WEAK: "Pillar: Performance & Efficiency | ... | Verdict: ON_TRACK" (no metrics)
- Fix procedure:
  1. Every per-pillar row MUST have: Total Goals, Backlog Coverage %, Done Items, Implementation %
  2. Example GOOD: "Performance & Efficiency | 5 goals | 4 backlog items | 1 done | 80% coverage | 20% impl"
  3. Calculate formulas (bash at lines 312-369)

### 4) Complete filled-in example (WQ2 fix)

Here is a realistic LLMem vision report example with all fields populated:

```markdown
## Executive Summary

Vision is clear and measurable: Local-first memory infrastructure for agents with fail-open deployment. Principles well-defined (event-sourced, deterministic, replaceable). Success metrics are specific (latency <100ms by Q2, 70% docstring coverage). Assessment: REALISTIC with PASS on quality gates.

## Extracted Artifacts

### Purpose/Mission
LLMem is a local-first long-term memory infrastructure for AI agents. Captures observations from agent runtimes, triages them using deterministic heuristics (no LLM in hot path), and provides a recall API returning budgeted XML injection blocks.

### Pillars (3 total)
- Core Memory System: Storage, triaging, recall
- Integration & Operations: Deployability, monitoring
- Extensibility: Pluggable backends, custom patterns

### Goals by Pillar
- **Core Memory System** (5 goals):
  - Event-sourced JSONL log as source of truth (implemented)
  - Deterministic IDs from content_hash for idempotency (implemented)
  - Masked secrets, hashed PII in storage (implemented)
  - Sub-100ms recall latency for 95% queries by Q2 2026
  - Support for 2+ backend implementations (InMemory, Qdrant)

- **Integration & Operations** (4 goals):
  - Docker + systemd deployment ready
  - Structured JSON logging + request tracing
  - Admin API for memory inspection + deletion
  - Health endpoint returning service status

- **Extensibility** (3 goals):
  - Pluggable embedder interface (not just hash)
  - Custom triage patterns (regex-based, extensible)
  - Backend interface: new backends without code fork

### Principles (4 total)
- **Deterministic**: Reproducible results across rebuilds; UUIDs stable from content_hash
- **Fail-open**: Memory system optional; errors log warnings, never block agent
- **Local-first**: All data persisted locally; optional cloud sync only in roadmap
- **No LLM in hot path**: Triage uses regex patterns, not language models

### Non-Goals (3 total)
- NOT: Real-time collaborative editing (too complex for MVP; revisit Q3 if agent demand grows)
- NOT: Semantic search using embeddings (Phase 2; MVP uses hash-based matching)
- NOT: Multi-tenant isolation (single agent per instance; revisit Q4 if co-hosting needed)

### Success Metrics (4 total, 75% measurable)
- Recall latency <100ms for 95th percentile of queries by Q2 2026
- Docstring coverage ≥70% across public API by end of Q1 2026
- Support 2+ production-grade backends (Qdrant + compatible alternative)
- Fail-open design: zero blocking errors in production; all errors logged + recoverable

## Quality Gate Assessment

### Structural Validation
| Check | Result | Evidence |
|-------|--------|----------|
| Principles ≥3 | PASS | Found 4 principles |
| Goals ≥1 | PASS | Found 12 goals (5+4+3 across pillars) |
| Non-goals ≥1 | PASS | Found 3 non-goals with reasoning |
| Constraints ≥1 | PASS | Found 2 constraints (latency <500ms, max 1GB memory) |

**Structural Score: 4/4** ✓

### Metrics Quality
3/4 metrics are measurable + time-bound:
- GOOD: "Recall latency <100ms by Q2 2026"
- GOOD: "Docstring coverage ≥70% by end of Q1 2026"
- GOOD: "Support 2+ production-grade backends"
- WEAK: "Fail-open design" (not quantified; suggest: "zero blocking errors in 100k+ events")

### Non-Goals Reasoning
3/3 non-goals have explicit reasoning:
- All three include parenthetical rationale (too complex, phase 2, revisit Q3)

### Constraints Evidence
2/2 constraints are measurable + reasoned:
- "Latency <500ms for worst-case query due to agent timeout sensitivity"
- "Memory ≤1GB per instance (embedded cost constraint)"

**Quality Gate Verdict: PASS ✓** — All sections present, 75% metrics concrete, all non-goals reasoned, all constraints evidence-based

### Vision Realism Assessment
- Pillar count: 3 (target: ≤7) → ✓ OK
- Max goals per pillar: 5 (target: ≤10) → ✓ OK
- Conflicting goals: None detected (local-first not contradicted by any pillar) → ✓ None
- Timeline estimate: ~8 epics → ~2 sprints (~3-4 months) → ✓ OK

**Realism Verdict: REALISTIC** ✓
```

### 4) Vision REALISM assessment — Ambition + feasibility check

**Algoritmus automatizované kontroly:**

```bash
# A) Check pillar count
PILLAR_COUNT=$(grep "^## " vision.md | wc -l)
if [ "$PILLAR_COUNT" -gt 7 ]; then
  echo "WARN: $PILLAR_COUNT pillars detected (>7 = too ambitious). Risk of diluted focus."
fi

# B) Check goal count per pillar
for pillar in $(grep "^## " vision.md | sed 's/^## //'); do
  PILLAR_GOALS=$(awk "/^## $pillar/,/^## [^#]/ { if (/^- /) count++ } END { print count+0 }" vision.md)
  if [ "$PILLAR_GOALS" -gt 10 ]; then
    echo "WARN: Pillar '$pillar' has $PILLAR_GOALS goals (>10 = unfocused)"
  fi
done

# C) Conflicting goals detection
# Extract keywords from core goals and look for opposites
GOALS_TEXT=$(awk '/^## Goals/,/^## [^G]/ { print }' vision.md)

if echo "$GOALS_TEXT" | grep -qi "simplicity\|minimal\|lean"; then
  if echo "$GOALS_TEXT" | grep -qi "feature.rich\|comprehensive\|all.in.one"; then
    echo "CRITICAL: Conflicting goals detected: 'simplicity' vs 'feature-rich'"
  fi
fi

if echo "$GOALS_TEXT" | grep -qi "local.first\|offline"; then
  if echo "$GOALS_TEXT" | grep -qi "cloud\|always.online\|sync"; then
    echo "CRITICAL: Conflicting goals detected: 'local-first' vs 'cloud-dependent'"
  fi
fi

# D) Timeline feasibility
TOTAL_EPICS=$(grep -c "^### " vision.md)
# Estimate: typical sprint delivers 3-5 items
ESTIMATED_SPRINTS=$((TOTAL_EPICS / 4))

echo "Timeline estimate: $TOTAL_EPICS epics → ~$ESTIMATED_SPRINTS sprints (~6-9 months)"
if [ "$ESTIMATED_SPRINTS" -gt 12 ]; then
  echo "WARN: Vision spans >12 sprints. Break into phased rollout."
fi
```

**Realism verdict:**
- ✓ REALISTIC: ≤7 pillars, ≤10 goals/pillar, no conflicts, timeline <12 sprints
- ⚠ CAUTION: >7 pillars OR >10 goals/pillar OR timeline 12-18 sprints
- ✗ UNREALISTIC: Conflicting goals OR timeline >18 sprints OR >15 pillars

### 3) Najdi ambiguitu a konflikty — Konkrétní detekční algoritmy

**A) Konflikty mezi core vizí a sub-vizemi:**

```bash
# Extract core vision keywords
CORE_KEYWORDS=$(awk '/^## Goals/,/^## [^G]/ { print }' vision.md | \
  grep -oE '\b[a-z]{4,}\b' | sort | uniq)

# For each sub-vision, check for contradictions
for subviz in {VISIONS_ROOT}/*.md; do
  SUB_KEYWORDS=$(awk '/^## Goals/,/^## [^G]/ { print }' “$subviz” | \
    grep -oE '\b[a-z]{4,}\b' | sort | uniq)

  # Check for explicit contradictions
  CONTRADICTION_PAIRS=(
    “local:cloud”
    “simplicity:complexity”
    “minimal:maximal”
    “offline:online”
    “deterministic:probabilistic”
    “stateless:stateful”
  )

  for pair in “${CONTRADICTION_PAIRS[@]}”; do
    WORD1=$(echo “$pair” | cut -d: -f1)
    WORD2=$(echo “$pair” | cut -d: -f2)

    if echo “$CORE_KEYWORDS” | grep -q “$WORD1” && echo “$SUB_KEYWORDS” | grep -q “$WORD2”; then
      echo “CRITICAL CONFLICT in $(basename $subviz): Core emphasizes '$WORD1' but sub-vision uses '$WORD2'”
    fi
  done

  # Check for NEW pillars in sub-vision not in core
  SUB_PILLARS=$(grep “^## “ “$subviz” | sed 's/^## //')
  while IFS= read -r pillar; do
    if ! grep -q “^## $pillar” vision.md; then
      echo “WARN: Sub-vision $(basename $subviz) introduces new pillar: '$pillar' (not in core)”
    fi
  done <<< “$SUB_PILLARS”
done
```

**Output format for conflicts:**
```
CONFLICT REPORT
===============
[CRITICAL] core=”local-first”, sub-vision/infrastructure.md=”cloud deployment”
[WARN] New pillar in sub-vision/analytics.md: “Real-time ML” (not mentioned in core)
[WARN] Orphaned pillar: “Extensibility” in vision.md not developed by any sub-vision
```

**B) Vágní cíle bez metrik:**

```bash
# Identify non-measurable goals
VAGUE_GOALS=$(awk '/^## Goals/,/^## [^G]/ { print }' vision.md | grep “^- “ | \
  grep -vE '[0-9]+%|[0-9]+ms|[0-9]+s|by Q[0-9]|by (January|February|March|April|May|June|July|August|September|October|November|December)')

if [ ! -z “$VAGUE_GOALS” ]; then
  echo “Non-measurable goals (need quantification):”
  echo “$VAGUE_GOALS”
fi
```

**C) Chybějící definice cílového uživatele:**

```bash
# Check for user/audience/persona definition
if ! grep -qiE “user|audience|persona|stakeholder” vision.md; then
  echo “CRITICAL: No explicit user/stakeholder definition in vision.md”
  echo “  → Add section 'Target Users' with 2-3 user personas or stakeholder groups”
fi
```

**D) Osiřelé sub-vize (bez reference z core):**

```bash
# Find sub-visions not referenced from core vision.md
for subviz in {VISIONS_ROOT}/*.md; do
  SUBVIZ_BASENAME=$(basename “$subviz” .md)
  if ! grep -q “$SUBVIZ_BASENAME\|$(basename $subviz)” vision.md; then
    echo “WARN: Orphaned sub-vision: $subviz”
    echo “  → Add reference in vision.md (e.g., '→ see {VISIONS_ROOT}/$SUBVIZ_BASENAME.md')”
  fi
done
```

**E) Chybějící sub-vize pro core pilíře:**

```bash
# Find pillars in vision.md not developed by sub-visions
CORE_PILLARS=$(grep “^## “ vision.md | sed 's/^## //')
DEVELOPED_PILLARS=””

for subviz in {VISIONS_ROOT}/*.md; do
  DEVELOPED_PILLARS=”$DEVELOPED_PILLARS $(grep “^## “ “$subviz” | sed 's/^## //')”
done

while IFS= read -r pillar; do
  if ! echo “$DEVELOPED_PILLARS” | grep -q “$pillar”; then
    echo “WARN: Pillar '$pillar' has no detailed sub-vision”
    echo “  → Either link to existing sub-vision or create one”
  fi
done <<< “$CORE_PILLARS”
```

### 4) Vytvoř vision report — Struktura + konkrétní šablona

Report MUSÍ být umístěn v: `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md`

**Povinná struktura:**

```markdown
---
schema: fabric.report.v1
kind: vision
version: "1.0"              # WQ9 fix: add version to track report schema evolution
run_id: "{run_id}"          # WQ9 fix: for tracing across runs
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"  # WQ9 fix: ISO 8601 timestamp
---

# Vision Analysis Report — {date}

## Executive Summary
{1-2 věty shrnutí: je vize jasná, měřitelná, dosažitelná? Jaká je hlavní zjištění?}

## Extracted Artifacts

### Purpose/Mission
{Quoted from vision.md, 1-3 věty}

### Pillars ({pillar_count} celkem)
- Pillar 1: {Popis}
- Pillar 2: {Popis}
- ...

### Goals by Pillar
- **Pillar 1** ({goal_count} goals):
  - Goal A: {Měřitelná? Deadline?}
  - Goal B: ...

### Principles ({principle_count} celkem)
{Vyjmenování klíčových principů}

### Non-Goals ({non_goal_count} celkem)
{Vyjmenování s vysvětlením}

### Success Metrics ({metric_count} celkem, {measured_pct}% measurable)
{Vyjmenování; flag které jsou vágní}

## Quality Gate Assessment

### Structural Validation
| Check | Result | Evidence |
|-------|--------|----------|
| Principles ≥3 | {PASS/FAIL} | Found {N} principles |
| Goals ≥1 | {PASS/FAIL} | Found {N} goals |
| Non-goals ≥1 | {PASS/FAIL} | Found {N} non-goals |
| Constraints ≥1 | {PASS/FAIL} | Found {N} constraints |

**Structural Score: {X}/4**

### Metrics Quality
{GOOD_METRICS}/{TOTAL_METRICS} metrics are measurable + time-bound
- GOOD example: "Recall latency <100ms by Q2 2026"
- WEAK example: "Improve performance"
{List weak metrics}

### Non-Goals Reasoning
{REASONED}/{TOTAL} non-goals have explicit reasoning
{List non-goals lacking rationale}

### Constraints Evidence
{MEASURED}/{TOTAL} constraints are measurable + reasoned
{List abstract constraints}

**Quality Gate Verdict: {PASS ✓ / REVIEW NEEDED ⚠}**
{Specify failing sections if needed}

### Vision Realism Assessment
- Pillar count: {N} (target: ≤7) → {✓ OK / ⚠ WARN}
- Max goals per pillar: {N} (target: ≤10) → {✓ OK / ⚠ WARN}
- Conflicting goals: {0 / list} → {✓ None / ⚠ CRITICAL}
- Timeline estimate: {N} sprints (~{months} months) → {✓ OK / ⚠ WARN}

**Realism Verdict: {REALISTIC / CAUTION / UNREALISTIC}**

## Per-Pillar Assessment

| Pilíř | Total Goals | Backlog Coverage | DONE Items | Coverage % | Implementation % | Last Activity | Drift | Verdict |
|-------|---|---|---|---|---|---|---|---|
| {Pillar 1} | {N} | {N} | {N} | {X}% | {Y}% | {date} | {LOW/MED/HIGH} | {ON_TRACK/CAUTION/DEVIATION} |
| {Pillar 2} | {N} | {N} | {N} | {X}% | {Y}% | {date} | {LOW/MED/HIGH} | {ON_TRACK/CAUTION/DEVIATION} |

**Overall Assessment:** {X} pillars ON_TRACK, {Y} CAUTION, {Z} DEVIATION

## Sub-Vision Alignment

### Identified Sub-Visions
- {VISIONS_ROOT}/file1.md → Develops: Pillar X
- {VISIONS_ROOT}/file2.md → Develops: Pillar Y
- ...

### Conflict Detection
{List any CRITICAL/WARN conflicts detected, or "No conflicts detected"}

### Orphaned Artifacts
- Pillars without sub-visions: {list or "None"}
- Sub-visions without core reference: {list or "None"}

## Top 5 Risks & Gaps

1. **Risk/Gap:** {Description} → **Mitigation:** {Action}
2. **Risk/Gap:** {Description} → **Mitigation:** {Action}
...

## Backlog Implications & Priorities

Based on this vision analysis, recommended backlog priorities:

1. {TOP PRIORITY ITEM} — Reason: {Links to pillar X, covers goal Y}
2. {PRIORITY ITEM 2} — Reason: {Coverage gap in pillar Z}
...

## Intake Items Generated

{List any generated intake items for vision improvements, or "None"}

---
**Generated:** {datetime}
**Status:** {PASS / REVIEW_NEEDED / CRITICAL_ISSUES}
```

**Validation bash (ENFORCE na kraju):**

```bash
# Check report quality before writing
REPORT_PATH="reports/vision-$(date +%Y-%m-%d).md"

# Validate report has required sections
REQUIRED_SECTIONS=("Extracted Artifacts" "Quality Gate Assessment" "Per-Pillar Assessment" "Top 5 Risks")

for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "^## $section\|^# $section" "$REPORT_PATH"; then
    echo "ERROR: Missing section: $section"
    exit 1
  fi
done

# Validate per-pillar assessment is not empty
PILLAR_COUNT=$(grep "^| " "$REPORT_PATH" | grep -v "Pilíř" | wc -l)
if [ "$PILLAR_COUNT" -lt 1 ]; then
  echo "ERROR: Per-Pillar Assessment has no data rows (minimum 1 pillar required)"
  exit 1
fi

# Validate all pillars have metrics
INCOMPLETE_ROWS=$(grep "^| " "$REPORT_PATH" | grep "^| " | grep -E "{.*}|—|N/A" | wc -l)
if [ "$INCOMPLETE_ROWS" -gt 0 ]; then
  echo "ERROR: $INCOMPLETE_ROWS pillar rows have incomplete metrics (use numbers, not placeholders)"
  exit 1
fi

# Validate Drift column contains only valid values
INVALID_DRIFTS=$(grep "^| " "$REPORT_PATH" | grep -v "Drift" | grep -v "LOW\|MEDIUM\|HIGH" | wc -l)
if [ "$INVALID_DRIFTS" -gt 0 ]; then
  echo "ERROR: Drift column must be LOW/MEDIUM/HIGH (found invalid values)"
  exit 1
fi

# Validate Verdict column contains only valid values
INVALID_VERDICTS=$(grep "^| " "$REPORT_PATH" | grep -v "Verdict" | grep -v "ON_TRACK\|CAUTION\|DEVIATION" | wc -l)
if [ "$INVALID_VERDICTS" -gt 0 ]; then
  echo "ERROR: Verdict column must be ON_TRACK/CAUTION/DEVIATION (found invalid values)"
  exit 1
fi

echo "✓ Report validation PASSED"
```

### 5) Pokud vize není dostatečná → vytvoř intake item

**Triggeringové podmínky:**

Vytvoř intake item IF:
- STRUCTURAL_SCORE < 4 (some sections missing)
- METRICS_GOOD_PCT < 50% (>50% of metrics are vague)
- NON_GOALS_REASONED_PCT < 50% (>50% of non-goals lack reasoning)
- CONSTRAINTS_MEASURED_PCT < 50% (>50% of constraints are abstract)
- ANY CRITICAL conflict detected (core vs. sub-vision)
- Realism verdict = UNREALISTIC
- ANY pillar has Verdict = DEVIATION for 3+ consecutive assessments

**Intake item creation:**

```bash
# Generate intake item for vision improvements
INTAKE_GAPS=””
if [ “$STRUCTURAL_SCORE” -lt 4 ]; then
  INTAKE_GAPS=”$INTAKE_GAPS- Add missing sections (Principles/Goals/Non-goals/Constraints)\n”
fi
if [ “$METRIC_PCT” -lt 50 ]; then
  INTAKE_GAPS=”$INTAKE_GAPS- Quantify success metrics (add numbers + deadlines)\n”
fi
if [ “$CONFLICT_COUNT” -gt 0 ]; then
  INTAKE_GAPS=”$INTAKE_GAPS- Resolve core vs. sub-vision conflicts ($CONFLICT_COUNT found)\n”
fi

# Write intake item
cat > “intake/vision-improve-$(date +%Y%m%d).md” << 'EOF'
---
source: generate
initial_type: Chore
raw_priority: 7
status: Open
created_date: $(date -Iseconds)
---

# Improve Vision Specification

## Problem
The current vision.md needs refinement to provide clear direction for backlog prioritization.

## Gaps Identified
$(echo -e “$INTAKE_GAPS”)

## Required Actions

### If Metrics < 50% good:
For each SUCCESS METRIC, ensure it contains:
- Numeric target (e.g., <100ms, >95%, 10/10 users)
- Time-bound deadline (e.g., by Q2 2026, by March 31)
- Measurable success criterion

Example:
- GOOD: “Recall latency <100ms for 95% of queries by Q2 2026”
- WEAK: “Improve latency”

### If Non-goals < 50% reasoned:
For each NON-GOAL, add explicit reasoning in parentheses:
- (too complex for MVP)
- (scheduled for Q3 2026)
- (conflicts with core principle: X)
- (requires Y infrastructure not yet available)

### If Structural gaps exist:
Add missing sections to vision.md:
- Principles section (≥3 guiding principles)
- Goals section (≥1 measurable goal per pillar)
- Non-goals section (≥1 explicitly out-of-scope item)
- Constraints section (≥1 technical/business constraint)

## Acceptance Criteria
- [ ] vision.md STRUCTURAL_SCORE = 4/4 (all sections present)
- [ ] Metrics Quality ≥70% (70%+ of metrics are measurable + time-bound)
- [ ] Non-goals Reasoning ≥70%
- [ ] Constraints Evidence ≥70%
- [ ] All CRITICAL conflicts resolved
- [ ] Realism Assessment = REALISTIC
EOF
```

---

## Quality Enforcement — Report Validation

**MANDATORY validation before marking work as DONE:**

```bash
#!/bin/bash
# Validate vision report quality (must pass 100% checks)

REPORT="${WORK_ROOT}/reports/vision-$(date +%Y-%m-%d).md"

# Count enforced elements
PASS_COUNT=0
TOTAL_CHECKS=0

# Check 1: Report exists and is not empty
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f "$REPORT" ] && [ -s "$REPORT" ]; then
  echo "✓ Check 1: Report file exists and has content"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 1: FAIL — Report missing or empty"
fi

# Check 2: Executive Summary section exists
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if grep -q "^## Executive Summary" "$REPORT"; then
  echo "✓ Check 2: Executive Summary section found"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 2: FAIL — Missing Executive Summary"
fi

# Check 3: Extracted Artifacts section with Purpose/Mission
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if grep -q "^## Extracted Artifacts" "$REPORT" && grep -q "^### Purpose" "$REPORT"; then
  echo "✓ Check 3: Extracted Artifacts (Purpose) section found"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 3: FAIL — Missing Extracted Artifacts or Purpose"
fi

# Check 4: Pillars section
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if grep -q "^### Pillars" "$REPORT"; then
  PILLAR_COUNT=$(grep "^- " "$REPORT" | head -10 | wc -l)
  if [ "$PILLAR_COUNT" -ge 1 ]; then
    echo "✓ Check 4: Pillars found ($PILLAR_COUNT detected)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "✗ Check 4: FAIL — Pillars section empty (need ≥1 pillar)"
  fi
else
  echo "✗ Check 4: FAIL — Missing Pillars section"
fi

# Check 5: Quality Gate Assessment section
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if grep -q "^## Quality Gate Assessment" "$REPORT"; then
  echo "✓ Check 5: Quality Gate Assessment section found"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 5: FAIL — Missing Quality Gate Assessment"
fi

# Check 6: Per-Pillar Assessment table (not empty)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if grep -q "^## Per-Pillar Assessment" "$REPORT"; then
  TABLE_ROWS=$(awk '/^## Per-Pillar Assessment/,/^## [^P]/ { if (/^| [^P]/) print }' "$REPORT" | grep -v "Pilíř" | wc -l)
  if [ "$TABLE_ROWS" -ge 1 ]; then
    echo "✓ Check 6: Per-Pillar Assessment has $TABLE_ROWS pillar rows"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "✗ Check 6: FAIL — Per-Pillar Assessment table is empty (need ≥1 pillar assessment)"
  fi
else
  echo "✗ Check 6: FAIL — Missing Per-Pillar Assessment section"
fi

# Check 7: All pillar rows have numeric Coverage %
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
INCOMPLETE_COVERAGE=$(awk '/^## Per-Pillar Assessment/,/^## [^P]/ { if (/^| / && !/Pilíř/) print }' "$REPORT" | \
  grep -v "[0-9]\+%" | wc -l)
if [ "$INCOMPLETE_COVERAGE" -eq 0 ]; then
  echo "✓ Check 7: All pillars have numeric Coverage %"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 7: FAIL — $INCOMPLETE_COVERAGE pillar rows missing Coverage % (use numbers: 50%, 75%, etc.)"
fi

# Check 8: All pillar rows have numeric Implementation %
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
INCOMPLETE_IMPL=$(awk '/^## Per-Pillar Assessment/,/^## [^P]/ { if (/^| / && !/Pilíř/) print }' "$REPORT" | \
  awk -F'|' '{ if ($6 !~ /[0-9]+%/) print }' | wc -l)
if [ "$INCOMPLETE_IMPL" -eq 0 ]; then
  echo "✓ Check 8: All pillars have numeric Implementation %"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 8: FAIL — $INCOMPLETE_IMPL pillar rows missing Implementation % (use numbers: 25%, 50%, etc.)"
fi

# Check 9: All Drift values are valid (LOW/MEDIUM/HIGH)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
INVALID_DRIFTS=$(awk '/^## Per-Pillar Assessment/,/^## [^P]/ { if (/^| / && !/Pilíř/) print }' "$REPORT" | \
  awk -F'|' '{ if ($8 !~ /LOW|MEDIUM|HIGH/) print }' | wc -l)
if [ "$INVALID_DRIFTS" -eq 0 ]; then
  echo "✓ Check 9: All Drift values are valid (LOW/MEDIUM/HIGH)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 9: FAIL — $INVALID_DRIFTS pillar rows have invalid Drift (must be LOW/MEDIUM/HIGH)"
fi

# Check 10: All Verdict values are valid (ON_TRACK/CAUTION/DEVIATION)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
INVALID_VERDICTS=$(awk '/^## Per-Pillar Assessment/,/^## [^P]/ { if (/^| / && !/Pilíř/) print }' "$REPORT" | \
  awk -F'|' '{ if ($9 !~ /ON_TRACK|CAUTION|DEVIATION/) print }' | wc -l)
if [ "$INVALID_VERDICTS" -eq 0 ]; then
  echo "✓ Check 10: All Verdict values are valid (ON_TRACK/CAUTION/DEVIATION)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "✗ Check 10: FAIL — $INVALID_VERDICTS pillar rows have invalid Verdict (must be ON_TRACK/CAUTION/DEVIATION)"
fi

# Check 11: Sub-Vision Alignment section (if sub-visions exist)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
SUBVIZ_COUNT=$(find {VISIONS_ROOT} -name "*.md" 2>/dev/null | wc -l)
if [ "$SUBVIZ_COUNT" -gt 0 ]; then
  if grep -q "^## Sub-Vision Alignment\|^### Conflict Detection" "$REPORT"; then
    echo "✓ Check 11: Sub-Vision Alignment section found (for $SUBVIZ_COUNT sub-visions)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "⚠ Check 11: WARN — Sub-visions exist but no alignment section (add Sub-Vision Alignment section)"
  fi
else
  echo "⊘ Check 11: SKIP — No sub-visions found (not required)"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# Check 12: Top 5 Risks section
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if grep -q "^## Top 5 Risks\|^## Risks" "$REPORT"; then
  RISK_COUNT=$(grep "^[0-9]\. " "$REPORT" | wc -l)
  if [ "$RISK_COUNT" -ge 3 ]; then
    echo "✓ Check 12: Top Risks section with $RISK_COUNT identified risks"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "✗ Check 12: FAIL — Risk section has <3 risks (need ≥3)"
  fi
else
  echo "✗ Check 12: FAIL — Missing Top Risks section"
fi

# Final verdict
echo ""
echo "========================================="
echo "Report Quality: $PASS_COUNT / $TOTAL_CHECKS checks passed"
echo "========================================="

if [ "$PASS_COUNT" -ge "$((TOTAL_CHECKS - 2))" ]; then
  echo "Status: ✓ PASS — Report meets quality standards"
  exit 0
elif [ "$PASS_COUNT" -ge "$((TOTAL_CHECKS - 5))" ]; then
  echo "Status: ⚠ NEEDS REVIEW — Some sections need improvement"
  exit 1
else
  echo "Status: ✗ CRITICAL — Major gaps; report is not publishable"
  exit 1
fi
```

**DO NOT mark work as DONE until all enforced checks PASS.**

---

## Self-check (pre-completion checklist)

- [ ] report file exists: `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md`
- [ ] report contains: Executive Summary, Extracted Artifacts (Purpose/Mission/Pillars/Goals/Principles/Non-goals/Constraints/Metrics)
- [ ] report contains: Quality Gate Assessment (Structural + Metrics + Non-goals + Constraints quality scores)
- [ ] report contains: Per-Pillar Assessment table with ≥1 pillar assessed
  - [ ] Each pillar row has: Total Goals, Backlog Coverage, DONE Items (actual numbers, not placeholders)
  - [ ] Each pillar row has: Coverage %, Implementation %, Last Activity date
  - [ ] Each pillar row has: Drift (LOW/MEDIUM/HIGH), Verdict (ON_TRACK/CAUTION/DEVIATION)
- [ ] report contains: Vision Realism Assessment (pillar count, goals/pillar, conflicts, timeline)
- [ ] report contains: Sub-Vision Alignment section with Conflict Detection (if sub-visions exist)
- [ ] report contains: Top 5 Risks section with ≥3 risks identified
- [ ] Intake item generated IF: STRUCTURAL_SCORE < 4 OR metrics <50% good OR conflicts detected OR realism = UNREALISTIC
  - [ ] intake item exists at: `{WORK_ROOT}/intake/vision-improve-*.md`
  - [ ] intake item clearly lists specific gaps to address
- [ ] Protocol logging:
  - [ ] `--event start` logged at beginning
  - [ ] `--event end --status OK --report <path>` logged on success
  - [ ] `--event error --status ERROR` logged on critical issues

**Enforcement:** Run validation bash before declaring work DONE. All checks must pass.

# fabric-vision — Detailní workflow

## § 1: Načti a strukturalizuj vizi

### A) Extrakce pilířů — Parsing rules

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

### B) Extrakce cílů per pilíř

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

### C) Extrakce z vision.md (core document)

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

### D) Procesování sub-vize (`{VISIONS_ROOT}/*.md`)

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

### E) Detekce konfliktů — core vs. sub-vize

**Algoritmus:**
1. Extract keywords z core vision goals (noun, adj, verb >4 char)
2. Extract keywords z sub-vision goals
3. Flag: IF sub-vision introduces contradictory keywords
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

**Output format:**
```
CONFLICT REPORT
===============
[CRITICAL] core="local-first", sub-vision/infrastructure.md="cloud deployment"
[WARN] New pillar in sub-vision/analytics.md: "Real-time ML" (not mentioned in core)
[WARN] Orphaned pillar: "Extensibility" in vision.md not developed by any sub-vision
```

**Všechny extrakce zaznamenej do "Extracted Artifacts" v reportu.**

---

## § 2: Vision quality gates — Scoring-based assessment

### A) Structural validation (automatizovatelná)

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

### B) Metrics quality (NOT just YES/NO)

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

### C) Non-goals quality (NOT just YES/NO)

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

### D) Constraints quality (NOT just YES/NO)

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

### E) QUALITY GATE VERDICT

```bash
STRUCTURAL_SCORE=4  # from check
METRICS_GOOD_PCT=$((GOOD_METRIC_COUNT * 100 / METRIC_COUNT))
NON_GOALS_REASONED_PCT=$((NON_GOAL_REASONED * 100 / NON_GOAL_COUNT))
CONSTRAINTS_MEASURED_PCT=$((CONSTRAINT_MEASURED * 100 / CONSTRAINT_COUNT))

if [ "$STRUCTURAL_SCORE" = "4" ] && [ "$METRICS_GOOD_PCT" -ge 50 ] && \
   [ "$NON_GOALS_REASONED_PCT" -ge 50 ] && [ "$CONSTRAINTS_MEASURED_PCT" -ge 50 ]; then
  QUALITY_GATE="PASS ✓"
else
  QUALITY_GATE="FAIL ✗"
fi
```

**WQ10 enforcement:** CRITICAL findings MUST return FAIL status:
- STRUCTURAL_SCORE < 4 → **FAIL** (create intake item to add missing sections)
- METRICS_GOOD_PCT < 50% → **FAIL** (create intake item to quantify metrics)
- NON_GOALS_REASONED_PCT < 50% → **FAIL** (create intake item to add reasoning)
- ANY CRITICAL conflict detected → **FAIL** (create intake item to resolve)
- Realism verdict = UNREALISTIC → **FAIL** (create intake item to reduce scope or phased approach)

### F) Anti-patterns with detection & fix procedures

**Anti-pattern A: Vágní non-goal bez zdůvodnění**
- Detection bash: `grep "^- NOT:" vision.md | grep -v '(.*)' | head -20`
- Fix procedure: Add parenthetical reason: "(too complex for MVP)" etc.

**Anti-pattern B: Hardcoded success metric without deadline**
- Detection bash: `grep "^- " vision.md | grep -E '^- (Improve|Enhance|Better)' | grep -v 'Q[1-4]'`
- Fix procedure: Identify measurable unit (ms, %, queries/sec), find deadline, rewrite: "Recall latency <100ms for 95% queries by Q2 2026"

**Anti-pattern C: Conflicting goals (local-first vs cloud, simple vs feature-rich)**
- Detection bash: keyword extraction (lines above)
- Fix procedure: Run conflict detection script, for each conflict choose: (a) clarify goal, (b) move to non-goals, (c) add "future phase" note

**Anti-pattern D: "Alle pilíře ON TRACK" without concrete numbers**
- Detection: grep "ON_TRACK" vision report without % columns filled
- Fix procedure: Every per-pillar row MUST have: Total Goals, Backlog Coverage %, Done Items, Implementation %

---

## § 3: Per-pillar kvantitativní assessment

Pro **KAŽDÝ pilíř** z vision.md vyhodnoť:

### A) Coverage % — konkrétní výpočet

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

### B) Implementation % — konkrétní výpočet

```bash
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

### C) Drift detection — konkrétní kritéria

```bash
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

### D) Verdict logic

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

### E) Output format — Assessment table

```markdown
## Per-Pillar Assessment

| Pilíř | Total Goals | Backlog Coverage | DONE Items | Coverage % | Implementation % | Last Activity | Drift | Verdict |
|-------|---|---|---|---|---|---|---|---|
| Performance & Efficiency | 5 | 4 | 1 | 80% | 20% | 3 days ago | MEDIUM | CAUTION |
| Developer Experience | 6 | 3 | 2 | 50% | 33% | 2 weeks ago | HIGH | DEVIATION |
| Security & Compliance | 4 | 4 | 3 | 100% | 75% | 1 day ago | LOW | ON TRACK |
```

---

## § 4: Detekce ambiguity a konfliktů

### A) Konflikty mezi core vizí a sub-vizemi

```bash
# Extract core vision keywords
CORE_KEYWORDS=$(awk '/^## Goals/,/^## [^G]/ { print }' vision.md | \
  grep -oE '\b[a-z]{4,}\b' | sort | uniq)

# For each sub-vision, check for contradictions
for subviz in {VISIONS_ROOT}/*.md; do
  SUB_KEYWORDS=$(awk '/^## Goals/,/^## [^G]/ { print }' "$subviz" | \
    grep -oE '\b[a-z]{4,}\b' | sort | uniq)

  # Check for explicit contradictions
  CONTRADICTION_PAIRS=(
    "local:cloud"
    "simplicity:complexity"
    "minimal:maximal"
    "offline:online"
    "deterministic:probabilistic"
    "stateless:stateful"
  )

  for pair in "${CONTRADICTION_PAIRS[@]}"; do
    WORD1=$(echo "$pair" | cut -d: -f1)
    WORD2=$(echo "$pair" | cut -d: -f2)

    if echo "$CORE_KEYWORDS" | grep -q "$WORD1" && echo "$SUB_KEYWORDS" | grep -q "$WORD2"; then
      echo "CRITICAL CONFLICT in $(basename $subviz): Core emphasizes '$WORD1' but sub-vision uses '$WORD2'"
    fi
  done

  # Check for NEW pillars in sub-vision not in core
  SUB_PILLARS=$(grep "^## " "$subviz" | sed 's/^## //')
  while IFS= read -r pillar; do
    if ! grep -q "^## $pillar" vision.md; then
      echo "WARN: Sub-vision $(basename $subviz) introduces new pillar: '$pillar' (not in core)"
    fi
  done <<< "$SUB_PILLARS"
done
```

### B) Vágní cíle bez metrik

```bash
# Identify non-measurable goals
VAGUE_GOALS=$(awk '/^## Goals/,/^## [^G]/ { print }' vision.md | grep "^- " | \
  grep -vE '[0-9]+%|[0-9]+ms|[0-9]+s|by Q[0-9]|by (January|February|March|April|May|June|July|August|September|October|November|December)')

if [ ! -z "$VAGUE_GOALS" ]; then
  echo "Non-measurable goals (need quantification):"
  echo "$VAGUE_GOALS"
fi
```

### C) Chybějící definice cílového uživatele

```bash
# Check for user/audience/persona definition
if ! grep -qiE "user|audience|persona|stakeholder" vision.md; then
  echo "CRITICAL: No explicit user/stakeholder definition in vision.md"
  echo "  → Add section 'Target Users' with 2-3 user personas or stakeholder groups"
fi
```

### D) Osiřelé sub-vize (bez reference z core)

```bash
# Find sub-visions not referenced from core vision.md
for subviz in {VISIONS_ROOT}/*.md; do
  SUBVIZ_BASENAME=$(basename "$subviz" .md)
  if ! grep -q "$SUBVIZ_BASENAME\|$(basename $subviz)" vision.md; then
    echo "WARN: Orphaned sub-vision: $subviz"
    echo "  → Add reference in vision.md (e.g., '→ see {VISIONS_ROOT}/$SUBVIZ_BASENAME.md')"
  fi
done
```

### E) Chybějící sub-vize pro core pilíře

```bash
# Find pillars in vision.md not developed by sub-visions
CORE_PILLARS=$(grep "^## " vision.md | sed 's/^## //')
DEVELOPED_PILLARS=""

for subviz in {VISIONS_ROOT}/*.md; do
  DEVELOPED_PILLARS="$DEVELOPED_PILLARS $(grep "^## " "$subviz" | sed 's/^## //')"
done

while IFS= read -r pillar; do
  if ! echo "$DEVELOPED_PILLARS" | grep -q "$pillar"; then
    echo "WARN: Pillar '$pillar' has no detailed sub-vision"
    echo "  → Either link to existing sub-vision or create one"
  fi
done <<< "$CORE_PILLARS"
```

---

## § 5: Report creation

### A) Vision Realism Assessment

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

### B) Intake item creation (IF quality gates FAIL)

**Triggering conditions:**

Vytvoř intake item IF:
- STRUCTURAL_SCORE < 4 (some sections missing)
- METRICS_GOOD_PCT < 50% (>50% of metrics are vague)
- NON_GOALS_REASONED_PCT < 50% (>50% of non-goals lack reasoning)
- CONSTRAINTS_MEASURED_PCT < 50% (>50% of constraints are abstract)
- ANY CRITICAL conflict detected (core vs. sub-vision)
- Realism verdict = UNREALISTIC
- ANY pillar has Verdict = DEVIATION for 3+ consecutive assessments

**Bash generation:**

```bash
# Generate intake item for vision improvements
INTAKE_GAPS=""
if [ "$STRUCTURAL_SCORE" -lt 4 ]; then
  INTAKE_GAPS="$INTAKE_GAPS- Add missing sections (Principles/Goals/Non-goals/Constraints)\n"
fi
if [ "$METRIC_PCT" -lt 50 ]; then
  INTAKE_GAPS="$INTAKE_GAPS- Quantify success metrics (add numbers + deadlines)\n"
fi
if [ "$CONFLICT_COUNT" -gt 0 ]; then
  INTAKE_GAPS="$INTAKE_GAPS- Resolve core vs. sub-vision conflicts ($CONFLICT_COUNT found)\n"
fi

# Write intake item
cat > "intake/vision-improve-$(date +%Y%m%d).md" << 'EOF'
---
source: fabric-vision
initial_type: Chore
raw_priority: 7
status: new
created_date: $(date -Iseconds)
---

# Improve Vision Specification

## Problem
The current vision.md needs refinement to provide clear direction for backlog prioritization.

## Gaps Identified
$(echo -e "$INTAKE_GAPS")

## Required Actions

### If Metrics < 50% good:
For each SUCCESS METRIC, ensure it contains:
- Numeric target (e.g., <100ms, >95%, 10/10 users)
- Time-bound deadline (e.g., by Q2 2026, by March 31)
- Measurable success criterion

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

## § 6: Downstream Contract (WQ7 fix)

**Which downstream skills consume the vision report and which fields they read:**

- **fabric-gap** reads:
  - `Per-Pillar Assessment` table → columns: Total Goals, Backlog Coverage %, Done Items, Coverage %
  - `Vision Realism Verdict` field → to warn if scope too ambitious (UNREALISTIC = risk signal)
  - `Top 5 Risks & Gaps` section → to identify high-priority gaps for planning

- **fabric-sprint** reads:
  - `Per-Pillar Assessment.Verdict` column → (ON_TRACK/CAUTION/DEVIATION) to sequence sprint priorities
  - `Success Metrics` section → deadline field (Q1/Q2/etc) to set sprint goals
  - Pillar ordering (implicit) → to align sprint backlog with vision priorities

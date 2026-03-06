# fabric-check — Příklady a referencní výstupy

## Příklad 1: Populovaný Audit Report (WQ2 fix)

```markdown
---
schema: fabric.report.v1
kind: check
run_id: "check-2026-03-06-abc123"
created_at: "2026-03-06T14:30:00Z"
version: "1.0"
status: WARN
score: 65
---

# check — Audit Report 2026-03-06

## Summary

Workspace audit found 2 CRITICAL issues (missing test command, stale process map), 1 HIGH issue (governance drift), and auto-fixed 3 backlog item metadata gaps. Score: 65/100 (WARN). All CRITICAL issues have intake items.

## Metrics

| Check | Result | Detail |
|-------|--------|--------|
| Structural integrity | PASS | All required directories exist |
| Backlog schema | WARN | 3 items missing 'prio' field (auto-fixed) |
| Backlog vision-fit | PASS | All T0/T1 items linked to vision goals |
| Governance index | PASS | decisions/ and specs/ indices present and current |
| Sprint plan | PASS | Sprint 5 task queue validated, all items exist |
| Config COMMANDS | CRITICAL | COMMANDS.test is TBD (blocks testing) |
| Process map | WARN | process-map.md stale (8 days old, threshold 7d) |
| Code coverage | CRITICAL | 42% < 50% floor (collected from last pytest run) |
| Lint/Format | SKIPPED | COMMANDS.lint empty, format_check TBD |
| Governance module tests | HIGH | Module triage/patterns.py has no test coverage |

## Findings (High → Low severity)

| Finding | Severity | Confidence | Intake Item |
|---------|----------|------------|-------------|
| COMMANDS.test is TBD — tests cannot run | CRITICAL | HIGH (deterministic check) | check-missing-test-command |
| Code coverage 42% < floor 50% — need >50% coverage | CRITICAL | HIGH (measured from pytest run) | check-coverage-floor-failed |
| Governance module triage/patterns.py has 0 test coverage | HIGH | MEDIUM (heuristic: grep-based detection) | check-missing-governance-tests |
| Process map stale (8 days old, threshold 7) | MEDIUM | HIGH (timestamp-based) | check-process-map-stale |
| Backlog items: 3 missing 'prio' field (auto-fixed) | LOW | HIGH (schema validation) | None (auto-fixed) |

## Auto-fixes applied

- ✓ Regenerated backlog.md index (5 items reordered by priority)
- ✓ Added missing 'prio' fields to 3 backlog items (set to 0, needs manual review)
- ✓ Regenerated governance/INDEX.md for decisions

## Intake items created

1. `intake/check-missing-test-command.md` — COMMANDS.test must be configured
2. `intake/check-coverage-floor-failed.md` — Coverage 42% needs to reach 50% floor
3. `intake/check-missing-governance-tests.md` — Add tests for triage/patterns.py

## Warnings

- Process map not updated for 8 days — recommend running fabric-process to refresh
- 2 backlog items (epic-data-pipeline, task-llmem-ui-mockup) unchanged for >30 days
- Report freshness: gap-* report is 35 days old (threshold 30 days)

## Configuration notes

- Coverage floor: 50% (from config.md)
- Stale item threshold: 30 days (default)
- Stale epic threshold: 60 days (default)
- Report freshness thresholds: gap=30d, prio=45d, check=15d
```

## Příklad 2: Anti-patterns s Detection & Fix (§9)

### Anti-pattern A: Stale backlog item ignored

**Detection:**
```bash
find {WORK_ROOT}/backlog/ -name "*.md" -mtime +30 | wc -l
```

**Fix:**
Create intake item per stale item. If >60 days, escalate to CRITICAL and FAIL the audit.

### Anti-pattern B: Broken backlog index (items exist but not in backlog.md)

**Detection:**
```bash
diff <(ls "{WORK_ROOT}/backlog"/*.md | sed 's|.*/||;s|\.md||' | sort) \
     <(grep -oP '(?<=\[)[^\]]+' "{WORK_ROOT}/backlog.md" | sort)
```

**Fix:**
```bash
python skills/fabric-init/tools/backlog_index.py --work-root "{WORK_ROOT}"
```

### Anti-pattern C: Missing required frontmatter fields

**Detection:**
```bash
for f in "{WORK_ROOT}/backlog"/*.md; do
  grep -L "^status:" "$f"
done
```

**Fix:**
Auto-fill missing fields with defaults:
- status: BACKLOG
- effort: M
- tier: T2
- updated: today

### Anti-pattern D: Config COMMANDS referencing non-existent scripts

**Detection:**
```bash
grep -oP 'test:\s*"?\K[^"]+' "{WORK_ROOT}/config.md" | \
  xargs -I{} sh -c 'command -v {} || echo "MISSING: {}"'
```

**Fix:**
Report as CRITICAL. Create intake item to fix config.md or install missing tool.

### Anti-pattern E: Duplicate backlog item slugs

**Detection:**
```bash
ls "{WORK_ROOT}/backlog"/*.md | sed 's|.*/||;s|\.md||' | sort | uniq -d
```

**Fix:**
Rename duplicates with suffix `-v2`, `-v3`. Update backlog.md index.

## Příklad 3: Status taxonomie (z config.md)

Backlog statusy musí být:
```
IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE
```

## Příklad 4: Scoring example

```
2 CRITICAL × 30 = 60 points
1 HIGH × 10 = 10 points
0 MEDIUM = 0 points
2 LOW × 1 = 2 points
SCORE = 100 - 60 - 10 = 30 → FAIL
```

## Příklad 5: Intake item template (check-missing-test-command.md)

```markdown
---
schema: fabric.intake_item.v1
title: "Add COMMANDS.test configuration to config.md"
source: check
initial_type: Task
raw_priority: 8
created: 2026-03-06
status: new
linked_vision_goal: "Code Quality & Testing"
---

## Kontext

fabric-check audit (2026-03-06) found that `COMMANDS.test` in config.md is set to `TBD` or empty. This blocks the pipeline because testing is mandatory before merge.

## Doporučená akce

Edit `{WORK_ROOT}/config.md` and set:
```yaml
COMMANDS:
  test: "pytest -q"
```

Verify by running:
```bash
{COMMANDS.test}
```

Should exit with code 0 (all tests pass).
```

## Příklad 6: Intake item template (check-process-map-missing.md)

```markdown
---
schema: fabric.intake_item.v1
title: "Create process-map.md documentation"
source: check
initial_type: Task
raw_priority: 7
created: 2026-03-06
status: new
linked_vision_goal: "Documentation & Knowledge"
---

## Kontext

fabric-check audit found that `{WORK_ROOT}/fabric/processes/process-map.md` does not exist. The project is in Sprint 2+ (current: 2026-03-06), so process documentation is mandatory for visibility and onboarding.

## Doporučená akce

Run the fabric-process skill to auto-generate:
```bash
python -m skills.fabric_process
```

Or manually create `{WORK_ROOT}/fabric/processes/process-map.md` with:
- Overview of team processes
- Decision-making flow
- Code review checklist
- Testing protocol
- Deployment steps
- Escalation path

Mark `updated: 2026-03-06` in frontmatter.
```

## Příklad 7: Intake item template (check-missing-vision-link-task-123.md)

```markdown
---
schema: fabric.intake_item.v1
title: "Link task-123 to vision goal or reduce tier"
source: check
initial_type: Task
raw_priority: 6
created: 2026-03-06
status: new
linked_vision_goal: ""
---

## Kontext

Backlog item `task-123` has `tier: T0` but `linked_vision_goal` is empty. High-tier items (T0/T1) must be connected to explicit vision goals to maintain backlog clarity.

## Doporučená akce

Choose one:

**Option A: Link to an existing vision goal**

Edit `{WORK_ROOT}/backlog/task-123.md`:
```yaml
linked_vision_goal: "Pillar: Data Pipeline / Goal: Real-time Ingestion"
```

Verify the goal exists in `{WORK_ROOT}/vision.md` or `{VISIONS_ROOT}/`.

**Option B: Reduce tier**

If this item is actually tactical (T2/T3), edit:
```yaml
tier: T2
```

Ensure justification is documented in the item body.
```

## Příklad 8: Scoring formula az config.md

```bash
# Ne hardcoded — vždycky z config.md
STALE_ITEM_DAYS=$(grep 'backlog_stale_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "30")
STALE_EPIC_DAYS=$(grep 'epic_stale_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "60")
STALE_REPORT_GAP_DAYS=$(grep 'report_stale_gap_threshold_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' || echo "30")

echo "Using stale thresholds from config.md: items=${STALE_ITEM_DAYS}d (>2 sprints), epics=${STALE_EPIC_DAYS}d (>4 sprints), reports=${STALE_REPORT_GAP_DAYS}d"
```

### WQ5 justification for thresholds:
- **STALE_ITEM_DAYS=30:** typical 2-week sprint means item active every 2 weeks; 30d = miss 2 sprints
- **STALE_EPIC_DAYS=60:** epics are longer-lived; 60d = miss 4 sprints (acceptable for multi-sprint epics)
- **STALE_REPORT_GAP_DAYS=30:** analysis reports should refresh ≤monthly; >30d = data drift risk

## Příklad 9: Confidence scoring per check

Format in report:
```markdown
| Finding | Severity | Confidence | Detail |
|---------|----------|------------|--------|
| Missing COMMANDS.test | CRITICAL | HIGH (95%+) | Deterministic check: grep config.md |
| Process map stale | MEDIUM | HIGH (95%+) | Timestamp-based: updated field comparison |
| E2E coverage ratio <50% | HIGH | MEDIUM (75%) | Heuristic: grep-based route counting |
| Stale epic (62 days) | CRITICAL | HIGH (95%+) | Deterministic: epoch calculation >60d threshold |
```

## Příklad 10: Backlog item validation checklist

Per item, validate:
```bash
# 1. File exists and is readable
[ -f "$ITEM_FILE" ] || MISSING="$MISSING file-not-found"

# 2. YAML frontmatter is valid
grep -q '^---$' "$ITEM_FILE" || MISSING="$MISSING yaml-frontmatter"

# 3. Required fields present and non-empty
for FIELD in schema id title type tier status effort created updated source prio; do
  grep -q "^${FIELD}:" "$ITEM_FILE" || MISSING="$MISSING $FIELD"
done

# 4. Enum values valid
STATUS=$(grep '^status:' "$ITEM_FILE" | awk '{print $2}')
echo "$ENUMS_STATUSES" | grep -qw "$STATUS" || MISSING="$MISSING invalid-status"

TIER=$(grep '^tier:' "$ITEM_FILE" | awk '{print $2}')
echo "$ENUMS_TIERS" | grep -qw "$TIER" || MISSING="$MISSING invalid-tier"

EFFORT=$(grep '^effort:' "$ITEM_FILE" | awk '{print $2}')
echo "$ENUMS_EFFORTS" | grep -qw "$EFFORT" || MISSING="$MISSING invalid-effort"

# 5. Filename matches ID
ITEM_ID=$(basename "$ITEM_FILE" .md)
grep -q "^id: $ITEM_ID" "$ITEM_FILE" || MISSING="$MISSING id-mismatch"

if [ -n "$MISSING" ]; then
  echo "FINDING: $ITEM_FILE missing:$MISSING"
fi
```

## Příklad 11: E2E endpoint coverage report

```
Route Count (from API code):    15 endpoints
E2E Test Count (from tests):     8 tests
Coverage Ratio:                  8/15 = 53%

Target:                          ≥50% (WARN if <50%)
Status:                          PASS ✓

Routes without tests:
  - POST /api/v1/users
  - DELETE /api/v1/users/{id}
  - PATCH /api/v1/config
  - GET /api/v1/health (implicit — tested in all E2E suites)
  - GET /api/v1/metrics
  - ...
```

## Příklad 12: Report freshness monitoring output

```
GAP report (max 30d freshness):
  - Latest: reports/gap-2026-02-24.md (10 days old)
  - Status: PASS ✓

PRIO report (max 45d freshness):
  - Latest: reports/prio-2026-01-22.md (43 days old)
  - Status: PASS ✓

CHECK report (max 15d freshness):
  - Latest: reports/check-2026-03-05.md (1 day old)
  - Status: PASS ✓

VISION report (max 60d freshness):
  - Latest: None found
  - Status: WARN ⚠ (never run)
```

## Příklad 13: Governance module test coverage

```bash
Registry modules (from config.md GOVERNANCE.decisions.registry):
  - triage/heuristics.py
  - triage/patterns.py
  - recall/pipeline.py
  - recall/scoring.py
  - storage/backends/qdrant.py

Test coverage per module:
  - triage/heuristics.py:    ✓ test_heuristics.py
  - triage/patterns.py:      ✗ NO TESTS (HIGH finding)
  - recall/pipeline.py:      ✓ test_pipeline.py
  - recall/scoring.py:       ✓ test_scoring.py
  - storage/backends/qdrant: ✓ test_qdrant_backend.py

Finding:
  - Module: triage/patterns.py
  - Status: CRITICAL — pattern detection is core to system
  - Action: Create intake item to add test coverage
```

## Příklad 14: Process map freshness detailed check

```
File: {WORK_ROOT}/fabric/processes/process-map.md

Checks:
1. File exists:           ✓ YES
2. Has 'updated' field:   ✓ YES (2026-02-28)
3. Age calculation:       8 days old (today=2026-03-07, updated=2026-02-28)
4. Freshness threshold:   7 days (from config.md)
5. Status:                ⚠ WARN (8 > 7)

Orphan count check:
  - UNIMPLEMENTED entries: 2
  - ORPHAN entries:        0
  - Status:                INFO (low concern)

Findings to report:
  1. Process map is stale (8 days old, >7d threshold) — WARN / HIGH confidence
  2. Process map has 2 unimplemented entries — INFO
  3. Recommendation: Run fabric-process to refresh documentation
```

## Příklad 15: WQ10 stale enforcement (CRITICAL threshold)

```bash
Stale detection results:

Items >30d but <60d (WARN):
  - task-data-pipeline (45 days unchanged)
    - Last updated: 2026-01-21
    - Recommendation: Review and update or move to done/

Items >60d (CRITICAL — WQ10 blocking):
  - epic-ui-refactor (92 days unchanged)
    - Last updated: 2025-12-04
    - Status: CRITICAL — must be resolved
    - Action: Create intake item or move to done/

  - task-legacy-cleanup (78 days unchanged)
    - Last updated: 2025-11-29
    - Status: CRITICAL — must be resolved
    - Action: Create intake item or move to done/

WQ10 Enforcement:
  - CRITICAL_STALE_COUNT: 2
  - Report status: FAIL (>0 items >60d stale triggers FAIL)
  - Score impact: 2 CRITICAL × 30 = -60 points

Recommendation:
  - Create intake items for both stale epics
  - Re-prioritize them or mark as DONE/archived
  - Plan recovery in next sprint planning
```

## Příklad 16: Confidence level definitions

```
HIGH (95%+):
  - File existence checks (does file exist?)
  - YAML schema validation (is frontmatter valid?)
  - Enum match validation (is status one of {IDEA, DESIGN, ...}?)
  - Filename matches ID (does item-123.md have id: item-123?)
  - Date/epoch calculations (>60 days old?)

MEDIUM (70–95%):
  - Stale detection with thresholds (item >30 days old, but threshold could be inadequate)
  - Grep-based code search (grep 'def test' {TEST_ROOT}/ — might miss some tests)
  - Process map freshness (timestamp comparison, but "stale" is policy-dependent)
  - Module test coverage detection (grep-based — may not find indirect tests)

LOW (<70%):
  - Code complexity estimates (heuristic: lines of code, cyclomatic complexity)
  - Documentation coverage estimation (counting markdown headers)
  - Integration depth inference (based on imports and references)
  - Best-effort pattern matching in code
```

## Příklad 17: Batch processing (multiple items)

```bash
# fabric-check processes all backlog items in one pass

TASK_IDS=$(ls {WORK_ROOT}/backlog/*.md | sed 's|.*/||;s|\.md||')

REPORT="{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md"
echo "---" > "$REPORT"
echo "schema: fabric.report.v1" >> "$REPORT"
echo "kind: check" >> "$REPORT"
echo "---" >> "$REPORT"
echo "" >> "$REPORT"
echo "# check — Audit Report {YYYY-MM-DD}" >> "$REPORT"
echo "" >> "$REPORT"
echo "| Item | Status | Issues | Auto-fixed |" >> "$REPORT"
echo "|------|--------|--------|------------|" >> "$REPORT"

for TASK_ID in $TASK_IDS; do
  ITEM_FILE="{WORK_ROOT}/backlog/${TASK_ID}.md"
  [ -f "$ITEM_FILE" ] || continue

  # Validate schema, extract findings
  ISSUES=""
  AUTOFIX=""

  if ! grep -q "^schema:" "$ITEM_FILE"; then
    AUTOFIX="$AUTOFIX; added schema"
    echo "schema: $(grep 'SCHEMA.backlog_item' {WORK_ROOT}/config.md | awk '{print $2}')" >> "$ITEM_FILE"
  fi

  # ...more checks...

  STATUS="PASS"
  [ -n "$ISSUES" ] && STATUS="WARN"

  echo "| $TASK_ID | $STATUS | $ISSUES | $AUTOFIX |" >> "$REPORT"
done

# Append summary, scoring, intake items at end...
```

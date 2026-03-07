---
name: fabric-review
description: "Perform automated code review for the current WIP task across 9 dimensions (R1–R9). Uses config COMMANDS.lint + COMMANDS.format_check as objective gates, then performs a structured diff review including process-chain validation. Writes a review report, updates backlog item review_report, and creates intake items for systemic improvements."
---

<!-- built from: builder-template -->

## § 1 Účel

Zajistit „enterprise-grade" kvalitu před merge:
- objektivní gates (lint/format),
- strukturovaný review diffu (R1–R9),
- jednoznačný verdikt: `CLEAN`, `REWORK`, nebo `REDESIGN`,
- evidence report + intake items pro systémové zlepšení.

## § 2 Protokol (povinné bash)

Log START/END events to shared protocol via:

```bash
# START: Log skill execution start
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-review" \
  --event start

# END: Log skill completion with report path
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-review" \
  --event end \
  --status OK \
  --report "{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"
```

If STOP or CRITICAL error encountered:

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-review" \
  --event error \
  --status ERROR \
  --message "Brief error summary (1 sentence)"
```

## § 3 Preconditions (bash validation)

```bash
# --- Path traversal guard (K7) ---
for VAR in "{WORK_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# 0. Phase validation (K1)
PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$PHASE" != "implementation" ]; then
  echo "STOP: fabric-review requires phase=implementation, current: $PHASE"
  exit 1
fi

# 1. WIP item and branch exist
WIP_ITEM=$(python skills/fabric-init/tools/fabric.py state-get --field wip_item 2>/dev/null)
WIP_BRANCH=$(python skills/fabric-init/tools/fabric.py state-get --field wip_branch 2>/dev/null)

if [ ! -f "{WORK_ROOT}/backlog/${WIP_ITEM}.md" ]; then
  echo "STOP: backlog file missing for wip_item=$WIP_ITEM"
  exit 1
fi

if ! git rev-parse --verify "$WIP_BRANCH" >/dev/null 2>&1; then
  echo "STOP: branch $WIP_BRANCH does not exist in git"
  exit 1
fi

# 2. Test report exists (temporal dependency: implement→test→review)
LATEST_TEST_REPORT=$(ls -t {WORK_ROOT}/reports/test-${WIP_ITEM}-*.md 2>/dev/null | head -1)
if [ -z "$LATEST_TEST_REPORT" ]; then
  echo "STOP: no test report found for wip_item=$WIP_ITEM — run fabric-test first"
  exit 1
fi

# 3. Check rework counter (max_rework_iters enforcement)
REWORK_COUNT=$(grep 'rework_count:' "{WORK_ROOT}/backlog/${WIP_ITEM}.md" | awk '{print $2}' | tr -d '[:space:]')
REWORK_COUNT=${REWORK_COUNT:-0}
# K7: Numeric guard — prevent shell injection via rework_count field
if ! echo "$REWORK_COUNT" | grep -qE '^[0-9]*$'; then
  echo "STOP: rework_count='$REWORK_COUNT' not numeric in backlog/${WIP_ITEM}.md"
  exit 1
fi
if [ "$REWORK_COUNT" -ge 3 ]; then
  echo "STOP: max rework iterations (3) exceeded for $WIP_ITEM"
  exit 1
fi
```

## § 4 Vstupy

- `{WORK_ROOT}/config.md` — COMMANDS.lint, COMMANDS.format_check, QUALITY.mode
- `{WORK_ROOT}/state.md` — wip_item, wip_branch, phase
- `{WORK_ROOT}/backlog/{wip_item}.md` — task metadata, rework_count
- `{WORK_ROOT}/reports/test-{wip_item}-*.md` — test evidence (temporal dependency)
- `{WORK_ROOT}/decisions/INDEX.md` — accepted ADR list (compliance)
- `{WORK_ROOT}/specs/INDEX.md` — active/draft specs (compliance)
- `{WORK_ROOT}/fabric/processes/process-map.md` — process contracts (R9, optional)
- git diff: `main...{wip_branch}` — code changes under review

## § 5 Výstupy

- `{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md`
  - Frontmatter: schema=fabric.report.v1, verdict=CLEAN|REWORK|REDESIGN
  - R1–R9 dimension scores + findings
  - Gate results (lint, format, tests)
  - Critical findings count
- Update backlog item:
  - `review_report: "reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`
  - `updated: {YYYY-MM-DD}`
  - `status`: DONE (CLEAN) / IN_PROGRESS (REWORK) / BLOCKED (REDESIGN)
- Optional intake items: `{WORK_ROOT}/intake/review-*.md` (systemic findings)
- Optional: publish via `python skills/fabric-init/tools/fabric.py review-publish`

## § 6 FAST PATH (zaměřeno na determinismus)

**Objective gates + verdict deterministically:**

```bash
# 1. Run objective gates (optional if not in config)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint} && LINT_RESULT="PASS" || LINT_RESULT="FAIL"
else
  LINT_RESULT="SKIPPED"
fi

if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check} && FMT_RESULT="PASS" || FMT_RESULT="FAIL"
else
  FMT_RESULT="SKIPPED"
fi

# 2. Create report skeleton (deterministic template)
python skills/fabric-init/tools/fabric.py report-new \
  --template review-summary.md \
  --step review --kind review \
  --out "{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md" \
  --ensure-run-id

# 3. Determine verdict based on gates + R1–R9 review (see §7)
# Verdict logic: CLEAN if no CRITICAL findings + gates pass/pre-existing only
#               REWORK if ≥1 CRITICAL (opravitelné) or gates fail in task files
#               REDESIGN if ≥1 CRITICAL (redesign) or max_rework_iters reached

# 4. Apply plan to update backlog
python skills/fabric-init/tools/fabric.py apply "{WORK_ROOT}/plans/review-plan-{wip_item}-{YYYY-MM-DD}-{run_id}.yaml"
```

## § 7 Postup (Proces)

**Overview:** Review is deterministic, multi-dimensional assessment (R1–R9) with objective gates. Detailed workflow in references/workflow.md.

**High-level steps:**

1. **Objective gates** (lint, format) — binary PASS/FAIL
2. **Diff analysis** — identify changed files, categorize (code/test/docs)
3. **R1–R9 review** — per-dimension checklist + scoring (see references/workflow.md)
4. **Verdict determination** — CLEAN / REWORK / REDESIGN (severity taxonomy)
5. **Report generation** — frontmatter + R1–R9 findings table + recommendations
6. **Backlog update** — link report, set status based on verdict
7. **Intake items** — systemic findings (if any)

> **Detaily viz `references/workflow.md` pro:**
> - R1 Correctness checklist (logic, edge cases, complexity)
> - R2 Security checklist (validation, secrets, auth)
> - R3 Performance checklist (algorithms, I/O, caching)
> - R4 Reliability checklist (error handling, timeouts, retries)
> - R5 Testability checklist (AC coverage, assertions, isolation)
> - R6 Maintainability checklist (naming, size, DRY)
> - R7 Documentation checklist (docstrings, comments, CHANGELOG)
> - R8 Compliance checklist (ADR/spec validation)
> - R9 Process Chain checklist (contract_modules validation)
> - Finding severity taxonomy & scoring
> - Fix strategy per finding type (standardized format)

## K10 — Concrete Example & Anti-patterns

### Example: Task b015 Review — R1–R9 Assessment (LLMem)

```
Review task-b015 (add recall scoring tests):
  WIP branch: feat/b015-recall-scoring-tests
  Diff: 47 LOC added ({CODE_ROOT}/recall/test_scoring.py lines 127–172)
  Test report: {WORK_ROOT}/reports/test-b015-2026-03-07-r1.md (PASS, 49/49)

Gate results:
  Lint: PASS (ruff check clean)
  Format: PASS (black unchanged)

R1 Correctness (85/100):
  ✓ Logic sound: 4 test cases cover happy/edge/error paths
  ✓ Edge cases: stale memory, minimal input tested
  ✗ MEDIUM: test_combine_score_minimal missing docstring (line 165)
  Finding: Missing docstring for complex assertion

R2 Security (90/100):
  ✓ No hardcoded secrets
  ✓ Input validation in test fixtures
  Finding: None (PASS)

R3 Performance (95/100):
  ✓ No O(n²) in test loops
  ✓ Fixtures efficient
  Finding: None (PASS)

R4 Reliability (80/100):
  ✗ CRITICAL: test_combine_score_old_memory uses time.sleep(1) — flaky on slow CI
  Recommendation: Mock time or use pytest-freezegun

R5 Testability (90/100):
  ✓ Tests isolated (no shared state)
  ✓ All assertions explicit
  Finding: None (PASS)

R6 Maintainability (85/100):
  ✓ Clear naming: test_combine_score_old_memory vs test_combine_score_fresh
  ✗ MEDIUM: lines 140–155 could extract helper (DRY)

R7 Documentation (80/100):
  ✗ HIGH: CHANGELOG not updated (product feature, should log)
  ✓ docstrings on 3/4 functions

R8 Compliance (95/100):
  ✓ ADR-003 (testing) followed
  Finding: None (PASS)

R9 Process Chain (90/100):
  ✓ contract_modules: [recall/scoring.py] — coverage verified
  Finding: None (PASS)

Verdict: REWORK
  Critical: 1 (flaky test - time.sleep)
  High: 1 (CHANGELOG missing)
  Medium: 2 (docstring + DRY refactor)

Recommendation:
  1. Replace time.sleep(1) with mock.patch('time.time') or freeze_time fixture
  2. Add entry to CHANGELOG.md under "[Unreleased]"
  3. Add docstring to test_combine_score_minimal
  4. (Optional) extract scoring assertion helper to reduce duplication

Status update: IN_PROGRESS (rework required)
```

### Anti-patterns (FORBIDDEN detection & prevention)

```bash
# A1: Approve WITHOUT running tests (review bypasses quality gates)
# DETECTION: Verdict=CLEAN but test status unknown
# FIX: Verify test report exists AND status=PASS before verdict
LATEST_TEST=$(ls -t {WORK_ROOT}/reports/test-${WIP_ITEM}-*.md 2>/dev/null | head -1)
if [ -z "$LATEST_TEST" ]; then
  echo "STOP: no test report for $WIP_ITEM — run fabric-test first"
  exit 1
fi

# A2: CRITICAL findings with CLEAN verdict (contradiction)
# DETECTION: Grep for severity:CRITICAL + verdict:CLEAN mismatch
CRITICAL_COUNT=$(grep -c 'severity: CRITICAL' {REPORT_FILE} 2>/dev/null || echo 0)
VERDICT=$(grep '^verdict:' {REPORT_FILE} | awk '{print $2}')
if [ "$CRITICAL_COUNT" -gt 0 ] && [ "$VERDICT" = "CLEAN" ]; then
  echo "FAIL: $CRITICAL_COUNT CRITICAL findings but verdict is CLEAN → contradiction"
  exit 1
fi

# A3: Missing R1–R9 dimensions in report
# DETECTION: Report doesn't have all 9 dimension scores
# FIX: Ensure all R1–R9 present (R9 can be SKIPPED but must be documented)
for DIM in R1 R2 R3 R4 R5 R6 R7 R8 R9; do
  if ! grep -q "^## $DIM\|^| $DIM " {REPORT_FILE}; then
    echo "FAIL: Dimension $DIM missing in report"
    exit 1
  fi
done
```

## § 8 Quality Gates

**Blocking validation (MUST PASS):**

```bash
# 1. Report exists and has valid frontmatter
REPORT="{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-*.md"
if ! grep -q "^schema: fabric.report.v1" "$REPORT"; then
  echo "FAIL: Report missing fabric.report.v1 schema"
  exit 1
fi

# 2. Verdict is valid (CLEAN|REWORK|REDESIGN)
VERDICT=$(grep "^Verdict:" "$REPORT" | awk '{print $2}')
if ! echo "$VERDICT" | grep -qE "^(CLEAN|REWORK|REDESIGN)$"; then
  echo "FAIL: Invalid verdict: $VERDICT"
  exit 1
fi

# 3. CRITICAL findings must not exist in CLEAN verdict
CRITICAL_COUNT=$(grep -c "CRITICAL" "$REPORT" || echo 0)
if [ "$CRITICAL_COUNT" -gt 0 ] && [ "$VERDICT" = "CLEAN" ]; then
  echo "FAIL: CRITICAL findings present but verdict is CLEAN"
  exit 1
fi

# 4. All R1–R9 dimensions scored (R9 can be SKIPPED)
for dim in R1 R2 R3 R4 R5 R6 R7 R8; do
  if ! grep -q "^## $dim\|^| $dim " "$REPORT"; then
    echo "FAIL: Dimension $dim not found in report"
    exit 1
  fi
done

echo "PASS: Review report validation successful"
```

## § 9 Report template (povinné)

**Frontmatter:**
```yaml
---
title: "Review Report - {WIP_ITEM}"
version: "1.0"
date: "{YYYY-MM-DD}"
wip_item: "{WIP_ITEM}"
wip_branch: "{WIP_BRANCH}"
schema: "fabric.report.v1"
verdict: "CLEAN|REWORK|REDESIGN"
---
```

**Mandatory sections:**

```markdown
## Executive Summary
**Verdict:** [CLEAN|REWORK|REDESIGN] ✓/❌

[1 sentence summary of result]

## Gate Results
- Linting: PASS|FAIL|SKIPPED
- Format: PASS|FAIL|SKIPPED
- Tests: PASS|FAIL

## R1–R9 Summary Table
| Dimension | Score | Status |
|-----------|-------|--------|
| R1 Correctness | N/100 | PASS|MEDIUM|HIGH findings |
| ... (R2–R9) |

## Findings (per dimension)
### R1 Correctness (N/100)
[Concrete findings with file:line, severity, fix procedure]

### R2–R9 (similarly)

## Summary & Recommendations
[Next steps if REWORK/REDESIGN]
```

See `references/examples.md` for complete example with LLMem data.

## § 10 Self-check (povinné)

Before submitting report:

- [ ] Report exists with valid fabric.report.v1 schema
- [ ] Verdict (CLEAN|REWORK|REDESIGN) is explicitly declared
- [ ] R1–R9 tabulka je přítomna (žádné vynechané dimenze)
- [ ] Všechny CRITICAL findings mají fix procedure s file:line + effort
- [ ] Backlog item aktualizován s review_report + updated + status
- [ ] Protocol log má START + END záznam
- [ ] Žádné soubory mimo reports/ nejsou modifikovány (review je read-only)
- [ ] Git working tree NENÍ změněn (no commits)

### Final Checkpoint — BLOCKING ENFORCEMENT

```bash
REPORT="{WORK_ROOT}/reports/review-*.md"
REPORT_FILE=$(ls -t $REPORT 2>/dev/null | head -1)

if [ -z "$REPORT_FILE" ]; then
  echo "❌ CRITICAL: Review report not found"; exit 1
fi
if ! grep -q "^verdict:" "$REPORT_FILE"; then
  echo "❌ CRITICAL: Verdict missing in report"; exit 1
fi
if ! grep -q "r1_score:" "$REPORT_FILE"; then
  echo "❌ CRITICAL: R1-R9 scores missing"; exit 1
fi

CRITICAL_COUNT=$(grep -c "severity: CRITICAL" "$REPORT_FILE" 2>/dev/null || echo 0)
VERDICT=$(grep "^verdict:" "$REPORT_FILE" | awk '{print $2}')
if [ "$CRITICAL_COUNT" -gt 0 ] && [ "$VERDICT" = "CLEAN" ]; then
  echo "❌ CRITICAL: CLEAN verdict with $CRITICAL_COUNT CRITICAL findings → mismatch"; exit 1
fi

echo "✅ Self-check PASS: report valid, verdict=$VERDICT, criticals=$CRITICAL_COUNT"
```

- ❌ CRITICAL: Report not found → **EXIT 1**
- ❌ CRITICAL: Verdict missing → **EXIT 1**
- ❌ CRITICAL: R1-R9 scores missing → **EXIT 1**
- ❌ CRITICAL: CLEAN + CRITICAL findings mismatch → **EXIT 1**

## § 11 Failure Handling

**Failure scenarios:**

| Scenario | Action |
|----------|--------|
| Precondition fails (missing WIP item, test report) | Create intake item, exit 1 |
| Rework counter ≥3 | Verdikt = REDESIGN, exit 1 |
| Gates timeout (>120s) | Mark gate as TIMEOUT, investigate infra issue, create intake |
| ADR/spec violation detected | Mark as CRITICAL, verdict = REWORK or REDESIGN |
| Process-chain test fails | Mark as CRITICAL (R9), verdict = REWORK/REDESIGN |
| Report validation fails (§8) | Fix report, re-validate |

**Non-blocking warnings:**

- Pre-existing lint/format issues → gate = PASS, create intake item for pre-existing
- Missing process-map.md → R9 = SKIPPED (fail-open)
- Missing docstring on private function → R7 = MEDIUM (not CRITICAL)

## § 12 Metadata & Contract

**Downstream consumers:**

- **fabric-close**: reads verdict, gate_results, critical_findings_count
- **fabric-loop**: reads verdict to determine next action (CLEAN→DONE, REWORK→IN_PROGRESS, REDESIGN→BLOCKED)
- **intake**: systemic findings feed into sprint backlog

**Key fields (mandatory in report):**

```yaml
verdict: CLEAN|REWORK|REDESIGN
r1_score: 0-100
r2_score: 0-100
...
r9_score: 0-100
critical_findings_count: N
gate_results:
  lint_pass: bool
  format_pass: bool
  test_pass: bool
findings:
  - dimension: R1-R9
    severity: CRITICAL|HIGH|MEDIUM|LOW
    file_line: "path:NNN"
    description: "..."
    fix_procedure: "..."
    estimated_effort: "Xmin|Xh"
```

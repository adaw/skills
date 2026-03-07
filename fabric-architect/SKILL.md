---
name: fabric-architect
description: "Performs comprehensive architectural analysis across 20 dimensions (Coherence, Modularity, Scalability, Evolution) and produces weighted health scores with evidence-based findings. Identifies structural debt and principle violations to guide refactoring priorities."
tags: [fabric, architecture, analysis, health-scoring]
depends_on: [fabric-status]
feeds_into: [fabric-process, fabric-gap, fabric-sprint]
---
<!-- built from: builder-template -->

# fabric-architect

Performs comprehensive architectural analysis across 20 dimensions (Coherence, Modularity, Scalability, Evolution). Produces weighted health score with evidence-based findings and backlog mutations.

---

## §1 Účel

**Primary Goal:** Perform comprehensive architectural assessment of the codebase against design vision, identifying structural debt, principle violations, and roadmap blockers.

**Why It Matters:** Without systematic architectural review, technical debt accumulates silently. Decisions become fragmented. Future features face unexpected coupling issues. The codebase drifts from its stated vision.

**Scope:** All 20 dimensions across 4 groups with weighted scoring (0-100 overall). Generates evidence-based backlog mutations.

**Variants:**
- **default** (with backlog mutations): Full analysis + concrete T0/T1 refactoring tasks
- **--no-fix** (read-only): Analysis only, zero mutations created
- **--focus={area}**: Deep dive on single group (KOHERENCE|MODULARITA|ŠKÁLOVATELNOST|EVOLUCE)
- **--strategy={mode}**: FAST (breadth-first scanning) | DEEP (line-by-line audit) | RISK (focus on > 40-score areas)

---

## Downstream Contract

**Kdo konzumuje výstupy fabric-architect a jaká pole čte:**

- **fabric-process** reads:
  - Architectural health score (0-100) → context for process-level risk assessment
  - Module dependency findings → identifies tightly-coupled modules where process changes are risky
  - Backlog mutations → new T0/T1 refactoring tasks to plan around

- **fabric-gap** reads:
  - Per-dimension scores (A0-A19) → dimensions scoring <50 indicate architectural gaps
  - Evidence-based findings → cross-reference with vision goals to detect structural gaps
  - `reports/architect-*.md` field: `overall_score`, `critical_findings[]`, `mutations[]`

- **fabric-sprint** reads:
  - Backlog mutations from architect → include in sprint target selection
  - Dimension priority → dimensions with lowest scores get sprint attention first

- **fabric-implement** reads:
  - Module dependency map → knows which modules are tightly coupled before making changes
  - Anti-pattern findings → avoids introducing patterns architect flagged

**Contract fields in report:**
```yaml
overall_score: float        # 0-100 weighted score
dimensions: [{id, name, score, evidence}]  # A0-A19
critical_findings: [{file, line, dimension, severity, description}]
mutations: [{slug, type, tier, effort, description}]
```

---

## §2 Protokol

```bash
# START
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "architect" --event start

# ... architectural analysis (A0-A19) ...

# END
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "architect" --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/architect-{YYYY-MM-DD}.md"
```

Outputs:
- START timestamp
- Per-phase progress markers (A0-A5)
- Quality gate results
- END timestamp + overall verdict

---

## §3 Preconditions (bash code)

All preconditions MUST be met. Skill STOPs at first missing dependency.

```bash
# 1. config.md exists (stores project-specific configuration)
test -f config.md || { echo "STOP: config.md missing"; exit 1; }

# 2. state.md exists (tracks architectural state from prior runs)
test -f state.md || { echo "STOP: state.md missing"; exit 1; }

# 3. vision.md exists (CRITICAL — architect scores against principles)
test -f vision.md || {
  echo "STOP: vision.md missing — architect cannot score without vision principles"
  exit 1
}

# 4. backlog/ directory exists (for mutations + cross-reference)
test -d backlog/ || { echo "STOP: backlog/ directory missing"; exit 1; }

# 5. CODE_ROOT exists and has .py files
CODE_ROOT="${CODE_ROOT:-.}"
test -d "$CODE_ROOT" || { echo "STOP: CODE_ROOT not found"; exit 1; }
find "$CODE_ROOT" -name "*.py" -type f | head -1 > /dev/null || {
  echo "STOP: No .py files found in CODE_ROOT";
  exit 1;
}

echo "✓ All preconditions met"
```

**Dependency Chain:**
```
fabric-init → [fabric-intake →] fabric-architect
```

Architect can run after init alone, but intake may feed intake items for A3 cross-check.

---

## §4 Vstupy

**Povinné (Required):**
- `config.md` — Project configuration and build context
- `state.md` — Prior architectural state (for drift detection)
- `vision.md` — 8 design principles + roadmap (CRITICAL)
- `{CODE_ROOT}` — All source files (from config.md CODE_ROOT path)
- `{WORK_ROOT}/backlog/` — Directory with task hierarchy

**Volitelné (Optional):**
- `{WORK_ROOT}/{DECISIONS_ROOT}/` — ADR files (scored in A19)
- `{WORK_ROOT}/{SPECS_ROOT}/` — Specification documents (scored in A3)
- `reports/` — Previous architect reports (for trend analysis)

---

## §5 Výstupy

**Primární (Primary):**
- `reports/architect-{YYYY-MM-DD}.md` — Full report (schema: `fabric.report.v1`)
  - Includes: all dimension scores, evidence, findings, verdict
  - Dimensions: 20 (A0-A19)
  - Mutations count + details

**Vedlejší (Secondary):**
- `reports/adr/{ADR_ID}.md` — Generated ADR files for undocumented decisions (A19)
- Backlog mutations (in default mode only):
  - New `backlog/T0-architect-*.md` refactoring tasks
  - New `backlog/T1-architect-*.md` blocking features
  - Priority shifts + dependency marks

**No code files modified** — architect is analysis-only.

---

## §6 FAST PATH

**Quick Context Gathering (< 2 min):**

1. **Backlog Index:**
   ```bash
   find backlog/ -name "*.md" | xargs grep -l "^# T[0-3]:" | wc -l
   ```
   Output: Count of T0-T3 epics

2. **Governance Index:**
   ```bash
   find "${WORK_ROOT}/${DECISIONS_ROOT}" -name "*.md" 2>/dev/null | wc -l
   find "${WORK_ROOT}/${SPECS_ROOT}" -name "*.md" 2>/dev/null | wc -l
   ```
   Output: Count of ADRs and specs

3. **Module Inventory:**
   ```bash
   find $CODE_ROOT -name "*.py" -type f | wc -l
   find $CODE_ROOT -name "*.py" -type f -exec wc -l {} + | tail -1
   ```
   Output: File count + total LOC

4. **Import Graph (sample):**
   ```bash
   grep -rn "^from\|^import" $CODE_ROOT/ --include="*.py" | head -20
   ```
   Output: Import patterns for quick dependency scan

---

## §7 Postup (Overview)

Detailed scanning procedures, dimension definitions, and scoring criteria are in references/:

**7.1) A0: Pre-flight (Context Load)**
- Load vision.md principles, scan backlog epics, inventory code structure.
- See: [references/workflow.md § 7.1](references/workflow.md#71-a0-pre-flight-context-load)

**7.2) A1: Principle Alignment (per principle scoring)**
- For EACH of the 8 principles from vision.md, assess codebase adherence.
- Dimension definitions: [references/dimensions.md § GROUP 0](references/dimensions.md#group-0-principles--a0)
- See: [references/workflow.md § 7.2](references/workflow.md#72-a1-principle-alignment-per-principle-scoring)

**7.3) A2: Architectural Scanning (A1-A19 dimensions)**
- Evaluate all 19 remaining dimensions across 4 groups (Coherence, Modularity, Scalability, Evolution).
- All 20 dimensions: [references/dimensions.md](references/dimensions.md)
- Scoring + evidence: [references/workflow.md § 7.3](references/workflow.md#73-a2-architectural-scanning-a1-a19-dimensions)

**7.4) A3: Backlog Cross-Check**
- For each T1/T2/T3 epic, assess if current architecture supports building it.
- Example: [references/examples.md § Backlog Assessment (WQ2 fix)](references/examples.md#backlog-cross-check-example-llmem-wq2-fix)
- See: [references/workflow.md § 7.4](references/workflow.md#74-a3-backlog-cross-check)

**7.5) A4: Synthesis & Scoring**
- Calculate weighted overall score, determine verdict, identify cross-dimensional insights.
- Scoring formula: [references/workflow.md § 7.5](references/workflow.md#75-a4-synthesis--scoring)
- Weight justification: [references/workflow.md § Weight Table](references/workflow.md#weight-justification-table)

**7.6) A5: Mutations (default mode only)**
- Generate concrete backlog changes based on findings.
- Mutation spec template: [references/workflow.md § 7.6](references/workflow.md#76-a5-mutations-default-mode-only)
- See: [references/workflow.md § 7.6](references/workflow.md#76-a5-mutations-default-mode-only--skip-if---no-fix)

**Anti-patterns with detection bash:** [references/workflow.md § Anti-patterns](references/workflow.md#anti-patterns-with-detection-bash--fix-procedures-wq4)

---

## §8 Quality Gates

**All gates MUST PASS. Skill reports failure mode if any gate fails.**

| Gate | Criterion | PASS | FAIL |
|------|-----------|------|------|
| **Gate 1: Dimension Coverage** | All 20 dimensions (A0-A19) have scores | 20/20 scored | <20 scored → FAIL |
| **Gate 2: Evidence Requirement** | Each score backed by file:line refs (not vague) | ≥95% of scores have evidence | <80% with evidence → FAIL |
| **Gate 3: Scoring Consistency** | Self-verify: scored dimensions based on actual code read, not assumptions | All dimensions justified | Any dimension scored without reading → FAIL |
| **Gate 4: Mutation Validity (default mode only)** | All new backlog items have acceptance criteria + estimate | All mutations meet spec | Any mutation vague → FAIL (report issue, don't create) |

**On gate failure:**
- Report which gate failed
- Stop before creating mutations (if applicable)
- List violations preventing progress
- Guidance for operator: what to fix

---

## §9 Report

**Output file:** `reports/architect-{YYYY-MM-DD}.md`

**Schema:** fabric.report.v1

**Fields:**
```yaml
kind: architect
title: "Architectural Analysis Report"
date: 2026-03-05
codebase: "project"
version: "1.0"
run_id: "architect-2026-03-05-abc123"
created_at: "2026-03-05T14:30:00Z"
status: "PASS"
version_hash: "{git_commit_hash_or_state_hash}"

summary:
  overall_score: 76
  verdict: "NEEDS ATTENTION"
  dimensions_scored: 20
  critical_findings: 3
  mutations_count: 4
  adrs_created: 2

dimension_scores:
  coherence:
    - {dim: "A1: Layer Isolation", score: 88, severity: "🟢 GOOD"}
    - {dim: "A2: Message Flow", score: 92, severity: "🟢 EXCELLENT"}
    ...

critical_findings:
  - {dim: "A16: Observability", issue: "...", fix: "...", severity: "CRITICAL"}

mutations:
  - {type: "T0", title: "...", status: "created"}
```

**Include in report body:**
- Full dimension scoring table (A0-A19)
- Evidence sections (file:line references)
- Top-5 critical findings with remediation
- Cross-dimensional insights
- Mutation summary (T0/T1 count, each with estimate)
- Verdict explanation

---

## §10 Self-check (12+ items)

**Run before completing skill:**

**Existence Checks:**
- [ ] Report file `reports/architect-{YYYY-MM-DD}.md` created
- [ ] All mutations written to `backlog/` (if default mode)
- [ ] ADR files created for undocumented decisions (if A19 < 80)
- [ ] Protocol log has START and END timestamps
- [ ] Backlog index updated with new items + counts

**Quality Checks:**
- [ ] All 20 dimensions scored (A0-A19)
- [ ] Weighted formula correctly applied
- [ ] Each CRITICAL (🔴) finding has corresponding T0 mutation (default mode)
- [ ] Evidence is file:line specific, not vague
- [ ] Verdict matches score range (≥80 → SOLID, <40 → REDESIGN, etc.)
- [ ] Cross-dimensional insights table present (≥3 insights)

**Invariant Checks:**
- [ ] Zero code files modified (architect is read-only analysis)
- [ ] Only mutations: backlog files, ADR files, report file
- [ ] In --no-fix mode: zero backlog mutations created (only report)
- [ ] All new backlog items in `backlog/` with proper filename (`T0-architect-*.md`)
- [ ] No external API calls (all analysis local)

---

## §11 Failure Handling

| Phase | Error | Action |
|-------|-------|--------|
| **Preconditions** | vision.md missing | STOP immediately — cannot score without vision principles. Log: "CRITICAL: vision.md required." Exit code 1. |
| **Pre-flight (A0)** | No .py files found | STOP — nothing to analyze. Log error, exit code 1. |
| **A1 Scanning** | Cannot parse file (syntax error) | WARN + skip file + note in report "File skipped due to parse error: {file}". Continue with other files. |
| **A2-A4 Scanning** | Confidence <50% on >50% of dimensions | REPORT WARN in final report: "High uncertainty on this analysis. Confidence: 50%. Consider manual review." Mark those dimensions LOW confidence. |
| **Mutation Creation (default mode)** | Cannot write to backlog/ | WARN + list mutations in report with message: "Mutations not created. Apply manually:" + show each mutation spec. |
| **Report Write Failure** | Cannot create reports/ directory | STOP + exit. Log: "Cannot write report — check permissions." Exit code 1. |

**Operator Guidance on Errors:**
- Missing precondition → fix precondition, re-run skill
- Parse error → fix syntax, re-run skill
- Low confidence → manually review hotspots; re-run with --strategy=DEEP
- Backlog write fail → manually apply mutations from report

---

## §12 Metadata

```yaml
phase: orientation
step: architect
skills:
  - fabric-architect (this skill)
dependencies_required:
  - fabric-init (must run first)
dependencies_optional:
  - fabric-intake (if new observations to triage)
depends_on: [fabric-init, fabric-vision]
feeds_into: [fabric-process, fabric-gap, fabric-sprint, fabric-implement]
may_modify_state: false
may_modify_backlog: true    # default mode only — creates T0/T1 items, ADRs, priority shifts
may_modify_code: false      # architect is read-only; never modifies source
may_create_intake: true     # can generate new intake items if observations found
output_kind: report
output_schema: fabric.report.v1
report_fields:
  - kind: architect
  - score: 0-100
  - verdict: SOLID|NEEDS_ATTENTION|REFACTOR_FIRST|REDESIGN
  - dimensions_scored: 20
  - mutations_count: 0-N
  - critical_findings: list
runtime_limit: 5 minutes  # analysis should complete quickly; anything longer suggests bugs in scanning
cron_schedule: "null"     # manual trigger only (not a background job)
runs_in_session: true     # operates within fabric planning session
isolation: full           # no side effects beyond backlog + report
repeatable: true          # can re-run; will overwrite prior report
```

---

## Closure Notes

**fabric-architect** is the architectural quality gatekeeper. It runs after `fabric-init`, scans the codebase against the vision, and surfaces debt systematically.

Without it: architecture silently drifts. Decisions fragment. Refactoring becomes reactive ("it's broken") instead of proactive ("we planned this").

With it: every decision is scored, every blocker is documented, every mutation is concrete.

Workflow:
```
fabric-init
   ↓
fabric-architect (you are here)
   ↓
fabric-prio (prioritizes backlog using architect findings)
   ↓
fabric-sprint (selects features/refactoring mix for next cycle)
```

---

**End of SKILL.md**

---
name: fabric-gap
description: "Detect gaps between vision, backlog, and reality (code, tests, docs). Produces a gap report and generates actionable intake items (source=gap) for the most important missing pieces (features, tests, docs, security, reliability)."
depends_on:
  - fabric-process
---

# GAP — Mezera mezi vizí, backlogem a realitou

## Účel

Porovnat:
1) **Vizi** (`{WORK_ROOT}/vision.md`) — co má existovat a proč  
2) **Backlog** (`{WORK_ROOT}/backlog.md` + items) — co je naplánované  
3) **Realitu** (`{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`) — co fakt existuje

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-gap" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-gap" --event end --status OK --report "{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


A z toho vytvořit:
- `reports/gap-*.md`
- 0..N intake itemů (top gaps), které posunou projekt správným směrem

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md`
- `{WORK_ROOT}/backlog.md` + `{WORK_ROOT}/backlog/*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`
- `{WORK_ROOT}/fabric/processes/process-map.md` (optional)

---

## Výstupy

- `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- intake items v `{WORK_ROOT}/intake/` dle `{WORK_ROOT}/templates/intake.md`:
  - `source: gap`
  - `initial_type` typicky Task/Chore/Bug
  - `raw_priority` podle dopadu

## Downstream Contract

**fabric-process** (next skill) reads the following from gap report:
- `findings[]` — list of all identified gaps with structure:
  - `gap_id` (string) — unique identifier (e.g., "G-001")
  - `type` (enum) — gap category (Vision→Backlog, Backlog→Code, Code→Tests, Code→Docs, Security, Operational)
  - `severity` (enum) — CRITICAL | HIGH | MEDIUM | LOW
  - `root_cause` (enum) — DEFERRED | BLOCKED | OVERSIGHT | CAPACITY
  - `evidence` (string) — file path or missing artifact reference
  - `impact` (string) — business/technical impact description
  - `priority` (float) — computed PRIORITY score
- `critical_findings_count` (int) — number of CRITICAL severity findings
- `intake_items_created[]` (list of file paths) — references to generated intake items
- `test_status` (enum) — PASS | FAIL | TIMEOUT
- `stub_count` (int) — count of unimplemented functions found in code

---

## Příklady vyplněných gap reportů

### Příklad 1: Gap Report — Security & Validation Gaps

```yaml
---
title: “Gap Report - 2026-03-06”
version: “1.0”
date: “2026-03-06”
status: “CRITICAL_FINDINGS_PRESENT”
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

### Příklad 2: Gap Report — Missing Feature & Backlog Drift

```yaml
---
title: “Gap Report - 2026-02-28”
version: “1.0”
date: “2026-02-28”
status: “HIGH_PRIORITY_BACKLOG_DRIFT”
gap_count: 5
critical_gaps: 1
---

## Summary

**Coverage:** 20 of 22 capabilities. Vision includes “Semantic Embeddings” (T1 goal) but backlog has no READY items for it.
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

## Postup

### 1) Extrahuj „capabilities” z vize

Z `vision.md` + `{VISIONS_ROOT}/*.md` vytáhni seznam:
- pillars / goals / must-haves (z core vision)
- rozšířené cíle a detaily z sub-vizí

Výsledek: 5–30 capabilities (krátké názvy).

### 2) Mapuj backlog coverage

- Z backlog indexu vezmi top itemy a zjisti, jestli odkazují na capability.
- Pokud backlog itemy nejsou explicitně tagované, mapuj heuristicky podle title/keywords.

Výsledek: capability → {backlog IDs}

### 3) Reality check (code, tests, docs)

Pro každou capability:
- **Code existence signal:** existuje relevantní modul/entrypoint?
- **Tests signal:** existují testy pro klíčové chování?
- **Docs signal:** je to popsáno v docs?

Neřeš přesné coverage číslo; stačí kvalitativní „Yes/No/Unknown” + evidence.

**Test execution pro reality check (POVINNÉ):**

Nečti jen soubory — SPUSŤ testy, abys zjistil REÁLNÝ stav:

```bash
# Quick test run pro reality check (ne plný test suite — jen smoke)
if [ -n “{COMMANDS.test}” ] && [ “{COMMANDS.test}” != “TBD” ]; then
  echo “Running quick test for gap reality check...”
  timeout 120 {COMMANDS.test} -x --tb=line -q 2>/dev/null | tail -5
  GAP_TEST_EXIT=$?
  if [ $GAP_TEST_EXIT -eq 0 ]; then
    GAP_TEST_STATUS=”PASS”
  elif [ $GAP_TEST_EXIT -eq 124 ]; then
    GAP_TEST_STATUS=”TIMEOUT”
  else
    GAP_TEST_STATUS=”FAIL”
    # Extrahuj failing test names pro gap mapping
    FAILING_TESTS=$(timeout 120 {COMMANDS.test} --tb=no -q 2>/dev/null | grep FAILED | head -10)
  fi
  echo “Gap reality check: $GAP_TEST_STATUS”
fi

# Stub detection v kódu (IMPROVED: exclude test files and comments)
STUBS=$(grep -rn '^\s*pass$\|^\s*raise NotImplementedError' {CODE_ROOT}/src --include='*.py' 2>/dev/null | grep -v __pycache__)
STUB_COUNT=$(echo “$STUBS” | grep -c '\S' || echo 0)
if [ “$STUB_COUNT” -gt 0 ]; then
  echo “Found $STUB_COUNT implementation stubs in code”
  echo “$STUBS” | head -5  # Show top-5 stubs
fi
```

Zapiš test výsledek + stub count do gap reportu. Pokud testy FAILují → gap je REÁLNÝ (ne jen “soubor chybí”).

**ROOT CAUSE IDENTIFICATION (POVINNÉ):**

Pro každou identifikovanou mezeru určete ROOT CAUSE:

| Gap | Root Cause | Evidence | Category | Impact |
|-----|-----------|----------|----------|--------|
| Missing async validation | DEFERRED: PR #123 waiting review | src/llmem/api/routes/capture.py:TODO_ASYNC | DEFERRED | Blocks T1: Semantic Embeddings |
| No rate limiting | OVERSIGHT: Slipped in sprint planning | No rate_limit in imports | OVERSIGHT | DOS vulnerability on /capture |
| Incomplete ADR-001 | CAPACITY: Not scheduled yet | 60% of ADR-001 applied | CAPACITY | Tech debt on distributed deploy |
| Security audit gaps | BLOCKED: Waiting for external firm | No security.md + no review checklist | BLOCKED | P0 untracked security issue |

**Root Cause Categories:**
- `DEFERRED` — Planned, approved, waiting implementation
- `BLOCKED` — Waiting external dependency or decision
- `OVERSIGHT` — Slipped through cracks; add to backlog
- `CAPACITY` — Lower priority; scheduled for later

### 4) Identifikuj gap typy

Vyrob seznam gaps:

A) Vision → Backlog gap
- capability nemá žádné backlog items

B) Backlog → Code gap
- backlog item status READY/IN_PROGRESS, ale kód/relevantní soubory neexistují (nebo jsou stub)

C) Code → Tests gap
- změny bez testů, kritické moduly bez test coverage signálu

D) Code → Docs gap
- public API / usage není dokumentované

E) Security/Operational gap
- chybí input validation, secrets hygiene, logging, error handling, etc.

**CONCRETE SECURITY GAP CHECKS (POVINNÉ):**

Proveď tyto konkrétní bezpečnostní kontroly:

```bash
# 1. Input Validation: Check endpoints without Pydantic validation
echo "=== INPUT VALIDATION CHECK ==="
UNVALIDATED=$(grep -rn "def " {CODE_ROOT}/src/llmem/api/routes --include="*.py" | \
  while read line; do
    file=$(echo "$line" | cut -d: -f1)
    grep -L "Pydantic\|ValidationError\|BaseModel" "$file" 2>/dev/null
  done | sort -u)
if [ -n "$UNVALIDATED" ]; then
  echo "SECURITY GAP: Endpoints without Pydantic validation:"
  echo "$UNVALIDATED"
fi

# 2. Auth Guards: Check routes without auth decorators
echo "=== AUTH GUARD CHECK ==="
NO_AUTH=$(grep -rn "^\s*@app.post\|^\s*@app.get" {CODE_ROOT}/src/llmem/api/routes --include="*.py" | \
  grep -v "@.*auth\|@.*require" | head -10)
if [ -n "$NO_AUTH" ]; then
  echo "SECURITY GAP: Routes missing auth decorators:"
  echo "$NO_AUTH" | head -5
fi

# 3. Hardcoded Secrets: Check for passwords, tokens, API keys
echo "=== HARDCODED SECRETS CHECK ==="
SECRETS=$(grep -rn "password\|secret\|token\|api_key" {CODE_ROOT}/src --include="*.py" | \
  grep -i "=\s*['\"].*['\"]" | grep -v "# " | head -10)
if [ -n "$SECRETS" ]; then
  echo "SECURITY GAP: Potential hardcoded secrets:"
  echo "$SECRETS" | head -5
fi

# 4. Rate Limiting: Check if rate limiter middleware exists
echo "=== RATE LIMITING CHECK ==="
if ! grep -rq "rate_limit\|RateLimiter\|throttle" {CODE_ROOT}/src --include="*.py"; then
  echo "SECURITY GAP: No rate limiting middleware found"
fi
```

Zapiš výsledky bezpečnostních kontrol do gap reportu.

### 5) Impact Analysis & Priority Formula

Před výběrem top gaps, proveď IMPACT ANALYSIS:

**Impact Levels:**
- `HIGH` — Blocks user workflow OR is security/data loss issue
- `MEDIUM` — Reduces code quality / team velocity / operational reliability
- `LOW` — Cosmetic / nice-to-have

**Priority Formula:**
```
PRIORITY = IMPACT_SCORE × (1 / EFFORT_DAYS) × FREQUENCY_MULTIPLIER

IMPACT_SCORE:  HIGH=10, MEDIUM=5, LOW=1
EFFORT_DAYS:   How many days to close gap (1..10)
FREQUENCY_MULTIPLIER: How often affects users (1=rarely, 2=sometimes, 3=every sprint)

Examples:
- HIGH impact, 1 day effort, 3x frequency: 10 × 1 × 3 = 30 (URGENT)
- MEDIUM impact, 2 day effort, 1x frequency: 5 × 0.5 × 1 = 2.5 (LOW)
- HIGH impact, 5 day effort, 2x frequency: 10 × 0.2 × 2 = 4 (MEDIUM)
```

**Intake Item Threshold:** Create intake item if **PRIORITY ≥ 15** (or if gap is CRITICAL). Lower-priority findings recorded in gap report but not escalated.

| Gap | Impact | Effort | Frequency | Priority | Root Cause | Reason |
|-----|--------|--------|-----------|----------|-----------|--------|
| No rate limiting on /capture | HIGH | 1 day | 3 (every sprint) | 30 (URGENT) | OVERSIGHT | DOS vulnerability, easy fix |
| Missing async validation | HIGH | 2 days | 2 (T1 blocks) | 10 (HIGH) | DEFERRED | Blocks Semantic Embeddings feature |
| Incomplete ADR-001 | MEDIUM | 3 days | 1 (once) | 1.7 (MEDIUM) | CAPACITY | Tech debt, not urgent |
| Sparse logging in hot path | MEDIUM | 2 days | 2 (every debug) | 5 (MEDIUM) | OVERSIGHT | Makes debugging hard |

**Gap Detection Bash for All Gap Types (POVINNÉ):**

```bash
# Vision→Backlog gap detection
echo "=== Vision→Backlog Gaps ==="
CAPABILITIES=$(grep -E '^## |^### ' {VISIONS_ROOT}/*.md 2>/dev/null | sed 's/:.*## //' | sort -u)
while IFS= read -r cap; do
  [ -z "$cap" ] && continue
  if ! grep -q "$cap" {WORK_ROOT}/backlog.md 2>/dev/null; then
    echo "GAP: Capability '$cap' from vision has NO backlog items"
    # Create intake item if PRIORITY ≥ 15
  fi
done <<< "$CAPABILITIES"

# Backlog→Code gap detection
echo "=== Backlog→Code Gaps ==="
grep -E 'status: (READY|IN_PROGRESS)' {WORK_ROOT}/backlog/*.md 2>/dev/null | while read -r item; do
  ITEM_FILE=$(echo "$item" | cut -d: -f1)
  ITEM_ID=$(basename "$ITEM_FILE" .md)
  # Check if code exists (heuristic: grep for item ID or title in src/)
  if ! grep -r "$ITEM_ID\|$(grep title "$ITEM_FILE" | head -1)" {CODE_ROOT}/src --include='*.py' | grep -qv test; then
    echo "GAP: Backlog item $ITEM_ID is READY but code not found in {CODE_ROOT}"
  fi
done

# Code→Tests gap detection
echo "=== Code→Tests Gaps ==="
MODIFIED_FILES=$(git diff {main_branch}...HEAD --name-only 2>/dev/null | grep src.*\.py)
while IFS= read -r file; do
  [ -z "$file" ] && continue
  MODULE=$(echo "$file" | sed 's|src/llmem/||' | sed 's/\.py//')
  TEST_FILE="{TEST_ROOT}/test_${MODULE}.py"
  if [ ! -f "$TEST_FILE" ]; then
    echo "GAP: Code changed in $file but test file $TEST_FILE not found"
  fi
done <<< "$MODIFIED_FILES"

# Code→Docs gap detection
echo "=== Code→Docs Gaps ==="
ENDPOINTS=$(grep -E "@app\.(get|post|put|delete)" {CODE_ROOT}/api/routes/*.py 2>/dev/null | grep -oP "(?<=['\"]).+?(?=['\"]\))" | sort -u)
while IFS= read -r endpoint; do
  [ -z "$endpoint" ] && continue
  if ! grep -q "$endpoint" {DOCS_ROOT}/*.md 2>/dev/null; then
    echo "GAP: Endpoint '$endpoint' in code but not documented in docs/"
  fi
done <<< "$ENDPOINTS"

# Security gaps already covered above in CONCRETE SECURITY GAP CHECKS section

# Operational gaps detection
echo "=== Operational Gaps ==="
if ! grep -q "logging\|logger" {CODE_ROOT}/api/server.py; then
  echo "GAP: API server.py has no logging configured"
fi
if ! grep -rq "timeout\|TIMEOUT" {CODE_ROOT}/api --include='*.py'; then
  echo "GAP: API routes missing timeout configuration"
fi
```

### 5.1) Vyber top 3–10 gaps a vytvoř intake items

Vyber top gaps podle PRIORITY (sestupně) a vytvoř intake item ({WORK_ROOT}/templates/intake.md):
- `title`: akční („Zavést rate limiting na /capture”, „Dopsat async validation”, „Dokumentovat CLI usage”)
- `source: gap`
- `initial_type`: Task/Bug/Chore/Spike
- `raw_priority`: 8–10 pro URGENT, 5–7 pro HIGH/MEDIUM

Do těla:
- Popis mezery (1 věta)
- Root Cause (DEFERRED/BLOCKED/OVERSIGHT/CAPACITY)
- Impact level (HIGH/MEDIUM/LOW)
- Evidence (soubor:řádek nebo chybějící artefakt)
- Doporučená akce + AC návrh

**Testovatelnost gap detection (P2 work quality):**
Každý identifikovaný gap musí mít:
- Konkrétní evidence (soubor:řádek nebo chybějící artefakt)
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Root Cause (DEFERRED/BLOCKED/OVERSIGHT/CAPACITY)
- Impact Level (HIGH/MEDIUM/LOW)
- Doporučená akce (ne jen “opravit” — konkrétně co a kde)
- Ověřitelné kritérium (jak poznat že gap je uzavřen)

### 5.5) Process Coverage Check

Ověř, že všechny zdokumentované externí procesy mají implementaci v kódu.

```bash
PROCESS_MAP=”{WORK_ROOT}/fabric/processes/process-map.md”

if [ ! -f “$PROCESS_MAP” ]; then
  echo “WARN: $PROCESS_MAP does not exist (optional input), skipping process coverage check”
else
  echo “Checking process coverage...”

  # Extrahuj dokumentované externí procesy ze process-map.md
  # Format: Předpokládá seznam externích procesů s jejich identifikátory
  DOCUMENTED_PROCESSES=$(grep -E '^- \[' “$PROCESS_MAP” | sed 's/^- \[//;s/\].*//' | sort | uniq)

  PROCESS_GAPS=0
  while IFS= read -r proc_id; do
    [ -z “$proc_id” ] && continue

    # Ověř, že proces má implementaci v {CODE_ROOT}
    # Hledej v config, handler registry, nebo process-specific modulech
    PROC_FOUND=$(grep -r “process.*$proc_id\|$proc_id.*handler” {CODE_ROOT}/ --include='*.py' 2>/dev/null | grep -v test | grep -v __pycache__ | head -1)

    if [ -z “$PROC_FOUND” ]; then
      echo “GAP: External process '$proc_id' documented but no implementation found in code”

      # Vytvoř intake item pro chybějící implementaci
      INTAKE_FILE=”{WORK_ROOT}/intake/process-impl-$proc_id-$(date +%s).md”
      cat > “$INTAKE_FILE” << 'EOF'
---
title: “Implement external process: $proc_id”
source: gap
initial_type: Task
raw_priority: 7
---

## Problem

External process `$proc_id` is documented in `fabric/processes/process-map.md` but has no implementation in the codebase.

## Evidence

- Documented in: `fabric/processes/process-map.md`
- Missing handler/implementation in `{CODE_ROOT}/`

## Acceptance Criteria

- [ ] Process handler created with clear input/output contracts
- [ ] Handler registered in configuration or process registry
- [ ] Basic tests verify handler can be invoked
- [ ] Documentation updated with implementation details

EOF
      PROCESS_GAPS=$((PROCESS_GAPS + 1))
    fi
  done <<< “$DOCUMENTED_PROCESSES”

  if [ $PROCESS_GAPS -gt 0 ]; then
    echo “Found $PROCESS_GAPS process coverage gaps”
  else
    echo “All documented processes have implementation coverage”
  fi
fi
```

### 6) Gap report

`reports/gap-{date}.md`:
- shrnutí: kolik capabilities má coverage
- tabulka gaps (severity + evidence)
- seznam vytvořených intake items

---

## Complete End-to-End Gap Detection Pipeline

Spusť tento bash skript pro deterministické zjištění VŠECH gap typů:

```bash
#!/bin/bash
set -e

echo "=== STARTING GAP DETECTION PIPELINE ==="

# 1. Vision→Backlog gaps
echo "Step 1: Detecting Vision→Backlog gaps..."
VISION_TO_BACKLOG_GAPS=$(
  grep -E '^## |^### ' {VISIONS_ROOT}/*.md 2>/dev/null | sed 's/:.*## //' | sort -u | while read cap; do
    [ -z "$cap" ] && continue
    if ! grep -q "$cap" {WORK_ROOT}/backlog.md 2>/dev/null; then
      echo "V2B_GAP: $cap"
    fi
  done
)
echo "Found Vision→Backlog gaps: $(echo "$VISION_TO_BACKLOG_GAPS" | grep -c 'V2B_GAP' || echo 0)"

# 2. Backlog→Code gaps
echo "Step 2: Detecting Backlog→Code gaps..."
BACKLOG_TO_CODE_GAPS=$(
  grep -E 'status: (READY|IN_PROGRESS)' {WORK_ROOT}/backlog/*.md 2>/dev/null | while read item; do
    ITEM_FILE=$(echo "$item" | cut -d: -f1)
    ITEM_ID=$(basename "$ITEM_FILE" .md)
    if ! grep -r "$ITEM_ID" {CODE_ROOT}/src --include='*.py' | grep -qv test; then
      echo "B2C_GAP: $ITEM_ID"
    fi
  done
)
echo "Found Backlog→Code gaps: $(echo "$BACKLOG_TO_CODE_GAPS" | grep -c 'B2C_GAP' || echo 0)"

# 3. Code→Tests gaps
echo "Step 3: Detecting Code→Tests gaps..."
CODE_TO_TEST_GAPS=$(
  find {CODE_ROOT}/src -name '*.py' -not -path '*/test*' | while read file; do
    MODULE=$(echo "$file" | sed "s|{CODE_ROOT}/src/||" | sed 's/\.py//')
    if [ ! -f "{TEST_ROOT}/test_${MODULE}.py" ] && [ ! -f "{TEST_ROOT}/test_$(basename $MODULE).py" ]; then
      # Heuristic: check if there are ANY tests for this module
      if ! grep -rq "$(basename "$file" .py)" {TEST_ROOT} --include='*.py'; then
        echo "C2T_GAP: $MODULE"
      fi
    fi
  done | head -10
)
echo "Found Code→Tests gaps (top 10): $(echo "$CODE_TO_TEST_GAPS" | grep -c 'C2T_GAP' || echo 0)"

# 4. Code→Docs gaps
echo "Step 4: Detecting Code→Docs gaps..."
CODE_TO_DOCS_GAPS=$(
  grep -rE "@app\.(get|post|put|delete)" {CODE_ROOT}/api/routes --include='*.py' 2>/dev/null | \
  grep -oP '(?<=["\'])/[a-zA-Z/_]*' | sort -u | while read endpoint; do
    [ -z "$endpoint" ] && continue
    if ! grep -q "$endpoint" {DOCS_ROOT}/*.md 2>/dev/null; then
      echo "C2D_GAP: $endpoint"
    fi
  done
)
echo "Found Code→Docs gaps: $(echo "$CODE_TO_DOCS_GAPS" | grep -c 'C2D_GAP' || echo 0)"

# 5. Security gaps (via CONCRETE SECURITY GAP CHECKS from above)
echo "Step 5: Detecting Security gaps..."
bash {WORK_ROOT}/scripts/security-gap-check.sh > /tmp/security-gaps.txt 2>&1 || true
SECURITY_GAPS=$(grep -c '^SECURITY GAP:' /tmp/security-gaps.txt || echo 0)
echo "Found Security gaps: $SECURITY_GAPS"

# 6. Operational gaps
echo "Step 6: Detecting Operational gaps..."
OPERATIONAL_GAPS=""
! grep -q "logging\|logger" {CODE_ROOT}/api/server.py && OPERATIONAL_GAPS="${OPERATIONAL_GAPS}LOGGING_MISSING "
! grep -rq "timeout\|TIMEOUT" {CODE_ROOT}/api --include='*.py' && OPERATIONAL_GAPS="${OPERATIONAL_GAPS}TIMEOUT_MISSING "
echo "Found Operational gaps: $OPERATIONAL_GAPS"

echo "=== GAP DETECTION COMPLETE ==="
```

Run this to get a structured summary of ALL gap types. Proceed to intake item creation for gaps with PRIORITY ≥ 15.

---

## Anti-patterns with Detection & Fix (§9)

**Anti-pattern A: Gap without root cause**
- Detection: `grep -E "^\| G-" reports/gap-*.md | grep -v "DEFERRED\|BLOCKED\|OVERSIGHT\|CAPACITY"`
- Fix: For every gap finding, add root cause classification. Review original backlog item/vision to determine: was it DEFERRED (conscious decision), BLOCKED (dependency), OVERSIGHT (missed), or CAPACITY (no bandwidth).

**Anti-pattern B: Vague gap evidence ("something is missing")**
- Detection: `grep -E "^\| G-" reports/gap-*.md | grep -vi "\.py\|\.md\|line\|endpoint\|route"`
- Fix: Every gap MUST reference a specific file:line, endpoint, or missing artefact. Replace vague descriptions with concrete pointers.

**Anti-pattern C: CRITICAL gap without intake item**
- Detection: `CRIT=$(grep -c "CRITICAL" reports/gap-*.md); INTAKE=$(ls intake/gap-* 2>/dev/null | wc -l); [ "$INTAKE" -lt "$CRIT" ] && echo "MISSING INTAKE"`
- Fix: For each CRITICAL gap, create intake item with: source=gap, severity=CRITICAL, actionable AC, estimated effort.

**Anti-pattern D: Duplicate gaps across sprints**
- Detection: `for f in reports/gap-*.md; do grep "^\| G-" "$f" | awk -F'|' '{print $3}'; done | sort | uniq -d`
- Fix: Merge duplicate gaps into single finding. If gap persists across 2+ sprints, escalate priority by +5 and add note "recurring gap".

**Anti-pattern E: Security gap left as MEDIUM when it should be CRITICAL**
- Detection: `grep -E "eval|exec|shell=True|pickle|SECRET|password" reports/gap-*.md | grep -v "CRITICAL"`
- Fix: Any security gap involving code execution (eval, exec, shell=True), deserialization (pickle), or credential exposure MUST be CRITICAL. Upgrade severity.

---

## Self-check (with BLOCKING validation)

- report existuje v `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- report obsahuje: Vision↔Backlog gaps, Backlog↔Code gaps, Code↔Tests gaps, Docs drift, Security/Operational gaps
- každé CRITICAL/HIGH gap má buď intake item, nebo explicitní vysvětlení proč ne
- počet intake items: 3–10

**BLOCKING Validation (WQ10 fix):**

```bash
# Validate gap report structure
REPORT="{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md"
if [ ! -f "$REPORT" ]; then
  echo "FAIL: Gap report does not exist"
  exit 1
fi

# Check required sections
for section in "Summary" "Gap Analysis" "Intake Items"; do
  if ! grep -q "^## $section" "$REPORT"; then
    echo "FAIL: Report missing required section: $section"
    exit 1
  fi
done

# Check that ALL findings have severity + confidence + root_cause
FINDING_COUNT=$(grep -c "^| " "$REPORT" || echo 0)
if [ "$FINDING_COUNT" -lt 1 ]; then
  echo "FAIL: Report has no findings table"
  exit 1
fi

# Validate CRITICAL findings create intake items
CRITICAL_COUNT=$(grep -c "CRITICAL" "$REPORT" || echo 0)
INTAKE_COUNT=$(ls {WORK_ROOT}/intake/gap-* 2>/dev/null | wc -l)
if [ "$CRITICAL_COUNT" -gt 0 ] && [ "$INTAKE_COUNT" -lt "$CRITICAL_COUNT" ]; then
  echo "FAIL: CRITICAL findings present but not all have intake items"
  exit 1
fi

echo "PASS: Gap report validation successful"
exit 0
```

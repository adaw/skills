# fabric-gap Workflow Reference

Detailní procedury, bash skripty, a anti-pattern checklist pro gap detection.

---

## Complete End-to-End Gap Detection Pipeline

Deterministický bash skript pro zjištění VŠECH gap typů:

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

# 5. Security gaps
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

Run this to get a structured summary of ALL gap types.

---

## Path Traversal Guard (K7: Input Validation)

Reject any input containing `..`:

```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic path inputs:
validate_path "$VISION_FILE"
validate_path "$GAP_REPORT"
```

---

## State Validation (K1: State Machine)

Ověř kompatibilitu s current phase:

```bash
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-gap. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

---

## Anti-patterns Detection & Fix

### Anti-pattern A: Gap bez root cause

**Detection:**
```bash
grep -E "^\| G-" reports/gap-*.md | grep -v "DEFERRED\|BLOCKED\|OVERSIGHT\|CAPACITY"
```

**Fix:** Pro každý gap finding přiřaď root cause klasifikaci:
- `DEFERRED` — conscious decision (na backlogu/PR, waiting implementation)
- `BLOCKED` — waiting external dependency or decision
- `OVERSIGHT` — slipped through cracks; add to backlog immediately
- `CAPACITY` — no bandwidth; scheduled for later sprint

---

### Anti-pattern B: Vágní gap evidence

**Detection:**
```bash
grep -E "^\| G-" reports/gap-*.md | grep -vi "\.py\|\.md\|line\|endpoint\|route"
```

**Fix:** Každý gap MUSÍ referencovat konkrétní file:line, endpoint, nebo chybějící artefakt:
- ❌ "Something is missing" → VÁGNÍ
- ✓ "POST /capture/event handler at api/routes/capture.py:line 45 has no Pydantic validation" → KONKRÉTNÍ

---

### Anti-pattern C: CRITICAL gap bez intake item

**Detection:**
```bash
CRIT=$(grep -c "CRITICAL" reports/gap-*.md)
INTAKE=$(ls intake/gap-* 2>/dev/null | wc -l)
[ "$INTAKE" -lt "$CRIT" ] && echo "MISSING INTAKE"
```

**Fix:** Pro každý CRITICAL gap vytvoř intake item:
- source=gap
- severity=CRITICAL (frontmatter tag)
- actionable AC
- estimated effort (1–5 days)

---

### Anti-pattern D: Duplicate gaps across sprints

**Detection:**
```bash
for f in reports/gap-*.md; do
  grep "^\| G-" "$f" | awk -F'|' '{print $3}'
done | sort | uniq -d
```

**Fix:**
1. Merguj duplicate gap findings do single entry
2. Pokud gap persists across 2+ consecutive sprints → escaluj priority +5 bodů
3. Přidej note: "recurring gap — priority escalated"

---

### Anti-pattern E: Security gap as MEDIUM, měl by být CRITICAL

**Detection:**
```bash
grep -E "eval|exec|shell=True|pickle|SECRET|password" reports/gap-*.md | grep -v "CRITICAL"
```

**Fix:** Upgrade severity na CRITICAL:
- Code execution (eval, exec, shell=True, os.system) ✓ CRITICAL
- Deserialization without validation (pickle, JSON.parse unsafe) ✓ CRITICAL
- Credential exposure (passwords, tokens, API keys in logs/code) ✓ CRITICAL
- Input validation bypass (SQL injection, XSS, command injection) ✓ CRITICAL
- Any gap rated CRITICAL ≥ 1 week blocked → escalate to incident handling

---

## Intake Item Creation Template

Pro každý top gap (PRIORITY ≥ 15 nebo CRITICAL severity), vytvoř:

```markdown
---
schema: fabric.intake_item.v1
title: "{Akční popis}"
source: gap
initial_type: {Task|Bug|Chore|Spike}
raw_priority: {8-10 pro URGENT, 5-7 pro HIGH/MEDIUM}
created: {YYYY-MM-DD}
status: new
linked_vision_goal: "{goal, pokud je zřejmé}"
---

## Problem

{1–2 věty o co je problema a proč to matters}

## Evidence

- Gap ID: {G-XXX}
- Root Cause: {DEFERRED|BLOCKED|OVERSIGHT|CAPACITY}
- Severity: {CRITICAL|HIGH|MEDIUM|LOW}
- Evidence file(s): {path:line nebo chybějící artefakt}

## Impact

{Jaký je business/technical dopad — 2–3 věty}

## Recommended Action

{Konkrétně co se má stát — ne jen "opravit"}

## Acceptance Criteria

- [ ] {Konkrétní, ověřitelné kritérium 1}
- [ ] {Konkrétní, ověřitelné kritérium 2}
- [ ] {Konkrétní, ověřitelné kritérium 3}

## Estimated Effort

{1-5 days, justify}
```

---

## Priority Formula Detail

```
PRIORITY = IMPACT_SCORE × (1 / EFFORT_DAYS) × FREQUENCY_MULTIPLIER

Vývoj:
- Pokud gap zablokuje release → +10 priority bonus
- Pokud security/compliance gap → +5 priority bonus
- Pokud blocuje T1 goal (ze vision.md) → +3 priority bonus
```

**Scoring table:**

| Impact | Score | Freq 1x | Freq 2x | Freq 3x |
|--------|-------|---------|---------|---------|
| HIGH (10) | 1 day | 10 | 20 | 30 |
| HIGH (10) | 2 days | 5 | 10 | 15 |
| HIGH (10) | 5 days | 2 | 4 | 6 |
| MEDIUM (5) | 1 day | 5 | 10 | 15 |
| MEDIUM (5) | 2 days | 2.5 | 5 | 7.5 |
| LOW (1) | 1 day | 1 | 2 | 3 |

**Rule:** Intake item pokud PRIORITY ≥ 15. Pokud < 15, zapiš do gap reportu ale nezačínej intake item.

---

## Security Gap Checklist (MUST RUN)

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

Record results in gap report. If any gap found → CRITICAL severity.

---

## Process Coverage Intake Template

Pokud proces je dokumentovaný ale bez implementace:

```markdown
---
schema: fabric.intake_item.v1
title: "Implement external process: {PROCESS_ID}"
source: gap
initial_type: Task
raw_priority: 7
created: {YYYY-MM-DD}
---

## Problem

External process `{PROCESS_ID}` is documented in `fabric/processes/process-map.md` but has no implementation in the codebase.

## Evidence

- Documented in: `fabric/processes/process-map.md`
- Missing handler/implementation in `{CODE_ROOT}/`

## Acceptance Criteria

- [ ] Process handler created with clear input/output contracts
- [ ] Handler registered in configuration or process registry
- [ ] Basic tests verify handler can be invoked
- [ ] Documentation updated with implementation details
```

---

## Testovatelnost Gap Detection (P2 work quality)

Každý identifikovaný gap MUSÍ mít:

- ✓ Konkrétní evidence (soubor:řádek nebo chybějící artefakt)
- ✓ Severity (CRITICAL/HIGH/MEDIUM/LOW)
- ✓ Root Cause (DEFERRED/BLOCKED/OVERSIGHT/CAPACITY)
- ✓ Impact Level (HIGH/MEDIUM/LOW)
- ✓ Doporučená akce (ne jen "opravit" — konkrétně co a kde)
- ✓ Ověřitelné kritérium (jak poznat že gap je uzavřen)

Pokud gap chybí některý z těchto — GAP REPORT se vrací k opravě.

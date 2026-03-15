# K10 Examples & Anti-patterns — fabric-design

## Inline Example — LLMem Batch Capture API

**Input:** Backlog item task-b015 "Add /capture/batch endpoint" (S effort): Accept POST with ≤100 observations, validate each, store deterministically, return 207 Multi-Status.
**Output:** Design with D1–D8: (D1) existing capture.py + triage flow understood, (D2) BatchCaptureRequest model with validators, (D3) endpoint signature POST /capture/batch with request/response schemas, (D4) integration flow diagram, (D5) config: BATCH_MAX_ITEMS=100, (D6) 3 test cases: happy path (3 items), edge case (100 items), error (1 invalid item mixed with valid), (D7) 2 alternatives (sequential vs parallel processing) + risks (rate limiting, memory), (D8) depends_on: triage.py stable, pydantic ≥2.0.

## Rework/Error Flow Example

**Input:** Design for task-b015 fails Gate 5 — governance conflict with ADR-007 (no batch endpoints without rate limiting).
**Flow:**
1. D7 identifies rate-limiting requirement from ADR-007
2. Gate 5 check: `grep 'ADR-007' {WORK_ROOT}/decisions/INDEX.md` → conflict detected
3. Design status remains DESIGN (not READY)
4. Intake item created: `{WORK_ROOT}/intake/design-fix-20260316.md` with title "Resolve ADR-007 rate-limiting requirement for batch endpoint"
5. Report status: WARN, governance_conflict: true
6. Next iteration: designer adds rate-limiting section to D5 (config: BATCH_RATE_LIMIT=100/min), re-runs design → Gate 5 PASS → status READY

## Anti-patterns (s detekcí)

```bash
# A1: Designing without reading existing code
# Detection: D1 section lacking 'read {CODE_ROOT}/' references
DESIGN_SPEC="{ANALYSES_ROOT}/${TASK_ID}-design.md"
if [ -f "$DESIGN_SPEC" ]; then
  D1_CODE_REFS=$(grep -c '{CODE_ROOT}\|src/' "$DESIGN_SPEC" 2>/dev/null || echo 0)
  if [ "$D1_CODE_REFS" -lt 1 ]; then
    echo "WARN: A1 — D1 section has no code references; design may lack context"
  fi
fi

# A2: Test cases without concrete input/output values
if [ -f "$DESIGN_SPEC" ]; then
  VAGUE_TESTS=$(grep -cE 'test.*pass|TODO|TBD' "$DESIGN_SPEC" 2>/dev/null || echo 0)
  if ! echo "$VAGUE_TESTS" | grep -qE '^[0-9]+$'; then VAGUE_TESTS=0; fi
  if [ "$VAGUE_TESTS" -gt 0 ]; then
    echo "FAIL: A2 — $VAGUE_TESTS vague test cases found (TODO/TBD in D6)"
    exit 1
  fi
fi

# A3: Pseudokód too vague (no numbered steps)
if [ -f "$DESIGN_SPEC" ]; then
  NUMBERED_STEPS=$(grep -cE '^[0-9]+\.' "$DESIGN_SPEC" 2>/dev/null || echo 0)
  if ! echo "$NUMBERED_STEPS" | grep -qE '^[0-9]+$'; then NUMBERED_STEPS=0; fi
  if [ "$NUMBERED_STEPS" -lt 3 ]; then
    echo "WARN: A3 — Only $NUMBERED_STEPS numbered pseudokód steps; complex logic needs ≥3"
  fi
fi

# A4: Missing alternatives or unjustified choices
if [ -f "$DESIGN_SPEC" ]; then
  if ! grep -qE 'Alternative|Alternativa|Pro/Con|pro/con' "$DESIGN_SPEC" 2>/dev/null; then
    echo "FAIL: A4 — No alternatives/pro-con table found in D7"
    exit 1
  fi
fi
```

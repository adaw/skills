---
name: fabric-design
description: "Convert READY/DESIGN backlog items into detailed implementation specifications: data models, components, APIs, configuration, tests, dependencies, risks, and alternatives. Bridge between vision and implementation preventing vague hand-offs."
---
<!-- built from: builder-template -->

# DESIGN — Implementační specifikace (deep design)

---

## K2 Fix: Design Section Counter

```bash
MAX_COMPONENTS=${MAX_COMPONENTS:-50}
COMPONENT_COUNTER=0

# Validate MAX_COMPONENTS is numeric (K2 tight validation)
if ! echo "$MAX_COMPONENTS" | grep -qE '^[0-9]+$'; then
  MAX_COMPONENTS=50
  echo "WARN: MAX_COMPONENTS not numeric, reset to default (50)"
fi

# K5: Design thresholds from config.md
MIN_TEST_CASES=$(grep 'DESIGN.min_test_cases:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MIN_TEST_CASES=${MIN_TEST_CASES:-3}
if ! echo "$MIN_TEST_CASES" | grep -qE '^[0-9]+$'; then MIN_TEST_CASES=3; fi
MAX_DEPS_PER_COMPONENT=$(grep 'DESIGN.max_deps_per_component:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MAX_DEPS_PER_COMPONENT=${MAX_DEPS_PER_COMPONENT:-5}
if ! echo "$MAX_DEPS_PER_COMPONENT" | grep -qE '^[0-9]+$'; then MAX_DEPS_PER_COMPONENT=5; fi
```

When iterating through components, API methods, or test cases in design:
```bash
while read -r component; do
  COMPONENT_COUNTER=$((COMPONENT_COUNTER + 1))

  # Numeric validation of counter (K2 strict check)
  if ! echo "$COMPONENT_COUNTER" | grep -qE '^[0-9]+$'; then
    COMPONENT_COUNTER=0
    echo "WARN: COMPONENT_COUNTER corrupted, reset to 0"
  fi

  if [ "$COMPONENT_COUNTER" -ge "$MAX_COMPONENTS" ]; then
    echo "WARN: max components reached ($COMPONENT_COUNTER/$MAX_COMPONENTS)"
    break
  fi
  # ... process component
done
```

---

## §1 — Účel

Převést backlog item (Task/Bug/Epic) na **detailní implementační specifikaci**, ze které může
`fabric-implement` pracovat deterministicky a bez dalších otázek.

Design produkuje: datový model (Pydantic), API signatury, integrační flow, konfiguraci,
testovací strategii s konkrétními test cases, závislosti, rizika a alternativní přístupy.

**Bez tohoto skillu:** LLM implementuje z 1–2 vět backlog popisu → nekonzistentní architektura,
chybějící edge cases, žádné alternativy, ad-hoc rozhodnutí. Každý rework cyklus je dražší
než upfront design.

**Rozdíl od fabric-analyze:**
- `fabric-analyze` = taktická dekompozice (Sprint Targets → Task Queue)
- `fabric-design` = hluboká specifikace (1 backlog item → implementační plán)
- Analyze je ŠIROKÝ (celý sprint), design je HLUBOKÝ (jeden item)

---

## §2 — Protokol (povinné — NEKRÁTIT)

Protocol logging is MANDATORY and must not be shortened.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-design" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-design" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/design-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-design" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

```bash
# K7: Path traversal guard
for VAR in "{WORK_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# K6: Mandatory preconditions (1-3)
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: config.md not found — run fabric-init first"
  exit 1
fi
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: state.md not found — run fabric-init first"
  exit 1
fi
if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  echo "STOP: backlog item ${TASK_ID} not found"
  exit 1
fi

# K6: Priority validation (fabric-prio dependency)
ITEM_PRIO=$(grep 'prio:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | awk '{print $2}' 2>/dev/null)
if [ -z "$ITEM_PRIO" ]; then
  echo "WARN: Target item missing prio field — run fabric-prio first"
fi
```

**Dependency chain:** `fabric-init → fabric-intake → fabric-prio → [fabric-design] → fabric-analyze → fabric-implement`

Detail: `references/02-preconditions.md` (optional checks 4-6: task status, CODE_ROOT, governance).

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (COMMANDS, cesty, taxonomie)
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/backlog/${TASK_ID}.md` (backlog item k rozpracování)
- `{CODE_ROOT}/` (zdrojový kód — pro pochopení existující architektury)
- `{TEST_ROOT}/` (existující testy — pro pochopení testing patterns)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/decisions/INDEX.md` + `{WORK_ROOT}/decisions/*.md` (governance constraints)
- `{WORK_ROOT}/specs/INDEX.md` + `{WORK_ROOT}/specs/*.md` (technické specifikace)
- `{ANALYSES_ROOT}/{TASK_ID}-analysis.md` (pokud analyze už proběhla — doplň, nepřepisuj)
- `{DOCS_ROOT}/` (dokumentace — API docs, README, architecture notes)
- `fabric/visions/` (vision alignment)

---

## §5 — Výstupy

### Primární (vždy)
- Design spec: `{ANALYSES_ROOT}/{TASK_ID}-design.md` (schema: `fabric.report.v1`, kind: `design`)
- Report: `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)
- Aktualizovaný backlog item: `status: READY` (pokud design kompletní)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/design-{slug}.md` (pro blocker/clarification)
- ADR draft: `{WORK_ROOT}/decisions/ADR-NNN-draft.md` (pokud design vyžaduje nový architektonický rozhodnutí)
- Spec draft: `{WORK_ROOT}/specs/SPEC-NNN-draft.md` (pokud design definuje nový kontrakt)

---

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

---

## §6 — Deterministic FAST PATH

Deterministic setup steps in **references/03-fast-path.md**.

**Summary:**
1. Sync backlog index: `python skills/fabric-init/tools/fabric.py backlog-index`
2. Sync governance index: `python skills/fabric-init/tools/fabric.py governance-index`
3. Extract project language: `grep 'Jazyk' {WORK_ROOT}/config.md` for framework context

These three steps establish baseline state. Fail-open (never block on missing indices).

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### State Validation (K1: State Machine)

```bash
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="planning"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-design. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### Path Traversal Guard (K7: Input Validation)

```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}
```

### Design Procedure (8 Sections: D1–D8)

Design work consists of 8 sequential sections. Each has a dedicated reference file with detailed procedures, templates, and anti-patterns.

#### D1: Pochop Kontext (VERIFY-FIRST)

**Goal:** Understand WHAT needs to be done and WHY.

**Quick summary:** Read backlog item, relevant source code, test patterns, and governance constraints. Identify what exists, what's new, and what constraints apply.

**Detailed procedure:** See **references/04-procedure-d1.md**
- Read backlog item (title, AC, effort, vision)
- Read ≥3 affected source files (understand architecture, patterns, conventions)
- Read test patterns (framework, fixtures, naming)
- Governance cross-check (find related ADRs and SPECs)

**Minimum success:**
- Backlog fully understood
- ≥3 relevant source files reviewed
- Test patterns documented
- Governance constraints listed

#### D2: Datový Model

**Goal:** Design new/modified data structures (Pydantic models, schemas, migrations).

**Quick summary:** For each entity, specify complete definition with types, validators, defaults, and relationships. Document migration strategy if modifying existing models.

**Detailed procedure:** See **references/05-procedure-d2.md**
- Identify data entities required by design
- For each entity: complete definition with types and validators
- Document relationships (1:1, 1:N, M:N)
- Migration strategy if modifying existing models

**Minimum success:**
- All entities have complete definitions with types
- Relationships documented
- Validators present for user-facing fields
- Migration path specified if applicable

#### D3: Komponenty a API

**Goal:** Design new/modified classes, methods, and API endpoints.

**Quick summary:** For each component, specify file, class, method signatures. For each endpoint, specify HTTP method, path, request/response schemas. Write pseudokód for complex logic.

**Detailed procedure:** See **references/06-procedure-d3-d4.md** (D3 section)
- Component specification: file + class + method signatures
- Endpoint specification: method + path + request/response + error codes
- Pseudokód for logic >5 lines (MANDATORY for complex logic)

**Minimum success:**
- Each component: file + class + key methods with signatures
- Each endpoint: HTTP method, path, request/response, status codes
- Pseudokód present for all non-trivial logic

#### D4: Integrace a Flow

**Goal:** Design how new code integrates with existing system.

**Quick summary:** Identify all integration points. Draw data flow diagram. Document side effects (cache invalidation, event publishing, metrics).

**Detailed procedure:** See **references/06-procedure-d3-d4.md** (D4 section)
- List integration points (which services are called, why, error handling)
- ASCII data flow diagram (inputs → transforms → outputs → errors)
- Side effects: cache, events, metrics, logging

**Minimum success:**
- Integration points identified and explained
- Flow diagram shows inputs, transformations, outputs, error paths
- Side effects documented with timing and impact

#### D5: Konfigurace

**Goal:** Specify new config keys, environment variables, feature flags.

**Quick summary:** List what must be configurable (not hardcoded). For each key: name, type, default, validation, description.

**Detailed procedure:** See **references/07-procedure-d5-d8.md** (D5 section)
- Identify what must be configurable (timeouts, API keys, thresholds, feature flags)
- For each key: name, type, default, validation rule, description, env var
- Check against existing config (prevent duplicates)

**Minimum success:**
- New config keys listed (or "none required")
- Each key: type, default, validation, description specified

#### D6: Testovací Strategie

**Goal:** Define SPECIFIC test cases (not vague "write tests").

**Quick summary:** For EACH new component, design ≥3 test cases: happy path, edge case, error handling. Specify concrete inputs and expected outputs. Estimate coverage.

**Detailed procedure:** See **references/07-procedure-d5-d8.md** (D6 section)
- ≥3 test cases per component: happy path + edge case + error handling
- Each test: name, scenario, specific input values, expected output
- Integration tests with fixtures and setup
- Coverage estimate (% of new lines)

**Minimum success:**
- ≥3 test cases per component with concrete inputs/outputs
- Coverage estimate provided
- Test names describe what is tested

#### D7: Alternativy a Rizika

**Goal:** Justify design choices. Identify and mitigate risks.

**Quick summary:** For each major design decision, propose ≥2 alternatives with pro/con analysis. Explain chosen approach. Identify ≥2 risks with mitigation strategies.

**Detailed procedure:** See **references/07-procedure-d5-d8.md** (D7 section)
- ≥2 alternatives per design decision with pros/cons
- Trade-offs explained (not "it's obvious")
- ≥2 risks identified with probability/severity/mitigation
- Risk owner assigned (who monitors this)

**Minimum success:**
- ≥2 alternatives documented with pro/con table
- Chosen approach justified
- ≥2 risks with mitigation, owner, and detection mechanism

#### D8: Závislosti a Pořadí

**Goal:** Define prerequisite work and implementation order.

**Quick summary:** List external dependencies (libraries, services). List internal dependencies (other tasks, codebase requirements). Propose implementation order.

**Detailed procedure:** See **references/07-procedure-d5-d8.md** (D8 section)
- External dependencies: libraries, services, versions
- Internal dependencies: tasks, codebase requirements
- Implementation order with parallelizable work noted
- Critical path identified

**Minimum success:**
- All dependencies listed with versions
- Implementation order specified
- Parallelizable work identified

### K10: Inline Example — LLMem Batch Capture API

**Input:** Backlog item task-b015 "Add /capture/batch endpoint" (S effort): Accept POST with ≤100 observations, validate each, store deterministically, return 207 Multi-Status.
**Output:** Design with D1–D8: (D1) existing capture.py + triage flow understood, (D2) BatchCaptureRequest model with validators, (D3) endpoint signature POST /capture/batch with request/response schemas, (D4) integration flow diagram, (D5) config: BATCH_MAX_ITEMS=100, (D6) 3 test cases: happy path (3 items), edge case (100 items), error (1 invalid item mixed with valid), (D7) 2 alternatives (sequential vs parallel processing) + risks (rate limiting, memory), (D8) depends_on: triage.py stable, pydantic ≥2.0.

### K10: Anti-patterns (s detekcí)
```bash
# A1: Designing without reading existing code — Detection: D1 section lacking 'read {CODE_ROOT}/' references
# A2: Test cases without concrete input/output values — Detection: grep -E 'test.*pass|TODO|TBD' {design-spec} in D6 section
# A3: Pseudokód too vague (no numbered steps) — Detection: grep -c '^[0-9]\.' {D3} < 3 for complex logic
# A4: Missing alternatives or unjustified choices — Detection: ! grep -E '| Alternative |' {D7} or no pro/con table
```

---

## §8 — Quality Gates

Design cannot proceed to READY without passing all 5 gates. Detailed checklist in **references/08-quality-gates.md**.

### Gate 1: Completeness (all 8 sections D1–D8)
- [ ] Design spec has explicit D1–D8 sections
- Each section has substantive content (not "TODO")

### Gate 2: Pseudokód Present
- [ ] Every complex logic (>5 lines) has numbered pseudokód steps
- [ ] Includes input, transformation, output, error cases

### Gate 3: Test Cases Concrete
- [ ] ≥3 test cases per component with specific input/output values
- [ ] Test names describe what is tested

### Gate 4: Alternatives Present
- [ ] ≥2 alternatives with pro/con table for main design decision
- [ ] Chosen approach justified

### Gate 5: Governance Aligned
- [ ] No conflicts with accepted ADRs
- [ ] No violations of active SPECs
- [ ] If conflict exists: intake item + DESIGN status (not READY)

### K3: Failure Recovery (executable)

```bash
# If design validation fails:
if [ "$DESIGN_VALID" != "true" ]; then
  echo "FAIL: Design validation failed — creating intake item"
  cat > "{WORK_ROOT}/intake/design-fix-$(date +%Y%m%d).md" <<INTAKE
---
title: "Fix design validation failure"
type: task
raw_priority: 7
---
Design failed validation. Rerun fabric-design after fixing.
INTAKE
fi
```

---

## §9 — Report

Create `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md` with:
- Frontmatter: schema, kind, run_id, status, task_id, design_spec path
- Summary: 1–3 sentences (what designed, outcome, blockers)
- Quality gates status (all 5 gates)
- Governance section: constraints + conflicts
- Top 2 risks from D7
- Design summary (data model, components, integration, testing)
- Recommended next step (analyze, implement, or keep in DESIGN)
- Intake items created (if any)
- Warnings (if any)

**Report template:** See **references/09-report-template.md**

---

## §10 — Self-Check (povinný — NEKRÁTIT)

Self-check is MANDATORY before marking design READY. Use detailed checklist in **references/10-self-check.md**.

### Existence Checks
- [ ] Design spec exists: `{ANALYSES_ROOT}/{TASK_ID}-design.md`
- [ ] Report exists: `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md`
- [ ] Backlog item status: READY (if complete) or DESIGN (if incomplete)

### Quality Checks
- [ ] ALL 8 sections (D1–D8) present and substantive
- [ ] D2: Complete type definitions with validators
- [ ] D3: Pseudokód for all complex logic
- [ ] D6: ≥3 test cases per component with concrete inputs/outputs
- [ ] D7: ≥2 alternatives with pro/con, ≥2 risks with mitigation
- [ ] D1: Governance constraints explicitly listed

### Invariants
- [ ] Design spec contains NO real code (only pseudokód/specification)
- [ ] NO files in `{CODE_ROOT}/` were modified
- [ ] Protocol log has START and END entries
- [ ] Backlog item not deleted or moved

---

## §11 — Failure Handling

Use this table to diagnose and resolve design failures. See **references/11-failure-handling.md** for detailed decision tree.

| Phase | Error | Action |
|-------|-------|--------|
| Preconditions | Backlog item missing | STOP — run fabric-intake first |
| Preconditions | Status IN_PROGRESS/DONE | STOP — design phase already passed |
| D1 Kontext | Code not found | WARN — design proceeds theoretically |
| D1 Kontext | Unclear AC | Create intake item for clarification; keep DESIGN status |
| D2 Model | Unclear entity boundaries | Create intake item; design best-guess; keep DESIGN status |
| D3 Component | Pseudokód too vague | Expand with numbered steps, inputs, outputs, errors |
| D3 Component | Too complex for 1 task | Recommend task split; create intake item |
| D4 Integration | >5 integration points | Assess each point; document mitigations |
| D4 Integration | Circular dependency | STOP — architectural error; re-architect before proceeding |
| D7 Alternatives | Only 1 approach | Brainstorm alternatives; if truly 1, justify exhaustively |
| D7 Alternatives | Both have dealbreakers | Design problem; rethink or accept trade-off explicitly |
| D8 Dependencies | Circular dependency | STOP — architectural error; re-architect |
| Gate 5 | Governance conflict | Create intake item for ADR amendment; keep DESIGN status |

**General rule:** Fail-open on OPTIONAL inputs (code not found → WARN), fail-fast on MANDATORY inputs (backlog missing → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: planning
step: design

# Oprávnění
may_modify_state: false        # design nesmí měnit phase/step
may_modify_backlog: true       # aktualizuje status backlog itemu (DESIGN → READY)
may_modify_code: false         # design NIKDY nemodifikuje kód — jen specifikuje
may_create_intake: true        # při blockers/clarifications

# Pořadí v pipeline
depends_on: [fabric-intake, fabric-prio]
feeds_into: [fabric-analyze, fabric-implement]
```

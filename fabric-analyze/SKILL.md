---
name: fabric-analyze
description: "Convert Sprint Targets into Task Queue + per-task analyses with explicit governance constraints."
---
<!-- built from: builder-template -->

# ANALYZE — Sprint Targets → Task Queue

Převést `Sprint Targets` → **Task Queue** tak, aby implementace byla deterministická, kontrolovatelná a v souladu s governance (decisions/specs).

---

## §1 — Účel

**Primary Goal:** Naplnit Task Queue tak, aby na něj šlo navázat `fabric-implement` bez dodatečných otázek. Pro každý task vytvořit per-task analýzu v `{ANALYSES_ROOT}/` s explicitními Constraints (ADR/spec).

**Why It Matters:** Bez analýzy implementátor hádá scope, testovatelnost a závislosti. Analýza je kontrakt mezi plánováním a implementací — zaručuje, že každý task je kompletně specifikován.

**Scope:** Všechny Sprint Targets z aktivního sprintu. Výstupem jsou per-task analýzy, aktualizovaný Task Queue, a analyze report.

**Variants:**
- **default**: Full analysis + Task Queue + cross-task analysis
- **single target**: Analýza jednoho konkrétního targetu (quick mode)

---

## Downstream Contract (WQ7)

| Skill | Contract | Enforcement |
|-------|----------|------------|
| **fabric-implement** | Per-task analysis MUST have §1-§11. Task status = READY only if complete. | Implement reads analysis; DRAFT = task skipped |
| **fabric-review** | Task Queue ordered by dependencies. No circular deps. | Review can cherry-pick if analysis marks tasks independent |
| **fabric-sprint** | Sprint Targets fully decomposed into Task Queue. Effort estimates algorithmic. | Sprint uses estimates for capacity |
| **backlog index** | Backlog items linked to analysis. Task status synchronized across 3 places. | Loop verifies consistency |

---

## §2 — Protokol (povinné — NEKRÁTIT)

```bash
# START
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "analyze" \
  --event start

# END (po úspěchu)
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "analyze" \
  --event end \
  --status OK \
  --report "{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}.md"

# ERROR (při selhání)
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "analyze" \
  --event error \
  --status ERROR \
  --message "<1 věta popisující důvod selhání>"
```

---

## §3 — Preconditions (temporální kauzalita)

```bash
# --- K7: Path traversal guard ---
for VAR in "{WORK_ROOT}" "{CODE_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# --- Phase validation (K1) ---
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" 2>/dev/null | awk '{print $2}')
if [ "$CURRENT_PHASE" != "planning" ]; then
  echo "STOP: fabric-analyze requires phase=planning, current: $CURRENT_PHASE"
  exit 1
fi

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

# --- Precondition 3: Sprint plan existuje ---
CURRENT_SPRINT=$(grep '^sprint:' "{WORK_ROOT}/state.md" 2>/dev/null | awk '{print $2}')
if [ -z "$CURRENT_SPRINT" ]; then
  echo "STOP: Current sprint not found in state.md"
  exit 1
fi

SPRINT_FILE="{WORK_ROOT}/sprints/sprint-${CURRENT_SPRINT}.md"
if [ ! -f "$SPRINT_FILE" ]; then
  echo "STOP: Sprint plan $SPRINT_FILE not found — run fabric-sprint first"
  exit 1
fi

# --- Precondition 4: Backlog index existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "STOP: {WORK_ROOT}/backlog.md not found — run fabric-intake first"
  exit 1
fi

# --- Precondition 5: Governance resources exist ---
if [ ! -f "{WORK_ROOT}/decisions/INDEX.md" ]; then
  echo "WARN: decisions/INDEX.md not found — governance constraints unavailable"
fi
if [ ! -f "{WORK_ROOT}/specs/INDEX.md" ]; then
  echo "WARN: specs/INDEX.md not found — specs constraints unavailable"
fi
```

**Dependency chain:** `fabric-sprint` → [fabric-analyze] → `fabric-implement`

---

## §4 — Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/sprints/sprint-{N}.md`
- `{WORK_ROOT}/backlog.md` + `{WORK_ROOT}/backlog/{id}.md` (všechny targety)
- `{WORK_ROOT}/decisions/INDEX.md` + `{WORK_ROOT}/decisions/*.md`
- `{WORK_ROOT}/specs/INDEX.md` + `{WORK_ROOT}/specs/*.md`
- `{CODE_ROOT}/` + `{TEST_ROOT}/` + `{DOCS_ROOT}/`

---

## §5 — Výstupy

- Aktualizovaný `{WORK_ROOT}/sprints/sprint-{N}.md` (vyplněný `Task Queue`)
- `{ANALYSES_ROOT}/{task_id}-analysis.md` pro každý task v Task Queue
- 0..N intake items v `{WORK_ROOT}/intake/` (clarifications / blockers)
- `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md` (souhrn)

---

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

---

## Kanonická pravidla

1. **Task Queue je autoritativní** pro implementaci. Implement/test/review se řídí pouze Task Queue.
2. **Každá per-task analýza musí mít sekci Constraints** (i kdyby byla `None`).
3. **Do Task Queue patří pouze:** Task | Bug | Chore | Spike.
4. Epic/Story target se vždy rozpadne na konkrétní Tasks.
5. Když není dost specifikace → vytvoř intake item (clarification) a nech task status `DESIGN`.
6. Když je specifikace dostatečná → nastav task status `READY`.

---

## §6 — Deterministic FAST PATH

```bash
# 1. Obnov indexy
python skills/fabric-init/tools/fabric.py backlog-index
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null || echo "WARN: governance-index failed"

# 2. Pro každý target: rozlož + analyzuj (viz §7)

# 3. Cross-task analýza (viz §7 krok 4.1)

# 4. Aktualizuj sprint plan
python skills/fabric-init/tools/fabric.py plan-apply \
  --plan "{WORK_ROOT}/sprints/sprint-{N}.md" \
  --patch "{WORK_ROOT}/plans/analyze-{run_id}.yaml"
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

> **Detailní workflow:** Přečti `references/workflow.md` pomocí Read toolu.
> Obsahuje: state validation, path traversal guard, target processing, procesní analýzu,
> governance constraints, cross-task analýzu, sprint plan update, report generation.

> **Per-task analysis template (11 povinných sekcí):** Přečti `references/analysis-template.md`.
> Obsahuje: kompletní template, contract enforcement script, status synchronization pravidla.

> **Příklady s reálnými LLMem daty (K10):** Přečti `references/examples.md`.

### K2: Counter Initialization

```bash
# K2: Counter initialization
MAX_TASKS_PER_ANALYZE=${MAX_TASKS_PER_ANALYZE:-100}
TASK_COUNTER=0

# K2: Numeric validation
if ! echo "$MAX_TASKS_PER_ANALYZE" | grep -qE '^[0-9]+$'; then
  MAX_TASKS_PER_ANALYZE=100
  echo "WARN: MAX_TASKS_PER_ANALYZE not numeric, reset to default (100)"
fi
```

### K5: Analysis Thresholds

```bash
# K5: Analysis thresholds from config.md (with fallback defaults)
EFFORT_BASE=$(grep 'ANALYSIS.effort_base:' "{WORK_ROOT}/config.md" 2>/dev/null | awk '{print $2}' || echo "") || { echo "ERROR: failed to read ANALYSIS.effort_base from config.md"; exit 1; }
EFFORT_BASE=${EFFORT_BASE:-1}
MAX_DEPS_PER_TASK=$(grep 'ANALYSIS.max_deps_per_task:' "{WORK_ROOT}/config.md" 2>/dev/null | awk '{print $2}' || echo "") || { echo "ERROR: failed to read ANALYSIS.max_deps_per_task from config.md"; exit 1; }
MAX_DEPS_PER_TASK=${MAX_DEPS_PER_TASK:-10}
```

### K10: Inline Example — LLMem Task Decomposition

**Input:** Sprint target: "Add per-instance Qdrant support with warmup + async initialization"
**Output:** 3 tasks (task-b015, task-b016, task-b017) with per-task analysis, effort estimates (M, S, S), dependencies (task-b015 → task-b016 → task-b017), Module Dependency Table showing storage/backends/*.py impact, Test Strategy covering Write Path chain (capture→triage→store→verify).

### K10: Rework/Error Flow Example

**Input:** Sprint target "Improve recall pipeline" decomposes into task-b020 (M) with FILES_TOUCHED=12.
**Flow:**
1. Effort algorithm: FILES_TOUCHED=12, NEW_TESTS=8, MAX_COMPLEXITY=3 → computed effort=XL
2. XL exceeds threshold → task must be split
3. Re-decompose: task-b020a (scoring refactor, S, 4 files), task-b020b (candidate generation, S, 5 files), task-b020c (injection update, S, 3 files)
4. Dependency: b020a → b020b → b020c (serial — scoring feeds generation feeds injection)
5. Cross-task check: shared module `recall/pipeline.py` touched by b020a and b020b → explicit ordering enforced
6. Contract validation: all 11 sections present in each analysis → status READY
7. Report: 1 target → 3 tasks (3 READY, 0 DESIGN), governance constraints: ADR-005 (scoring weights)

### K10: Anti-patterns (s detekcí)
```bash
# A1: Analyzing without governance specs
MISSING_GOV=$(find "{ANALYSES_ROOT}" -name '*-analysis.md' -exec grep -L 'decisions/INDEX.md\|specs/INDEX.md\|Constraints' {} \; 2>/dev/null | wc -l)
if ! echo "$MISSING_GOV" | grep -qE '^[0-9]+$'; then MISSING_GOV=0; fi
if [ "$MISSING_GOV" -gt 0 ]; then
  echo "WARN: A1 — $MISSING_GOV analyses missing governance cross-reference"
fi

# A2: Epic→Tasks missing intermediate decomposition
for ANALYSIS in "{ANALYSES_ROOT}"/*-analysis.md; do
  [ -f "$ANALYSIS" ] || continue
  FILES_TOUCHED=$(grep -oE 'FILES_TOUCHED:\s*[0-9]+' "$ANALYSIS" 2>/dev/null | grep -oE '[0-9]+')
  FILES_TOUCHED=${FILES_TOUCHED:-0}
  if ! echo "$FILES_TOUCHED" | grep -qE '^[0-9]+$'; then FILES_TOUCHED=0; fi
  if [ "$FILES_TOUCHED" -gt 8 ]; then
    echo "WARN: A2 — $(basename "$ANALYSIS") touches $FILES_TOUCHED files; consider splitting"
  fi
done

# A3: Circular dependencies in Task Queue
# Detection via topological sort failure
if [ -f "$SPRINT_FILE" ]; then
  DEPS=$(grep -oE 'depends_on:.*' "{ANALYSES_ROOT}"/*-analysis.md 2>/dev/null)
  # Simple A→B→A check
  for A in $(echo "$DEPS" | grep -oE 'task-[a-z0-9-]+'); do
    for B in $(grep "depends_on:.*$A" "{ANALYSES_ROOT}"/*-analysis.md 2>/dev/null | grep -oE 'task-[a-z0-9-]+' | grep -v "$A"); do
      if grep -q "depends_on:.*$B" "{ANALYSES_ROOT}/${A}"-analysis.md 2>/dev/null; then
        echo "FAIL: A3 — Circular dependency: $A ↔ $B"
        exit 1
      fi
    done
  done
fi

# A4: Effort estimates missing FILES_TOUCHED
MISSING_EFFORT=$(grep -rL 'FILES_TOUCHED:\|NEW_TESTS:' "{ANALYSES_ROOT}"/*-analysis.md 2>/dev/null | wc -l)
if ! echo "$MISSING_EFFORT" | grep -qE '^[0-9]+$'; then MISSING_EFFORT=0; fi
if [ "$MISSING_EFFORT" -gt 0 ]; then
  echo "FAIL: A4 — $MISSING_EFFORT analyses missing FILES_TOUCHED/NEW_TESTS effort data"
  exit 1
fi
```

Stručný přehled kroků:

1. **Deterministická příprava** — obnov backlog + governance indexy
2. **Pro každý target vytvoř tasks** — rozlož Epic/Story na Tasks, urči ID/Type/Status/Estimate
3. **Procesní analýza per task (POVINNÉ):**
   - A) Datový tok (ASCII diagram + error paths)
   - B) Module Dependency Table (full paths + risk)
   - C) Entity Lifecycle (pokud relevantní)
   - D) Process-map cross-reference
4. **Governance constraints** — cross-reference ADR/specs, escalate conflicts
5. **Zapiš per-task analýzy** — 11 povinných sekcí, contract enforcement
6. **Cross-task analýza** — sdílené moduly, závislosti, optimální pořadí
7. **Aktualizuj sprint plan** — Task Queue update (deterministicky)
8. **Generuj analyze report** — souhrn s frontmatter

---

## §8 — Quality Gates

| Gate | Kritérium | Automatizace |
|------|-----------|-------------|
| QG1 | Každý task má kompletní per-task analýzu | contract enforcement script (11 sekcí) |
| QG2 | Data Flow diagram má error paths | grep check v analýzách |
| QG3 | Module Dependency Table má full paths | grep check |
| QG4 | Alternatives ≥2 (nebo WARN pro XS/S) | grep check |
| QG5 | Test Strategy pokrývá všech 5 úrovní | section count check |
| QG6 | Effort algorithmic (ne heuristika) | grep FILES_TOUCHED v analýze |
| QG7 | Cross-task analýza v reportu | grep check |
| QG8 | Status synchronized (3 místa) | diff check analysis ↔ sprint ↔ backlog |

---

## §9 — Report

`{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md`:

```yaml
---
schema: fabric.report.v1
kind: analyze
step: "analyze"
run_id: "analyze-{YYYY-MM-DD}-{RUN_ID}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: PASS
targets_count: N
tasks_ready: N
tasks_design: N
---
```

Sekce: Summary, Per-task Results (tabulka), Cross-task Analysis, Governance Constraints Used, Clarifications Created, Warnings.

---

## §10 — Self-check (VŠECHNY položky MUSÍ být ✅ ANTES publish)

### Per-task Analysis Quality (§2.1 contract)

- [ ] **Každý task má kompletní per-task analýzu** v `{ANALYSES_ROOT}/{task_id}-analysis.md`
- [ ] **§1 Constraints**: Tabulka `| ADR/Spec | Requirement | How satisfied |` — ≥1 row (može být "None")
- [ ] **§2 Data Flow**: ASCII diagram s minimálně 3 kroky + error handling pro každý krok (ne jen happy path)
- [ ] **§3 Module Dependency Table**: Tabulka `| Module | Type | Upstream | Downstream | Risk |` — VŠECHNY dotčené moduly
- [ ] **§4 Entity Lifecycle**: Stavy CREATED → ... → EXPIRED (pokud task mění entity); jinak "N/A — {reason}"
- [ ] **§5 Affected Processes**: Cross-reference s process-map.md (konkrétní proces jméno + kontrakty) nebo "NOTE: file not found"
- [ ] **§6 Pseudocode**: KONKRÉTNÍ (references actual files, functions, imports), ne generický Python
- [ ] **§7 Alternatives**: ≥2 alternativy (nebo WARN pro XS/S) s tabulkou `| Approach | Complexity | Risk | ADR Align | Test | Total | Chosen |`
- [ ] **§8 Test Strategy**: VŠECH 5 úrovní (Unit/Integration/E2E/Edge/Regression) s konkrétními test jmény (ne "implementátor doplní")
- [ ] **§9 Effort Estimate**: Vypočteno algoritmicky (FILES_TOUCHED + NEW_TESTS + MAX_COMPLEXITY) + výpočet zobrazen
- [ ] **§10 AC Mapping**: Tabulka mapování AC → jak task splňuje
- [ ] **§11 Risks & Open Questions**: Konkrétní rizika (ne "může být složité") + mitigation + open questions (ne prázdné)

### Contract Validation (§4 enforcement)

- [ ] **Contract validation script PASSED**: Všechny 11 sekcí přítomny (výjimka: Alternatives ok pro XS/S)
  - Pokud FAIL → task vrácen do DESIGN, implementátor ho přeskočí
  - Pokud PASS → status nastavěn na READY ✅
- [ ] **Status synchronization**: VŠECHNY 3 místa updated:
  1. `{ANALYSES_ROOT}/{task_id}-analysis.md` frontmatter `status:`
  2. `{WORK_ROOT}/sprints/sprint-{N}.md` Task Queue sloupec `Status`
  3. `{WORK_ROOT}/backlog/{task_id}.md` frontmatter `status:`

### Cross-task Analysis (§4.1 ALWAYS)

- [ ] **Cross-task analýza v analyze reportu** (i pro 1-2 tasks):
  - 1-2 tasks: "N/A — {N} tasks, impact on backlog verified"
  - ≥3 tasks: KOMPLETNÍ analýza s dependency table + execution order + parallel opportunities
- [ ] **Dependency ordering**: Task Queue seřazeno podle: dependencies → risk → effort (momentum)
- [ ] **Shared modules identified**: Pokud ≥2 tasks touch stejný soubor → explicita order v reportu

### Governance Integrity

- [ ] **Governance indexes existují** a jsou čitelné (`{WORK_ROOT}/decisions/INDEX.md`, `{WORK_ROOT}/specs/INDEX.md`)
- [ ] **Constraints sekce**: Všechny relevantní ADR/SPEC odkazovány (ne vynechané)
- [ ] **Conflicts escalated**: Pokud task conflicts s ADR/SPEC → intake item `governance-clarification-{task_id}.md` vytvořen

### Test Coverage & Process Chain

- [ ] **Write Path tasks** (capture, triage, store): test pokrytí Write Path chain (capture→triage→store→verify)
- [ ] **Recall Path tasks** (recall, scoring, injection): test pokrytí Recall Path chain (query→search→score→inject)
- [ ] **Critical process tests**: Pokud task mění process-map kontrakty → `test_e2e_{process_name}` zmapován
- [ ] **Regression coverage**: Pokud bugfix → `test_{id}_regression_{bug}` named konkrétně

### Effort & Scope Sanity

- [ ] **Effort sanity check**: Pokud S ale FILES_TOUCHED ≥5 → odhad Updated (L nebo XL)
- [ ] **XL/oversized tasks split**: Pokud EFFORT = XL → task je rozložen na ≤L subtasks
- [ ] **Anti-patterns**: Vágní popis ("implementuj feature X" — musí být konkrétní soubory/funkce)

### Report & Artifacts

- [ ] **Analyze report** (`{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md`) vytvořen:
  - Souhrn: N targetů → N tasks (M READY, N-M DESIGN)
  - ADR/SPEC constraints použité
  - Clarifications vytvořené (intake items)
  - Cross-task analysis sekce
- [ ] **Intake items** (pokud potřeba): `{WORK_ROOT}/intake/governance-clarification-*.md` + `{WORK_ROOT}/intake/blocker-*.md`
- [ ] **Backlog updated**: Všechny backlog items s linkama na analysis (`See {ANALYSES_ROOT}/{task_id}-analysis.md`)

### Final Checkpoint — BLOCKING ENFORCEMENT (WQ10)

- [ ] ✅ Všechny per-task analýzy prošly contract validation (PASS)
  - ❌ CRITICAL: Analýza chybí povinné sekce (§1-§11) → **FAIL task** (vrátit do DESIGN, EXIT 1)
  - ❌ CRITICAL: Task in READY ale bez Data Flow diagram → **EXIT 1** (incomplete specification)
- [ ] ✅ Všechny tasks v Task Queue jsou READY nebo DESIGN (ne other states)
  - ❌ CRITICAL: Task se opakuje ve více řádcích Task Queue → **EXIT 1** (duplicate cleanup required)
- [ ] ✅ Žádný task v READY bez kompletní analýzy (contract enforcement passed)
  - ❌ CRITICAL: Status sync mismatch (READY v analysis, DESIGN v backlog) → **EXIT 1** (synchronize before publish)
- [ ] ✅ Cross-task analýza pokrývá všechny interakce (dependency ordering optimized)
  - ❌ CRITICAL: Circular dependency detected (A→B→A) → **EXIT 1** (unresolvable, intake item required)
- [ ] ✅ Report vygenerován a archivován
  - ❌ CRITICAL: Analyze report missing or truncated → **EXIT 1** (re-run analysis)

**Non-critical warnings (don't fail analyze):**
- ⚠️ WARN: Task is DESIGN (incomplete analysis) — note in report, implementer will skip
- ⚠️ WARN: Effort estimate ≥XL — recommend splitting (but don't fail)
- ⚠️ WARN: process-map.md missing — note in report, continue without process validation

Pokud JAKÝKOLIV CRITICAL check selhává → **EXIT 1, log error, artifact cleanup** (don't publish partial report).

---

## §11 — Failure Handling

| Stav | Akce |
|------|------|
| Config/State chybí | STOP — `fabric-init` musí běžet první |
| Sprint plan chybí | STOP — `fabric-sprint` musí běžet první |
| Backlog index chybí | STOP — `fabric-intake` musí běžet první |
| Governance chybí | WARN — pokračuj bez constraints |
| Target backlog item chybí | WARN — skip target, zaznamenáš do reportu |
| Oversized backlog item (>100KB) | WARN — skip, zaznamenáš |
| Analýza incomplete | Set DRAFT, task → DESIGN (ne READY) |
| Circular dependency | EXIT 1, intake item pro řešení |

### Idempotence

Re-run je bezpečný. Existující analýzy se přepíšou (idempotent). Task Queue se doplní (ne duplikuje). Report se přegeneruje.

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
depends_on: [fabric-sprint, fabric-design]
feeds_into: [fabric-implement]
phase: planning
lifecycle_step: analyze
touches_state: false
touches_git: false
estimated_ticks: 1
idempotent: true
fail_mode: fail-open  # DESIGN tasks jsou validní výsledek
```

### Downstream Contract

- **fabric-implement** reads: `{ANALYSES_ROOT}/{task_id}-analysis.md` (all 11 sections), Task Queue status
- **fabric-review** reads: analysis for context during code review
- **fabric-loop** reads: analyze report `status` + `tasks_ready` count

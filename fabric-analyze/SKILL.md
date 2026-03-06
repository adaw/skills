---
name: fabric-analyze
description: "Convert Sprint Targets into Task Queue + per-task analyses with explicit governance constraints."
---

# fabric-analyze

> **Úkol:** Převést `Sprint Targets` → **Task Queue** tak, aby implementace byla deterministická, kontrolovatelná a v souladu s governance (decisions/specs).

## Cíl

- Naplnit `Task Queue` tak, aby na něj šlo navázat `fabric-implement` bez dodatečných otázek.
- Pro každý task vytvořit krátkou **per-task analýzu** v `{ANALYSES_ROOT}/`.
- Explicitně uvést **Constraints** (které ADR/spec ovlivňují task).
- Když chybí informace → vytvořit intake item (clarification / blocker) místo vymýšlení.

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/sprints/sprint-{N}.md`
- `{WORK_ROOT}/backlog.md` + `{WORK_ROOT}/backlog/{id}.md` (všechny targety)
- `{WORK_ROOT}/decisions/INDEX.md` + `{WORK_ROOT}/decisions/*.md`
- `{WORK_ROOT}/specs/INDEX.md` + `{WORK_ROOT}/specs/*.md`
- `{CODE_ROOT}/` + `{TEST_ROOT}/` + `{DOCS_ROOT}/`

## Výstupy

- Aktualizovaný `{WORK_ROOT}/sprints/sprint-{N}.md` (vyplněný `Task Queue`)
- `{ANALYSES_ROOT}/{task_id}-analysis.md` pro každý task v Task Queue
- 0..N intake items v `{WORK_ROOT}/intake/` (clarifications / blockers)
- `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md` (souhrn)

## Kanonická pravidla

1. **Task Queue je autoritativní** pro implementaci. Implement/test/review se řídí pouze `Task Queue`.
2. **Každá per-task analýza musí mít sekci `Constraints`** (i kdyby byla `None`).
3. **Do Task Queue patří pouze:** `Task | Bug | Chore | Spike`.
4. `Epic/Story` target se vždy rozpadne na konkrétní Tasks.
5. Když není dost specifikace → vytvoř intake item (clarification) a nech task status `DESIGN`.
6. Když je specifikace dostatečná → nastav task status `READY`.

## Formát per-task analýzy (povinný)

Ulož do `{ANALYSES_ROOT}/{task_id}-analysis.md`:

```md
---
schema: fabric.report.v1
kind: analysis
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
task_id: "{task_id}"
source_target: "{target_id}"
status: "DRAFT"  # DRAFT | READY
---

# {task_id} — Analysis

## Goal
{WHAT_SUCCESS_LOOKS_LIKE}

## Constraints
> Explicitně uveď, které **accepted ADR** a **active specs** ovlivňují tento task.

- Decisions (ADR): {ADR_IDS_OR_NONE}
- Specs: {SPEC_IDS_OR_NONE}
- Notes: {HOW_THEY_CONSTRAIN}

## Design
- Approach: {APPROACH}
- Files likely touched: {FILES}
- Risks: {RISKS}

## Affected Processes
> If `process-map.md` exists in `{WORK_ROOT}/fabric/`, cross-reference this task's modules with documented process chains.

- Processes affected: {PROCESS_NAMES_OR_NONE}
- Contract modules touched: {MODULES_FROM_PROCESS_MAP_OR_NONE}
- Causal dependencies impacted: {DEPENDENCY_CHAIN_OR_NONE}
- Recommendation: {TEST_COVERAGE_RECOMMENDATION_OR_NONE}

**Procedure (fail-open):**
```bash
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if [ -f "$PROCESS_MAP" ]; then
  # Extract processes that contain any of the task's touched files
  grep -E "({touched_files_regex})" "$PROCESS_MAP" | cut -d'|' -f1 | sort -u
  # Build causal chain from process map for each affected process
else
  echo "NOTE: process-map.md not found — skipping process cross-reference"
fi
```

## Plan
1. {STEP_1}
2. {STEP_2}
3. {STEP_3}

## Tests
- Baseline: {BASELINE_COMMANDS}
- Unit (≥3): {test_happy}, {test_edge}, {test_error}
- Integration: {test_integration_endpoint} (pokud API/service change)
- E2E: {test_e2e_scenario} (pokud user-facing feature)
- Edge cases (≥2): {konkrétní scénáře}
- Regression: {test_regression} (pokud bugfix)
- Evidence artifacts: {WHAT_TO_SAVE_IN_REPORTS}

## Acceptance criteria mapping
- AC1: {MAP_TO_REQUIREMENT}
- AC2: {MAP_TO_REQUIREMENT}

## Open questions
- {QUESTION_1}
- {QUESTION_2}
```

## Postup

### 0) Deterministická příprava (rychlá)

```bash
python skills/fabric-init/tools/fabric.py backlog-index
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null
if [ $? -ne 0 ]; then
  echo "WARN: governance-index failed — continuing without governance data"
fi
```

> Tohlo je strojová práce: srovná indexy a odhalí strukturální drift.

**Governance index error handling (P2 fix):** The governance-index call is wrapped with error suppression and continuation logic. If the governance index fails (e.g., missing ADR/spec files), the analysis continues without hard blocking, and a warning is logged for manual review.

### 1) Načti sprint plan a targety

- Najdi aktivní sprint v `state.md` (`state.active_sprint`) a otevři `sprints/sprint-{N}.md`.
- Z tabulky `Sprint Targets` vezmi seznam targetů.
- Pokud `Task Queue` už existuje a není prázdná:
  - doplň jen chybějící tasks
  - nemaž ručně vložené změny, pokud nejsou zjevně špatně.

### 2) Pro každý target vytvoř návrh tasks

**Co:** Rozložit targety na implementovatelné tasky s jasným scope a testovatelností.

**Size guard (P2 fix): Skip oversized backlog items to prevent parsing performance issues:**
```bash
# Size guard: skip oversized backlog items (P2 fix)
FILE_SIZE=$(wc -c < "{WORK_ROOT}/backlog/${target}.md" 2>/dev/null || echo 0)
MAX_SIZE=102400  # 100KB
if [ "$FILE_SIZE" -gt "$MAX_SIZE" ]; then
  echo "WARN: backlog item ${target}.md exceeds ${MAX_SIZE} bytes — skipping"
  continue
fi
```

Pro každý target:

1) Otevři backlog item `{WORK_ROOT}/backlog/{target}.md`
2) Urči typ (Epic/Story/Task/Bug/Chore/Spike)
3) Pokud Epic/Story:
   - rozpadni na 3–12 tasks (jasně pojmenované, testovatelné)
4) Pokud Task/Bug/Chore/Spike:
   - vytvoř 1 task (můžeš ho upřesnit na implementovatelný)

Každý task musí mít:
- `ID` (např. `{target}-T01`, nebo nově `TASK-XXXX` — buď konzistentní v rámci sprintu)
- `Type` (Task/Bug/Chore/Spike)
- `Status` (DESIGN/READY)
- `Description` (1–2 věty max)
- `Estimate` (S/M/L; heuristika)

**Effort sanity check (POVINNÉ):**
Pokud analýza odhalí, že skutečný scope neodpovídá effort odhadu:
```bash
# Effort sanity: pokud task odhadnutý jako S ale dotýká se ≥5 souborů nebo ≥3 modulů → WARN
TOUCHED_FILES=$(echo "{files_list}" | wc -w)
if [ "$EFFORT" = "S" ] && [ "$TOUCHED_FILES" -ge 5 ]; then
  echo "WARN: task $TASK_ID estimated S but touches $TOUCHED_FILES files — consider M or L"
fi
```
Pokud effort mismatch: uprav odhad v Task Queue a backlog itemu + zapiš důvod do analýzy.

**Anti-patterns (zakázáno):**
- ❌ Vágní task popis ("implementuj feature X" — musí být konkrétní: jaké soubory, jaký endpoint, jaký model)
- ❌ Task bez testovatelných AC (každý task musí mít alespoň 1 ověřitelné akceptační kritérium)
- ❌ Estimate bez zdůvodnění (L protože "je to složité" — uveď proč: nový model + API + testy)
- ❌ Epic/Story v Task Queue bez rozkladu na Tasks

### 2.1) Procesní analýza per task (POVINNÉ)

Pro KAŽDÝ task PŘED zápisem do analýzy proveď procesní rozbor:

**A) Datový tok** — identifikuj jak data tečou systémem pro tento task:
```
Vstup → [Validace] → [Transformace] → [Persistence] → [Response]
         ↓ error       ↓ error          ↓ error         ↓ error
       400/422        500/log          retry/fail       500/partial
```
Zapiš do analýzy sekci `## Data Flow` s ASCII diagramem (nemusí být složitý — 3-5 kroků stačí).

**B) Dotčené moduly a závislosti** — SYSTEMATICKY (ne "files likely touched"):
```markdown
### Dotčené moduly
| Modul | Typ změny | Závislosti UP | Závislosti DOWN | Risk |
|-------|-----------|--------------|-----------------|------|
| {CODE_ROOT}/api/routes/capture.py | MODIFY | server.py (router) | services/capture.py | LOW |
| {CODE_ROOT}/services/capture.py | MODIFY | — | triage/heuristics.py, storage/ | MEDIUM |
```

**C) Message/Entity lifecycle** (pokud task mění chování entity):
```
CREATED → VALIDATED → STORED → [RECALLED] → EXPIRED
```
Pokud task nemění lifecycle entity → napiš "N/A — task nemění entity lifecycle".

**D) Process-map cross-reference (Affected Processes check):**

Pro KAŽDÝ task proveď procesní mapování:
```bash
# 1. Prepare touched files list
TOUCHED_FILES="{files_list}"  # e.g., "api/routes/capture.py services/capture.py"

# 2. Load process map if exists
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if [ ! -f "$PROCESS_MAP" ]; then
  echo "NOTE: process-map.md not found at $PROCESS_MAP — skipping process cross-reference"
  exit 0
fi

# 3. Find affected processes (grep for touched files in process-map)
AFFECTED_PROCESSES=$(
  for file in $TOUCHED_FILES; do
    # Search for process chain containing this file
    grep -B 5 -A 5 "$file" "$PROCESS_MAP" 2>/dev/null | \
      grep -E "^##\s|^###\s" | head -1
  done | sort -u
)

# 4. For each affected process, extract contract_modules
if [ -n "$AFFECTED_PROCESSES" ]; then
  echo "Affected processes:"
  echo "$AFFECTED_PROCESSES"

  # Extract causal dependencies from process map
  while IFS= read -r process; do
    echo "  Process: $process"
    # Find contract modules in the process chain
    awk "/$process/,/^##/" "$PROCESS_MAP" | grep -E "contract_modules|dependencies" || true
  done <<< "$AFFECTED_PROCESSES"
fi
```

Zapiš do analýzy sekci `## Affected Processes` s:
- Seznamem dotčených procesů (nebo "None — task je izolován")
- Contract modules z process-map, které se mění
- Kauzální závislostmi (např. "Write Path se změní, musíš ověřit Recall Path")
- Doporučením: "Ensure tests cover {PROCESS_CHAIN}, especially {CRITICAL_STEP}" (nebo "N/A — single-module task")

**Anti-patterns:**
- ❌ "Files likely touched: models.py, api/" — VÁGNÍ (musí být konkrétní modul + typ změny + závislosti)
- ❌ Přeskočit datový tok protože "je to jednoduchý task" — i jednoduchý task má vstup→výstup
- ❌ Ignorovat proces mapování pokud process-map.md chybí (napiš "NOTE: process-map.md not found")
- ✅ ASCII diagram VŽDY, i kdyby měl jen 3 boxy
- ✅ Fail-open: chybí process-map → pokračuj, jen zaznamenej NOTE do analýzy

### 3) Governance constraints per task

- Z `decisions/INDEX.md` a `specs/INDEX.md` vyber relevantní kontrakty.
- Pokud backlog item explicitně odkazuje na ADR/SPEC, použij je.
- Pokud je konflikt:
  - nevymýšlej workaround
  - vytvoř intake item `intake/governance-clarification-{task_id}.md`
  - v tasku nastav `Status = DESIGN`

### 4) Zapiš per-task analýzy

**Co:** Pro každý task vytvořit kompletní analýzu s pseudokódem a alternativami.

- Pro každý task vytvoř `{ANALYSES_ROOT}/{task_id}-analysis.md` podle template výše.
- Pokud má task otevřené otázky → ponech `status: DRAFT` a `Task Queue Status = DESIGN`.
- Pokud je vše jasné → `status: READY` a `Task Queue Status = READY`.

**Contract enforcement (analyze→implement):**
Analýza NESMÍ být označena `READY` pokud chybí kterákoli z povinných sekcí:
```bash
# Validace před nastavením READY
ANALYSIS_FILE="{ANALYSES_ROOT}/{task_id}-analysis.md"
MISSING=""
grep -q "^## Constraints" "$ANALYSIS_FILE" || MISSING="${MISSING} Constraints"
grep -q "^## Plan" "$ANALYSIS_FILE" || MISSING="${MISSING} Plan"
grep -q "^## Tests" "$ANALYSIS_FILE" || MISSING="${MISSING} Tests"
grep -q "^## Affected Processes" "$ANALYSIS_FILE" || MISSING="${MISSING} AffectedProcesses"
if [ -n "$MISSING" ]; then
  echo "WARN: analysis missing sections:${MISSING} — keeping status DESIGN"
  # Nastav DESIGN, ne READY — implement by jinak dostal neúplnou analýzu
fi
```

**Povinné sekce v každé analýze (nesmí chybět):**

1. **Pseudokód** — v sekci `## Design → Approach` napiš pseudokód hlavní logiky:
```python
# Pseudokód pro {task_id}
def new_feature(input: InputType) -> OutputType:
    validated = validate(input)          # krok 1: validace
    result = process(validated)          # krok 2: core logika
    store(result)                        # krok 3: persistence
    return format_response(result)       # krok 4: output
```

2. **Alternativy** — v sekci `## Design` uveď **≥2 alternativní přístupy** s pro/con:
```markdown
### Alternativy
| # | Přístup | Pro | Con | Zvolen? |
|---|---------|-----|-----|---------|
| A | {přístup 1} | {výhody} | {nevýhody} | ✅ |
| B | {přístup 2} | {výhody} | {nevýhody} | — |
```

3. **Test strategie (5 úrovní)** — v sekci `## Tests → New tests` uveď testy na VŠECH relevantních úrovních:

   **Úroveň 1 — Unit testy (POVINNÉ, ≥3):**
   - `test_{id}_happy` — základní funkčnost
   - `test_{id}_edge` — hraniční případ (empty, None, max, unicode)
   - `test_{id}_error` — chybový stav (invalid input → exception)

   **Úroveň 2 — Integration testy (POVINNÉ pokud task mění API/service):**
   - `test_{id}_integration_{endpoint}` — endpoint volání end-to-end (request→response)
   - `test_{id}_integration_{service}` — service vrstva s reálnou závislostí (ne mock)

   **Úroveň 3 — E2E testy (POVINNÉ pokud task přidává nový user-facing feature):**
   - `test_{id}_e2e_{scenario}` — celý flow od vstupu po výstup

   **Úroveň 4 — Edge case testy (POVINNÉ, ≥2):**
   - Concurrent access, race conditions, timeout, network failure, malformed input
   - Pro každý edge case: konkrétní scénář + expected behavior

   **Úroveň 5 — Regression testy (POVINNÉ pokud task fixuje bug):**
   - `test_{id}_regression_{bug_description}` — reprodukce původního bugu + ověření fixu

   **MINIMUM:** Každá analýza MUSÍ mít ≥3 unit + relevantní integration/E2E/edge/regression.
   **Anti-pattern:** ❌ "testy dodá implementátor" — analyzátor MUSÍ specifikovat CO testovat na KTERÉ úrovni.

**Anti-patterns (zakázáno):**
- ❌ Analýza bez pseudokódu ("implementuj dle specifikace" — LLM potřebuje konkrétní kroky)
- ❌ Jediná alternativa ("jinak to nejde" — vždy existují ≥2 přístupy, byť jeden je horší)
- ❌ Prázdná sekce Tests ("testy doplní implementátor" — analyzátor MUSÍ definovat co testovat)
- ❌ Vágní rizika ("může to být složité" — konkrétní: "SQLite lock contention při concurrent writes")
- ❌ Over-engineering ("abstrakce pro budoucí rozšiřitelnost" bez aktuálního use case — YAGNI/KISS)
- ✅ Preferuj jednodušší řešení: pokud alternativa A je jednodušší a splňuje AC, zvol A i když B je "elegantnější"

**DŮLEŽITÉ: Synchronizace statusu.**  Kdykoli změníš status tasku (DESIGN → READY nebo naopak), aktualizuj **všechna tři místa**:
1. Per-task analýza (`{ANALYSES_ROOT}/{task_id}-analysis.md`, frontmatter `status:`)
2. Sprint plan Task Queue (`sprints/sprint-{N}.md`, sloupec `Status`)
3. **Backlog item** (`backlog/{task_id}.md`, frontmatter `status:`)

Pokud některé z těchto míst neaktualizuješ, `fabric-implement` uvidí nekonzistentní stav a task přeskočí.

### 4.1) Cross-task analýza (POVINNÉ pro ≥3 tasks)

Pokud sprint má ≥3 tasks, proveď cross-task analýzu PŘED finalizací:

**A) Sdílené patterny:**
- Používají ≥2 tasks stejný modul? → identifikuj POŘADÍ implementace (kdo jde první)
- Zavádí ≥2 tasks nové modely? → ověř konzistenci naming/patterns

**B) Závislosti a konflikty:**
```markdown
### Cross-task závislosti
| Task A | Task B | Typ | Řešení |
|--------|--------|-----|--------|
| task-001 | task-003 | task-003 mění model, task-001 ho čte | task-003 MUSÍ jít PRVNÍ |
| task-002 | task-004 | oba mění scoring.py | SEKVENČNÍ, task-002 nejdřív (menší scope) |
```

**C) Optimální pořadí:**
Seřaď tasks podle: závislosti → risk (high-risk první, aby se chytily problémy dříve) → effort (menší první pro momentum).

Zapiš do analyze reportu sekci `## Cross-task Analysis` (i pro <3 tasks — pak napiš "N/A — jen {N} tasks").

**Anti-patterns:**
- ❌ Analyzovat tasks izolovaně bez cross-task pohledu
- ❌ Nechat pořadí v Task Queue náhodné (musí reflektovat závislosti)
- ✅ Vždy identifikovat sdílené moduly a konflikty

### 5) Aktualizuj sprint plan deterministicky

Preferuj `plan-apply` (ne ruční edit), aby byl diff čistý:

```bash
python skills/fabric-init/tools/fabric.py plan-apply --plan "{WORK_ROOT}/sprints/sprint-{N}.md" --patch "{WORK_ROOT}/plans/analyze-{run_id}.yaml"
```

- Pokud `plan-apply` není praktické, uprav sprint plan ručně, ale zachovej tabulku strukturu.

> **OWNERSHIP (P2 fix #38):** Sekce `## Task Queue` v sprint plánu je vlastněna výhradně `fabric-analyze`. Jiné skills (fabric-sprint, fabric-implement) ji ČTOU ale NEPÍŠOU. Pokud implementátor potřebuje změnit status tasku, mění ho v `backlog/{id}.md` a v `analyses/{id}-analysis.md`, ne přímo v Task Queue.

### 6) Vygeneruj analyze report

- Shrň:
  - kolik targetů
  - kolik tasks (READY vs DESIGN)
  - jaké ADR/SPEC constraints byly použity
  - jaké clarifications jsi vytvořil do intake

Ulož do `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md` (schema `fabric.report.v1`).

## Self-check

- [ ] Každý task má per-task analýzu a má sekci `Constraints`.
- [ ] Každý task má sekci `Affected Processes` s procesní analýzou (cross-reference s `process-map.md`, nebo NOTE že soubor chybí).
- [ ] Každý task v Task Queue je implementovatelný bez dalších otázek, nebo je označen `DESIGN` a má intake item.
- [ ] Governance indexy existují a jsou čitelné (`decisions/INDEX.md`, `specs/INDEX.md`).
- [ ] Pro tasks dotýkající se kritických procesů (Write Path, Recall Path) jsou testy explicitně zaměřeny na process chain coverage.

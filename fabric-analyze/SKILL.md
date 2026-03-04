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

## Plan
1. {STEP_1}
2. {STEP_2}
3. {STEP_3}

## Tests
- Baseline: {BASELINE_COMMANDS}
- New tests: {NEW_TESTS}
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
python skills/fabric-init/tools/fabric.py governance-index
```

> Tohle je strojová práce: srovná indexy a odhalí strukturální drift.

### 1) Načti sprint plan a targety

- Najdi aktivní sprint v `state.md` (`state.active_sprint`) a otevři `sprints/sprint-{N}.md`.
- Z tabulky `Sprint Targets` vezmi seznam targetů.
- Pokud `Task Queue` už existuje a není prázdná:
  - doplň jen chybějící tasks
  - nemaž ručně vložené změny, pokud nejsou zjevně špatně.

### 2) Pro každý target vytvoř návrh tasks

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

### 3) Governance constraints per task

- Z `decisions/INDEX.md` a `specs/INDEX.md` vyber relevantní kontrakty.
- Pokud backlog item explicitně odkazuje na ADR/SPEC, použij je.
- Pokud je konflikt:
  - nevymýšlej workaround
  - vytvoř intake item `intake/governance-clarification-{task_id}.md`
  - v tasku nastav `Status = DESIGN`

### 4) Zapiš per-task analýzy

- Pro každý task vytvoř `{ANALYSES_ROOT}/{task_id}-analysis.md` podle template výše.
- Pokud má task otevřené otázky → ponech `status: DRAFT` a `Task Queue Status = DESIGN`.
- Pokud je vše jasné → `status: READY` a `Task Queue Status = READY`.

**DŮLEŽITÉ: Synchronizace statusu.**  Kdykoli změníš status tasku (DESIGN → READY nebo naopak), aktualizuj **všechna tři místa**:
1. Per-task analýza (`{ANALYSES_ROOT}/{task_id}-analysis.md`, frontmatter `status:`)
2. Sprint plan Task Queue (`sprints/sprint-{N}.md`, sloupec `Status`)
3. **Backlog item** (`backlog/{task_id}.md`, frontmatter `status:`)

Pokud některé z těchto míst neaktualizuješ, `fabric-implement` uvidí nekonzistentní stav a task přeskočí.

### 5) Aktualizuj sprint plan deterministicky

Preferuj `plan-apply` (ne ruční edit), aby byl diff čistý:

```bash
python skills/fabric-init/tools/fabric.py plan-apply --plan "{WORK_ROOT}/sprints/sprint-{N}.md" --patch "{WORK_ROOT}/plans/analyze-{run_id}.yaml"
```

- Pokud `plan-apply` není praktické, uprav sprint plan ručně, ale zachovej tabulku strukturu.

### 6) Vygeneruj analyze report

- Shrň:
  - kolik targetů
  - kolik tasks (READY vs DESIGN)
  - jaké ADR/SPEC constraints byly použity
  - jaké clarifications jsi vytvořil do intake

Ulož do `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md` (schema `fabric.report.v1`).

## Self-check

- [ ] Každý task má per-task analýzu a má sekci `Constraints`.
- [ ] Každý task v Task Queue je implementovatelný bez dalších otázek, nebo je označen `DESIGN` a má intake item.
- [ ] Governance indexy existují a jsou čitelné (`decisions/INDEX.md`, `specs/INDEX.md`).

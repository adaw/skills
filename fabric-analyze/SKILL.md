---
name: fabric-analyze
description: "Deep pre-implementation analysis for sprint targets. Produces per-task analysis docs in {ANALYSES_ROOT}/, decomposes Epics/Stories into concrete Tasks, updates backlog items to READY when specification is sufficient, and updates the sprint plan Task Queue (authoritative order for WIP=1 implementation)."
---

# ANALYZE — Analýza + rozpad na Task Queue

## Účel

Před implementací musíme mít:
- jasné acceptance criteria,
- návrh řešení (API/arch, rizika),
- plán testů,
- konkrétní implementační frontu (`Task Queue`) seřazenou pro WIP=1.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-analyze" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-analyze" --event end --status OK --report "{WORK_ROOT}/reports/analyze-sprint-{N}-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


`fabric-analyze` je **most** mezi „co chceme“ (Sprint Targets) a „co přesně budeme dělat“ (Task Queue).

---

## Vstupy (povinné)

1. `{WORK_ROOT}/config.md`  
2. `{WORK_ROOT}/state.md` (sprint N)
3. `{WORK_ROOT}/sprints/sprint-{N}.md` (Sprint Targets + Task Queue)
4. `{WORK_ROOT}/backlog/{id}.md` pro všechny targety
5. `{CODE_ROOT}/` (kódový kontext) + `{TEST_ROOT}/` + `{DOCS_ROOT}/`

---

## Výstupy

- Per-task analýzy: `{ANALYSES_ROOT}/{task-id}-analysis.md`
- Aktualizovaný sprint plán: doplněná sekce `## Task Queue`
- Volitelně nové backlog items (Tasks) vytvořené z Epic/Story targetů
- Report: `{WORK_ROOT}/reports/analyze-sprint-{N}-{YYYY-MM-DD}.md`

---

## Kanonická pravidla

1. **Task Queue je autoritativní** pro implementaci. Implement/test/review se řídí pouze `Task Queue`.
2. **Do Task Queue patří pouze:** `Task | Bug | Chore | Spike`.
3. Pokud je target `Epic/Story`, analyze ho rozpadne na Tasks.
4. Pokud target nebo task nemá dost specifikace → vytvoř intake item „clarification“ a nech status `DESIGN`.
5. Pokud je specifikace dostatečná → nastav task status `READY`.

---

## Postup

### 1) Načti config + sprint plán

1. Z configu si vytáhni `SPRINT.max_tasks` a cesty v YAML sekci.
2. Ze `state.md` vezmi sprint `N`.
3. Načti `sprints/sprint-{N}.md`:
   - `Sprint Targets` tabulka = vstup
   - `Task Queue` tabulka = buď prázdná, nebo částečně vyplněná

### 2) Projdi Sprint Targets a vytvoř „worklist“

Pro každý target ID:
- načti `{WORK_ROOT}/backlog/{id}.md`
- extrahuj: `type`, `status`, `title`, `tier`, `effort`, `prio`, `depends_on/blocked_by`
- z těla extrahuj AC checkboxy (sekce „Acceptance Criteria“)

Rozděl na:
- **A) už je Task-like** (`Task/Bug/Chore/Spike`)
- **B) je container** (`Epic/Story`) → bude rozpad

### 3) Container rozpad (Epic/Story → Tasks)

Pro každý Epic/Story:
1. Vytvoř 2–8 konkrétních Tasks (dle rozsahu) tak, aby:
   - každý task má jasnou hodnotu + AC
   - tasks jsou malé (ideálně do 1–3 hodin agentního času)
2. ID generuj deterministicky:
   - `task-{parent_id}-{short_slug}`
   - pokud kolize → přidej `-2`, `-3`, ...
3. Každý nově vytvořený task ulož do `{WORK_ROOT}/backlog/{task-id}.md` podle `{WORK_ROOT}/templates/task.md`:
   - `source: intake` (nebo `source: generate` pokud to vzniklo čistě generativně)
   - `tier` zděď z parenta
   - `effort` = `TBD` pokud si nejsi jistý, jinak XS/S/M/L
   - `prio` prozatím zděď (nebo 0); PRIO recalculuje `fabric-prio` v dalším cyklu, pokud je potřeba

4. Parent Epic/Story **nezavírej**. Nech ho jako target/kontext.

> Pokud Epic/Story nemá dost informací pro rozpad → vytvoř intake item `clarification` místo tasks.

### 4) Per-task analýza (pro každý task ve výsledné worklist)

Pro každý task, který má jít do Task Queue:

Vytvoř `{ANALYSES_ROOT}/{task-id}-analysis.md`:

```markdown
# Analysis — {task-id} ({YYYY-MM-DD})

## Context
- Task: {title}
- Source: sprint-{N}
- Goal: {sprint_goal}

## Acceptance Criteria (restate)
- ...

## Design / Approach
- Chosen approach:
- Alternatives considered:
- Key tradeoffs:

## Affected files (expected)
- {CODE_ROOT}/...
- {TEST_ROOT}/...
- {DOCS_ROOT}/...

## Test plan
- Unit:
- Integration:
- Edge cases:
- Regression scope:

## Risks & mitigations
- Risk:
  - Mitigation:

## Implementation plan (WIP-friendly)
1. ...
2. ...

## Open questions
- ...
```

### 5) Nastav READY vs DESIGN

Pro každý task:
- Pokud má ≥ 3 jasná AC a je zřejmé, co upravit/testovat → nastav backlog item `status: READY`
- Jinak `status: DESIGN` a vytvoř intake item `intake/clarification-{task-id}.md`:
  - co chybí
  - 2–5 konkrétních otázek
  - návrh rozhodnutí

> Nezapomeň aktualizovat `updated:` ve frontmatter.

### 6) Aktualizuj Task Queue ve sprint plánu

1. Vezmi všechny tasky vybrané pro sprint.
2. Seřaď:
   - nejdřív tasks, které odemykají ostatní (dependency order)
   - potom zbytek podle PRIO
3. Ořízni na `SPRINT.max_tasks`.
4. Přepiš sekci `## Task Queue` tabulkou:

| Order | ID | Title | Type | Effort | Status | Depends on |
|------:|----|-------|------|--------|--------|------------|

- `Order` je autoritativní pořadí pro implement.
- Pokud je nějaký task `DESIGN`/`BLOCKED`, může být v queue, ale implement se zastaví a vytvoří intake.

### 7) Vytvoř analyze report

Vytvoř `{WORK_ROOT}/reports/analyze-sprint-{N}-{YYYY-MM-DD}.md`:
- kolik targetů bylo rozpadnuto
- kolik tasks vzniklo
- kolik tasks je READY vs DESIGN vs BLOCKED
- rizika a „first task to implement“ (Order=1)

---

## Fail conditions (musí vytvořit intake + report)

- Sprint plán nemá `Sprint Targets` tabulku
- Target ID nemá odpovídající backlog soubor
- Nelze vytvořit `Task Queue` (např. žádné tasks a zároveň chybí informace pro rozpad)

V těchto případech:
- vytvoř intake item `intake/analyze-blocked-sprint-{N}.md`
- reportuj CRITICAL v analyze reportu

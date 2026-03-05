---
name: fabric-sprint
description: "Create a sprint plan from the prioritized backlog. Selects top candidates (respecting SPRINT.max_tasks and WIP=1 flow), writes {WORK_ROOT}/sprints/sprint-{N}.md using the sprint-plan template, and sets sprint metadata in state.md (goal/start/end). Does not implement code."
---

# SPRINT — Plánování sprintu

## Účel

Vybrat nejlepší kandidáty z backlogu a vytvořit sprint plán (`sprints/sprint-{N}.md`) tak, aby:
- byl konzistentní s vizí,
- respektoval WIP=1 (single-piece flow),
- dal se bez ambiguity převést na konkrétní implementační tasky (`fabric-analyze` doplní `Task Queue`).

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-sprint" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-sprint" --event end --status OK --report "{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy (povinné)

1. `{WORK_ROOT}/config.md` (SPRINT pravidla + taxonomie)
2. `{WORK_ROOT}/state.md` (aktuální sprint N)
3. `{WORK_ROOT}/backlog.md` (prioritizovaný index)
4. `{WORK_ROOT}/backlog/*.md` (detail pro top kandidáty)
5. `{WORK_ROOT}/templates/sprint-plan.md` (kanonická šablona)

---

## Výstupy

- `{WORK_ROOT}/sprints/sprint-{N}.md` (dle šablony)
- Update `{WORK_ROOT}/state.md` (pouze):
  - `sprint_started`
  - `sprint_ends`
  - `sprint_goal`
- Report `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` (co a proč)

---


## FAST PATH (doporučeno)

Než budeš vybírat položky do sprintu, vezmi deterministický backlog snapshot:

```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

Použij ho jako zdroj pravdy pro výběr top-PRIO položek.

---

## Postup

### 1) Načti konfiguraci

- Z `{WORK_ROOT}/config.md` si přečti:
  - `SPRINT.max_days`
  - `SPRINT.max_tasks`
  - `SPRINT.wip_limit`
  - definici statusů backlogu
  - `GIT.main_branch` (jen informativně)

Pokud `SPRINT` nebo `COMMANDS` blok chybí → vytvoř intake item `intake/config-missing-sprint-or-commands.md` a pokračuj s defaulty:
- `max_days=5`, `max_tasks=10`, `wip_limit=1`

### 2) Načti state a zjisti sprint N

- Přečti `{WORK_ROOT}/state.md` → `sprint = N`
- Pokud N chybí → N=1 (a zapiš do reportu jako WARNING; neměň state, to řeší loop/init)

**Sprint counter enforcement (P2 fix):**
```bash
# Sprint counter enforcement — validate active_sprint is numeric
CURRENT_SPRINT=$(grep 'active_sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$CURRENT_SPRINT" | grep -qE '^[0-9]+$'; then
  echo "WARN: active_sprint is not a valid integer: $CURRENT_SPRINT"
  CURRENT_SPRINT=1
fi
```
This ensures the sprint counter is always a valid positive integer, preventing silent failures downstream.

### 3) Načti backlog kandidáty

Z `{WORK_ROOT}/backlog.md` vezmi tabulku a vyfiltruj:
- status NOT IN: `DONE`
- preferuj: `READY` a `DESIGN`
- `BLOCKED` může být vybrán jen pokud jde o „blocker task“ pro top priority chain (jinak ne)

Pokud backlog.md neexistuje:
- fallback: načti `{WORK_ROOT}/backlog/*.md` a seřaď podle `prio:` ve frontmatter.

### 4) Vyber Sprint Targets (co chceme posunout)

Vyber top kandidáty podle PRIO (sestupně) s těmito pravidly:

1. **Základ:** vyber až `SPRINT.max_tasks` položek (nebo méně), ale drž sprint fokus:
   - max 1–2 epics/stories (strategické cíle)
   - zbytek tasks/bugs/chores (exekuční práce)
2. Pokud je top item `Epic` nebo `Story`, může být v `Sprint Targets`,
   ale implementace musí proběhnout přes tasks (doplní analyze).
3. Každý vybraný target musí mít:
   - `title`, `type`, `tier`, `status`, `effort`, `prio` (frontmatter)
   - aspoň 1–3 AC checkboxy v těle (jinak označ jako DESIGN a počítej s analýzou)

**Sprint size limit (P2 work quality):**
- Maximum tasks per sprint: 12 (hard cap)
- Doporučený rozsah: 5-8 tasks (sweet spot)
- Pokud target decomposition > 12 tasks → rozděl na 2 sprinty
- Effort distribution: max 40% L tasks, zbytek S/M

**Sprint goal** napiš jako 1 větu, která shrnuje společný outcome všech targetů.

### 5) Vytvoř sprint plán (podle šablony)

Vytvoř soubor:
- `{WORK_ROOT}/sprints/sprint-{N}.md`

Použij `{WORK_ROOT}/templates/sprint-plan.md` a vyplň:
- sprint title (krátké)
- goal (z kroku 4)
- start = dnešek, end = start + `SPRINT.max_days` (kalendářní)
- `Sprint Targets` tabulku

`Task Queue`:
- pokud už máš konkrétní tasks typu `Task/Bug/Chore/Spike` ve statusu `READY`, můžeš předvyplnit 1–3 nejvyšší.
- jinak nech „Task Queue” s placeholderem (doplní `fabric-analyze`).

**Task Queue formát (P2 work quality):**
```markdown
| Order | ID | Type | Status | Estimate | Description |
|-------|----|------|--------|----------|-------------|
| 1 | task-xxx | Task | READY | S | Popis |
```
Povinné sloupce: Order, ID, Type, Status, Estimate. Description je volitelný.
Status: DESIGN | READY | IN_PROGRESS | IN_REVIEW | DONE | CARRY-OVER

### 6) Update state sprint metadata (povolené)

V `{WORK_ROOT}/state.md` nastav pouze:
- `sprint_started: <YYYY-MM-DD>`
- `sprint_ends: <YYYY-MM-DD>`
- `sprint_goal: "<goal>"`

Nesahej na `phase` ani `step`.

### 7) Vytvoř sprint report

V `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` uveď:
- seznam targetů + proč (PRIO, vize)
- rizika (dependencies, blocked)
- jaký typ práce to je (feature vs debt vs security)
- co analyzovat jako první (dependency ordering hint)

---

## Self-check (fail conditions)

- sprint plán byl vytvořen a má sekce `Sprint Targets` + `Task Queue`
- každý target ID odpovídá existujícímu `{WORK_ROOT}/backlog/{id}.md`
- state metadata byla nastavena (3 pole)

Pokud něco z toho neplatí → reportuj jako CRITICAL a vytvoř intake item `intake/sprint-plan-invalid.md`.

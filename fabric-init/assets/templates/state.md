# State — Fabric-Loop Orchestrator

> Šablona pro `{WORK_ROOT}/state.md`.
> Fabric-loop aktualizuje tento soubor automaticky.
> Manuální editace: pouze `error` field pro reset.

## Current

```yaml
schema: fabric.state.v1
run_id: null             # run correlation id (set at start of RUN)
phase: orientation        # orientation | planning | implementation | closing
step: vision              # aktuální skill (vision, status, implement, review...)
sprint: 1                 # číslo aktuálního sprintu
wip_item: null            # ID aktuálně rozpracovaného tasku (null = žádný)
wip_branch: null          # git branch pro aktuální task (null = žádný)
last_completed: null      # poslední úspěšně dokončený step
last_run: 2026-01-01      # datum posledního RUN (ISO date)
last_tick_at: null        # ISO datetime posledního ticku (deterministický heartbeat)
error: null               # popis chyby (null = OK, vymaž pro reset)

# Optional sprint metadata (set by fabric-sprint)
sprint_started: null        # ISO date when sprint started
sprint_ends: null            # ISO date when sprint is expected to end
sprint_goal: null            # Sprint goal text
```

## Field descriptions

| Field | Typ | Popis |
|-------|-----|-------|
| `phase` | enum | Aktuální fáze lifecycle (orientation/planning/implementation/closing) |
| `step` | string | Aktuální sub-skill (vision, status, architect, gap, generate, intake, prio, sprint, analyze, implement, test, review, close, docs, check, archive) |
| `sprint` | int | Číslo aktuálního sprintu (auto-increment po archive) |
| `wip_item` | string\|null | ID rozpracovaného backlog itemu (WIP=1 pravidlo) |
| `wip_branch` | string\|null | Git branch název pro aktuální task |
| `last_completed` | string\|null | Poslední úspěšně dokončený step |
| `last_run` | date | ISO datum posledního spuštění RUN |
| `last_tick_at` | datetime\|null | ISO datetime posledního ticku (pro debugging + determinismus) |
| `error` | string\|null | Chybový stav — nastav při selhání, vymaž při úspěchu |

## History

Append-only audit trail. Každý step přidá řádek.

| Date | Step | Result | Note |
|------|------|--------|------|
| 2026-01-01 | init | DONE | Bootstrap from empty project |

## Pravidla zápisu

1. **Atomický update:** Přepiš celý soubor najednou (ne append do Current)
2. **History append:** Přidej řádek do History tabulky
3. **Timestamp:** Každý zápis aktualizuje `last_run`
4. **Error field:** Nastav při chybě, vymaž při úspěchu
5. **wip_item + wip_branch:** Nastav při zahájení implementace, vymaž po DONE

## Crash recovery

Pokud state.md je corrupted (neparsovatelný):
1. Pokus o obnovu z git: `git show HEAD:{WORK_ROOT}/state.md`
2. Pokud ne → vytvoř nový: phase=orientation, step=vision, sprint=auto-detect
3. Loguj: `{WORK_ROOT}/reports/error-{date}.md`

Viz fabric-loop/SKILL.md pro detailní crash recovery decision tree.
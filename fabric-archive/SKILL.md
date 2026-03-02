---
name: fabric-archive
description: "Archive completed work safely. Moves DONE backlog items from backlog/ to backlog/done/, creates immutable snapshots under archive/, and archives sprint plans and key reports. Does not delete history; preserves provenance for audits."
---

# ARCHIVE — Archivace (immutable snapshots)

## Účel

Po uzavření sprintu:
- DONE backlog items se přesunou do `{WORK_ROOT}/backlog/done/`
- vytvoří se imutabilní snapshoty do `{WORK_ROOT}/archive/`
- archivují se sprint plány a reporty

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-archive" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-archive" --event end --status OK --report "{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Cíl: auditovatelnost + čistý aktivní backlog.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md` (sprint N)
- `{WORK_ROOT}/backlog/*.md` (active)
- `{WORK_ROOT}/backlog/done/` (target)
- `{WORK_ROOT}/sprints/sprint-{N}.md`
- `{WORK_ROOT}/reports/*` (zejména close/check)

---

## Výstupy

- přesunuté DONE backlog items do `{WORK_ROOT}/backlog/done/`
- snapshoty do:
  - `{WORK_ROOT}/archive/backlog/`
  - `{WORK_ROOT}/archive/sprints/`
  - `{WORK_ROOT}/archive/reports/`
- report `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`

---


## FAST PATH (doporučeno) — archivace deterministicky jedním příkazem

1) Spusť deterministickou archivaci sprintu:

```bash
python skills/fabric-init/tools/fabric.py archive-sprint > "{WORK_ROOT}/reports/archive-sprint-{SPRINT_NUMBER}-{YYYY-MM-DD}.json"
```

2) Pokud JSON vrací `ok=false`, vytvoř report s chybou (missing backlog / remaining_not_done) a **STOP**.

3) Vytvoř report `{WORK_ROOT}/reports/archive-sprint-{SPRINT_NUMBER}-{YYYY-MM-DD}.md`:
- odkaz/summary na JSON výstup
- co bylo zkopírováno (stamp dir)
- co bylo přesunuto do `backlog/done/`

---

## Postup

### 1) Najdi DONE backlog items v aktivním backlogu

Pro každý `{WORK_ROOT}/backlog/{id}.md` (mimo done/):
- parse YAML a vyber ty, které splňují:
  - `status: DONE`
  - `merge_commit` není null (bylo mergnuto v CLOSE)

Pokud žádné:
- vytvoř report „0 items archived“ a DONE

### 2) Přesuň DONE items do backlog/done/

Pro každý DONE item:
- cílový path: `{WORK_ROOT}/backlog/done/{id}.md`
- pokud už tam existuje:
  - porovnej obsah; pokud stejné → skip
  - pokud jiné → ulož do `archive/quarantine/{id}-{YYYY-MM-DD}.md` a vytvoř intake item (konflikt)
- jinak:
  - move (ne copy) do backlog/done

### 3) Snapshot do archive/backlog

Pro každý DONE item (před/po move):
- vytvoř snapshot soubor:
  - `{WORK_ROOT}/archive/backlog/{id}-{YYYY-MM-DD}.md`
- snapshot je imutabilní (už ho neměň)

### 4) Archivuj sprint plán a reporty

Z `state.md` zjisti sprint `N`.
- pokud existuje `{WORK_ROOT}/sprints/sprint-{N}.md`:
  - zkopíruj do `{WORK_ROOT}/archive/sprints/sprint-{N}-{YYYY-MM-DD}.md`

Vyber klíčové reporty pro sprint:
- `close-sprint-{N}-*.md`
- `check-*.md`
- `docs-*.md`
- `prio-*.md` (volitelně)

Zkopíruj do `{WORK_ROOT}/archive/reports/` se stejným názvem (nebo s prefixem sprintu).

### 5) Archive report

Vytvoř `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`:
- seznam přesunutých itemů
- seznam snapshotů
- co bylo archivováno (sprint plan, reporty)
- konflikty (quarantine) + vytvořené intake items

---

## Self-check

- DONE items už nejsou v `{WORK_ROOT}/backlog/` (kromě done/)
- existují snapshoty v `archive/backlog/`
- report existuje

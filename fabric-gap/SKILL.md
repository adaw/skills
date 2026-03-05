---
name: fabric-gap
description: "Detect gaps between vision, backlog, and reality (code, tests, docs). Produces a gap report and generates actionable intake items (source=gap) for the most important missing pieces (features, tests, docs, security, reliability)."
---

# GAP — Mezera mezi vizí, backlogem a realitou

## Účel

Porovnat:
1) **Vizi** (`{WORK_ROOT}/vision.md`) — co má existovat a proč  
2) **Backlog** (`{WORK_ROOT}/backlog.md` + items) — co je naplánované  
3) **Realitu** (`{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`) — co fakt existuje

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-gap" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-gap" --event end --status OK --report "{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


A z toho vytvořit:
- `reports/gap-*.md`
- 0..N intake itemů (top gaps), které posunou projekt správným směrem

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md`
- `{WORK_ROOT}/backlog.md` + `{WORK_ROOT}/backlog/*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`

---

## Výstupy

- `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- intake items v `{WORK_ROOT}/intake/` dle `{WORK_ROOT}/templates/intake.md`:
  - `source: gap`
  - `initial_type` typicky Task/Chore/Bug
  - `raw_priority` podle dopadu

---

## Postup

### 1) Extrahuj „capabilities“ z vize

Z `vision.md` + `{VISIONS_ROOT}/*.md` vytáhni seznam:
- pillars / goals / must-haves (z core vision)
- rozšířené cíle a detaily z sub-vizí

Výsledek: 5–30 capabilities (krátké názvy).

### 2) Mapuj backlog coverage

- Z backlog indexu vezmi top itemy a zjisti, jestli odkazují na capability.
- Pokud backlog itemy nejsou explicitně tagované, mapuj heuristicky podle title/keywords.

Výsledek: capability → {backlog IDs}

### 3) Reality check (code, tests, docs)

Pro každou capability:
- **Code existence signal:** existuje relevantní modul/entrypoint?
- **Tests signal:** existují testy pro klíčové chování?
- **Docs signal:** je to popsáno v docs?

Neřeš přesné coverage číslo; stačí kvalitativní „Yes/No/Unknown“ + evidence.

### 4) Identifikuj gap typy

Vyrob seznam gaps:

A) Vision → Backlog gap  
- capability nemá žádné backlog items

B) Backlog → Code gap  
- backlog item status READY/IN_PROGRESS, ale kód/relevantní soubory neexistují (nebo jsou stub)

C) Code → Tests gap  
- změny bez testů, kritické moduly bez test coverage signálu

D) Code → Docs gap  
- public API / usage není dokumentované

E) Security/Operational gap  
- chybí input validation, secrets hygiene, logging, error handling, etc.

### 5) Vyber top 3–10 gaps a vytvoř intake items

Pro každý top gap vytvoř intake item ({WORK_ROOT}/templates/intake.md):
- `title`: akční („Dopsat testy pro X”, „Zavést rate limiting”, „Dokumentovat CLI usage”)
- `source: gap`
- `initial_type`: Task/Bug/Chore/Spike
- `raw_priority`: 8–10 pro critical, 5–7 pro medium

Do těla:
- Popis mezery
- Evidence (soubor, modul, nebo „missing”)
- Doporučená akce + AC návrh

**Testovatelnost gap detection (P2 work quality):**
Každý identifikovaný gap musí mít:
- Konkrétní evidence (soubor:řádek nebo chybějící artefakt)
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Doporučená akce (ne jen “opravit” — konkrétně co a kde)
- Ověřitelné kritérium (jak poznat že gap je uzavřen)

### 6) Gap report

`reports/gap-{date}.md`:
- shrnutí: kolik capabilities má coverage
- tabulka gaps (severity + evidence)
- seznam vytvořených intake items

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/gap-{YYYY-MM-DD}.md`
- report obsahuje: Vision↔Backlog gaps, Backlog↔Code gaps, Code↔Tests gaps, Docs drift, Security/Operational gaps
- každé CRITICAL/HIGH gap má buď intake item, nebo explicitní vysvětlení proč ne
- počet intake items: 3–10

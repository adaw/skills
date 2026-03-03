---
name: fabric-architect
description: "Architectural audit of the current codebase. Identifies key components, boundaries, risks, and improvement opportunities. Produces an architect report and converts the top actionable findings into intake items (source=arch) for triage."
---

# ARCHITECT — Architektonický audit + actionable intake

## Účel

Rychle zmapovat realitu kódu a najít:
- arch rizika (coupling, layering violations, missing boundaries),
- debt hotspots (complexity, flaky tests, build pain),
- bezpečnostní/operational gaps,
- a konkrétní návrhy na zlepšení.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-architect" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-architect" --event end --status OK --report "{WORK_ROOT}/reports/architect-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Výstup musí být:
- report pro lidi/agentní pipeline,
- + několik konkrétních intake itemů, které lze rovnou triagovat do backlogu.

---

## Vstupy

- `{WORK_ROOT}/config.md` (CODE_ROOT, TEST_ROOT, DOCS_ROOT)
- `{WORK_ROOT}/vision.md` (pro alignment)
- `{WORK_ROOT}/decisions/*.md` (existující architektonická rozhodnutí — respektuj je, nenavrhuj to co je už rozhodnuto)
- `{WORK_ROOT}/specs/*.md` (technické kontrakty — ověř, zda kód odpovídá)
- `{CODE_ROOT}/` (kód)
- `{TEST_ROOT}/` (testy)
- `{DOCS_ROOT}/` (docs)

---

## Výstupy

- `{WORK_ROOT}/reports/architect-{YYYY-MM-DD}.md`
- 0..N intake items v `{WORK_ROOT}/intake/`:
  - `source: arch`
  - podle `{WORK_ROOT}/templates/intake.md`
- 0..N nových decisions v `{WORK_ROOT}/decisions/`:
  - dle `{WORK_ROOT}/templates/adr.md`
  - `status: proposed` (přijato bude po review)
- 0..N nových/aktualizovaných specs v `{WORK_ROOT}/specs/`:
  - pokud audit odhalí nezdokumentovaný kontrakt → vytvoř spec

---

## Postup

### 1) Context scan

- přečti `vision.md` (pillars/goals/principles)
- přečti `{WORK_ROOT}/decisions/*.md` (existující ADR — respektuj accepted decisions, ověř zda kód dodržuje)
- přečti `{WORK_ROOT}/specs/*.md` (technické kontrakty — ověř zda kód odpovídá specifikacím)
- proveď rychlý scan repo struktury:
  - entrypoints, core modules, dependency boundaries
  - test layout
  - docs + ADR presence

### 2) Map architektury (stručně, ale konkrétně)

Do reportu uveď:
- komponenty + odpovědnosti
- boundary map (co je core vs edge)
- dependency graph (high-level)
- build/test pipeline snapshot (zhruba)

### 3) Najdi hotspots

Hledej:
- velké soubory / vysoká komplexita
- cyklické importy
- duplication
- chybějící testy pro klíčové moduly
- nejasné vlastnictví configu
- security footguns (secrets, auth, input parsing)

### 4) Z toho vyrob actionable findings

V reportu udělej tabulku:

| # | Finding | Severity | Evidence | Suggested action |
|---:|--------|----------|----------|------------------|

Severity: CRITICAL/HIGH/MEDIUM/LOW

### 5) Vytvoř intake items (top 3–7)

Pro každé finding s CRITICAL/HIGH (a vybrané MEDIUM):
- vytvoř intake item soubor dle `{WORK_ROOT}/templates/intake.md`:
  - `title`: krátké a akční
  - `source: arch`
  - `initial_type`: typicky `Chore` nebo `Task`
  - `raw_priority`: 7–10 pro CRITICAL/HIGH, 4–6 pro MEDIUM
  - `linked_vision_goal`: pokud je zřejmé
- do těla napiš:
  - evidence (soubor, modul, pattern)
  - riziko (proč to bolí)
  - doporučenou akci (konkrétně)

### 6) Vytvoř ADR pro klíčová rozhodnutí

Pokud audit odhalí architektonické rozhodnutí, které:
- ovlivňuje víc než 1 modul/komponentu,
- definuje konvenci nebo kontrakt,
- vybírá z více alternativ,

→ vytvoř ADR v `{WORK_ROOT}/decisions/` dle `{WORK_ROOT}/templates/adr.md`:
- ID: `D{NNNN}` (inkrementální, vyšší než existující)
- `status: proposed`
- v sekci Kontext referuj finding z reportu
- v sekci Alternativy popiš zvažované přístupy

Pokud audit odhalí nezdokumentovaný implicitní kontrakt v kódu (API formát, schéma, protokol):
→ vytvoř spec v `{WORK_ROOT}/specs/` s popisem kontraktu a `Status: Draft`

> **Pravidlo:** Decisions se NIKDY nevytváří jako `accepted` — vždy `proposed`. Přijímá je review nebo člověk.

---

## Self-check

- report existuje
- každé CRITICAL/HIGH finding má buď intake item, nebo explicitní zdůvodnění proč ne
- pokud vznikly nové decisions → jsou v `{WORK_ROOT}/decisions/` se `status: proposed`
- pokud vznikly nové specs → jsou v `{WORK_ROOT}/specs/`
- existující accepted decisions nebyly porušeny (nebo je v reportu vysvětleno proč)

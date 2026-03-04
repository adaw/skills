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
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md` (ADR / governance)
- `{WORK_ROOT}/specs/` + `specs/INDEX.md` (technical specs)
- `{CODE_ROOT}/` (kód)
- `{TEST_ROOT}/` (testy)
- `{DOCS_ROOT}/` (docs)

---

## Výstupy

- `{WORK_ROOT}/reports/architect-{YYYY-MM-DD}.md`
- (volitelně) 0..N nových governance artefaktů:
  - `decisions/ADR-*.md` (status: proposed)
  - `specs/SPEC-*.md` (status: draft)
  - po vytvoření spusť: `python skills/fabric-init/tools/fabric.py governance-index`
- 0..N intake items v `{WORK_ROOT}/intake/`:
  - `source: arch`
  - podle `{WORK_ROOT}/templates/intake.md`

---

## Postup

### 1) Context scan

- přečti `vision.md` (pillars/goals/principles)
- přečti `decisions/INDEX.md` a `specs/INDEX.md` (pokud existují) — chápej to jako **kontrakt**
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

### 3) Governance audit (ADR/specs)

Zkontroluj:
- zda existují klíčové ADR pro kritické volby (bezpečnost, multi-tenant, data model, integrace, P2P/memory atd.)
- zda existují specs pro části, kde bez toho vzniká chaos (API, storage, scheduler, protocol/logging)
- drift: kde kód očividně odporuje accepted ADR/spec (pokud existují)
- „mrtvé“ proposed ADR nebo draft specs (stárnou a nikdo je neřeší)

Pokud najdeš zásadní chybějící rozhodnutí/spec:
- navrhni nový soubor:
  - `decisions/ADR-XXXX-<slug>.md` (status: proposed)
  - `specs/SPEC-XXXX-<slug>.md` (status: draft)
- použij runtime template:
  - `{TEMPLATES_ROOT}/adr.md`
  - `{TEMPLATES_ROOT}/spec.md`
- v těle uveď: Context, Decision/Spec, Consequences, Evidence, Alternatives.
- po vytvoření spusť: `python skills/fabric-init/tools/fabric.py governance-index`

### 4) Najdi hotspots

Hledej:
- velké soubory / vysoká komplexita
- cyklické importy
- duplication
- chybějící testy pro klíčové moduly
- nejasné vlastnictví configu
- security footguns (secrets, auth, input parsing)

### 5) Z toho vyrob actionable findings

V reportu udělej tabulku:

| # | Finding | Severity | Evidence | Suggested action |
|---:|--------|----------|----------|------------------|

Severity: CRITICAL/HIGH/MEDIUM/LOW

### 6) Vytvoř intake items (top 3–7)

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

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/architect-{YYYY-MM-DD}.md`
- report obsahuje: Component map, Coupling/layering analýzu, Debt hotspots, Security assessment
- každé CRITICAL/HIGH finding má buď intake item, nebo explicitní zdůvodnění proč ne
- počet intake items: 3–7 (ne 0, ne 20+)

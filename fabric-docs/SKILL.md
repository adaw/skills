---
name: fabric-docs
description: "Synchronize documentation with the current codebase and recent merged changes. Updates {DOCS_ROOT}/ (and optionally in-code docstrings/README) based on code reality, adds/updates ADRs if needed, and writes a docs sync report. Never invent APIs that are not in code."
---

# DOCS — Dokumentace sync (code → docs)

## Účel

Po merge (CLOSE) musí dokumentace odpovídat realitě:
- nová funkcionalita je popsána,
- změny API jsou zdokumentované,
- ADR existuje pro významná arch rozhodnutí.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-docs" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-docs" --event end --status OK --report "{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


`fabric-docs` je konzervativní: **nepřidává vymyšlené informace**.

---

## Vstupy

- `{WORK_ROOT}/config.md` (DOCS_ROOT, CODE_ROOT)
- `{WORK_ROOT}/reports/close-sprint-*-*.md` (co se mergnulo)
- `{CODE_ROOT}/` (aktuální main)
- `{DOCS_ROOT}/` (existující docs)
- volitelně `{WORK_ROOT}/archive/` (historie)

---

## Výstupy

- aktualizované docs soubory v `{DOCS_ROOT}/`
- volitelně nové ADR v `{DOCS_ROOT}/adr/` (pokud projekt používá)
- report `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`

---

## Postup

### 1) Načti context

1. Otevři poslední `close` report a vylistuj:
   - merged items (ID + title)
   - změny chování / API (pokud jsou v reportu)
2. Pro každý merged item:
   - najdi backlog item (pro popis a AC)
   - najdi dotčené soubory (sekce „Dotčené soubory“ nebo diff, pokud existuje)

### 2) Zjisti, co je „doc-worthy“

Doc-worthy změny typicky:
- nový endpoint / public API / CLI command
- změna konfigurace
- změna chování, která může rozbít integrace
- nové bezpečnostní/operational požadavky
- nové limity/performance charakteristiky

Není doc-worthy:
- čistý refactor bez změny behavioru (pokud nemá dopad)
- interní rename

### 3) Aktualizuj docs (konzistentně s kódem)

- Přidávej odkazy na konkrétní moduly/entrypoints v `{CODE_ROOT}/`.
- Pokud existují README, aktualizuj je.
- Pokud projekt používá doc generator (MkDocs, Sphinx, Docusaurus), dodrž strukturu.

**Pravidlo:** Vždy ověř informaci v kódu nebo testech.

### 4) CHANGELOG update

Pokud projekt má `CHANGELOG.md` (nebo `{DOCS_ROOT}/CHANGELOG.md`):
- Přidej entry pro každý merged item pod sekci `## [Unreleased]` (nebo aktuální verzi)
- Formát: `- **{type}({id}):** {title}` (jednoduše, strojově čitelně)
- Pokud CHANGELOG neexistuje a merged items obsahují user-facing změny → vytvoř intake item `intake/docs-create-changelog.md`

### 5) ADR (pokud došlo k arch změně)

Pokud merged změna mění arch (např. nový storage, nový auth model):
- vytvoř ADR soubor dle `{WORK_ROOT}/templates/adr.md` v odpovídajícím adr adresáři (typicky `{DOCS_ROOT}/adr/`)

### 6) Vytvoř docs report

`{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`:

- co bylo aktualizováno (seznam souborů)
- co je stále TODO (a proč)
- zda byl vytvořen ADR
- odkazy na merged items

---

## Self-check

- změny v `{DOCS_ROOT}/` odpovídají realitě kódu (žádné vymyšlené API)
- report existuje

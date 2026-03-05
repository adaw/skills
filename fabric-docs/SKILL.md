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
   - najdi dotčené soubory (sekce „Dotčené soubory” nebo diff, pokud existuje)

**MINIMUM:** seznam ≥1 merged item(u) s ID, title, a dotčenými soubory

### 2) Zjisti, co je „doc-worthy”

Doc-worthy změny typicky:
- nový endpoint / public API / CLI command
- změna konfigurace
- změna chování, která může rozbít integrace
- nové bezpečnostní/operational požadavky
- nové limity/performance charakteristiky

Není doc-worthy:
- čistý refactor bez změny behavioru (pokud nemá dopad)
- interní rename

**MINIMUM:** klasifikace KAŽDÉHO merged itemu jako „doc-worthy” nebo „skip” + zdůvodnění (1 věta per item)

### 3) Aktualizuj docs (konzistentně s kódem)

- Přidávej odkazy na konkrétní moduly/entrypoints v `{CODE_ROOT}/`.
- Pokud existují README, aktualizuj je.
- Pokud projekt používá doc generator (MkDocs, Sphinx, Docusaurus), dodrž strukturu.

**Pravidlo:** Vždy ověř informaci v kódu nebo testech.

**MINIMUM:** Pro každý doc-worthy item ≥1 aktualizovaný soubor v `{DOCS_ROOT}/` s explicitní linkováním na code

**Test metodika pro docs (P2 work quality):**
Po aktualizaci docs ověř:
- Všechny code examples v docs jsou spustitelné (syntax check)
- Interní odkazy (cross-references) vedou na existující soubory
- API docs odpovídají aktuálním signatures (grep pro nesoulad)

**Coverage threshold (P2 work quality):**
- Všechny veřejné funkce/třídy v `{CODE_ROOT}/` musí mít docstring (target: ≥80%)
- README.md aktuální (ověř: `make` commands, install instrukce, architecture popis)
- CHANGELOG aktuální (pokud existuje)

**Anti-patterns (zakázáno):**
- Neaktualizuj docs bez ověření v kódu (žádné spekulativní API)
- Nevynechávaej „opravdu malé" API změny (všechny veřejné API mají být zdokumentovány)
- Nepřidávaj zastaralé příklady (vždy check-out aktuální kód)

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

**MINIMUM obsah reportu:**
- **Co bylo aktualizováno:** seznam souborů v tabulce: `| File | Change | Merged Item |`
- **Co je stále TODO:** pokud existuje, zdůvodnění (chybí info, cekání na AC, ...)
- **ADR:** „Vytvořen:" (cesta) nebo „Nepotřebný"
- **Merged items:** tabulka `| ID | Title | Doc-worthy? | Updated docs |`
- **Coverage check:** ≥80% docstrings? README OK? CHANGELOG OK? (PASS/WARN/FAIL)

**Šablona:**
```markdown
---
schema: fabric.report.v1
kind: docs
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# docs — Report {YYYY-MM-DD}

## Souhrn
{1 věta: kolik items bylo zpracováno, kolik doc-worthy, kolik souborů změněno}

## Merged items
| ID | Title | Doc-worthy | Updated |
|----|-------|-----------|---------|
| {id} | {title} | {YES/NO} | {file list or "—"} |

## Updated files
| File | Change | Reference code |
|------|--------|-----------------|
| {path} | {co se změnilo} | {modul/funkce/třída} |

## Coverage check
- Public docstrings: {N}% (target: ≥80%)
- README.md: {OK|STALE}
- CHANGELOG.md: {OK|CREATED|N/A}

## ADR
{Vytvořen: {path} or Nepotřebný — {zdůvodnění}}

## TODO
{Seznam zbývajících itemů nebo "žádné"}
```

---

## Self-check

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`
- [ ] Report má povinné sekce: Souhrn, Merged items, Updated files, Coverage check, ADR, TODO

### Quality checks
- [ ] Všechny doc-worthy items mají ≥1 aktualizovaný soubor v `{DOCS_ROOT}/`
- [ ] Žádná doc změna bez ověření v kódu (grep cross-check)
- [ ] Všechny code examples jsou syntakticky korektní
- [ ] Interní linky v docs vedou na existující soubory (check ls)
- [ ] Coverage check runnable (docstring count, README status, CHANGELOG status)

### Invarianty
- [ ] Žádný soubor mimo `{DOCS_ROOT}/` nebyl modifikován (pokud skill explicitně nepředepisuje)
- [ ] Pokud byl vytvořen ADR → je v `{DOCS_ROOT}/adr/`
- [ ] Pokud byl vytvořen CHANGELOG → má správný formát (## [Unreleased] nebo ## [version])

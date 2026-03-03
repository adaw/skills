---
name: fabric-check
description: "Consistency and quality audit of the Fabric workspace. Validates directory structure, templates, backlog item schemas, backlog index, sprint plan integrity, and basic code health signals (via configured COMMANDS). Applies safe auto-fixes (e.g., regenerate backlog.md) and creates intake items for anything requiring human/agent follow-up. Writes an audit report."
---

# CHECK — Konzistenční audit + safe auto-fix

## Účel

Najít rozbité invariants dřív, než se pipeline rozjede dál:
- špatné cesty / chybějící adresáře
- rozbitá metadata (YAML schema)
- backlog index mimo sync
- sprint plán nevalidní
- config COMMANDS chybí

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-check" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-check" --event end --status OK --report "{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Aplikovat jen **bezpečné** automatické opravy (idempotentní) a vše ostatní převést na intake items.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/*.md`
- `{WORK_ROOT}/sprints/*.md`
- `{WORK_ROOT}/templates/*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` (existence + volitelné commands)

---

## Výstupy

- audit report: `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` (dle `{WORK_ROOT}/templates/audit-report.md`)
- safe auto-fix changes (např. regenerace backlog.md)
- intake items pro CRITICAL/WARNING:
  - `{WORK_ROOT}/intake/check-*.md`

---

## Status taxonomie (z config.md)

Backlog statusy musí být:
`IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE`

---

## Postup

### 1) Strukturální integrita workspace

Ověř existenci:
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/vision.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/` + `backlog/done/`
- `{WORK_ROOT}/intake/` + `intake/done/` + `intake/rejected/`
- `{WORK_ROOT}/reports/`
- `{WORK_ROOT}/sprints/`
- `{WORK_ROOT}/analyses/`
- `{WORK_ROOT}/templates/`
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`
- `{WORK_ROOT}/reviews/` + `reviews/INDEX.md`

CRITICAL pokud chybí → vytvoř intake item `check-missing-structure.md`.

### 2) Templates integrity

Ověř, že v `{WORK_ROOT}/templates/` existují povinné šablony (viz config).
Pokud chybí → WARNING + intake.

### 3) Backlog item schema audit

Z `{WORK_ROOT}/config.md` načti kontrakty:
- `SCHEMA.backlog_item`
- `ENUMS.statuses`, `ENUMS.tiers`, `ENUMS.efforts`, `ENUMS.types`

Pro každý `{WORK_ROOT}/backlog/*.md` (mimo `backlog/done/`):
- parse YAML frontmatter
- ověř povinné klíče:
  - `schema`, `id`, `title`, `type`, `tier`, `status`, `effort`, `created`, `updated`, `source`, `prio`
- validuj hodnoty:
  - `schema` == `SCHEMA.backlog_item`
  - `status` ∈ `ENUMS.statuses`
  - `type` ∈ `ENUMS.types`
  - `tier` ∈ `ENUMS.tiers`
  - `effort` ∈ `ENUMS.efforts`
  - `prio` je integer
  - filename odpovídá `id` (např. `{id}.md`)

Safe auto-fix (idempotentní):
- pokud chybí `schema`, doplň `schema: <SCHEMA.backlog_item>`
- pokud chybí `updated`, doplň `updated: {YYYY-MM-DD}`
- pokud chybí `prio`, doplň `prio: 0` (a reportuj WARNING; prio to později přepočítá)

Ne-safe (→ intake + WARNING/CRITICAL):
- chybějící `id` nebo `title`
- `schema` existuje, ale je **jiný** než očekávaný (drift)
- nevalidní status/type/tier/effort

### 4) Backlog index sync

Regeneruj „expected“ tabulku z backlog itemů a porovnej s `{WORK_ROOT}/backlog.md`.

Pokud nesedí:
- safe auto-fix: přepiš backlog.md na kanonickou tabulku (seřazení PRIO desc)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```
- zapiš do reportu jako FIXED


### 4.1) Governance integrity (decisions/specs/reviews)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py governance-index
python skills/fabric-init/tools/fabric.py governance-scan
```

Vyhodnoť:
- chybějící `INDEX.md` → WARNING + intake (nebo auto-fix přes `governance-index`)
- proposed ADR starší než `GOVERNANCE.decisions.stale_proposed_days` → WARNING + intake
- draft SPEC starší než `GOVERNANCE.specs.stale_draft_days` → WARNING + intake
- missing `date`/`status` ve governance souborech → WARNING + intake (oprava: doplnit metadata)

Pozn.: `governance-index` je safe auto-fix (jen přegeneruje indexy).


### 5) Sprint plan audit (pokud existuje)

Najdi aktuální sprint:
- ze `state.md` (`sprint: N`)
- sprint file: `{WORK_ROOT}/sprints/sprint-{N}.md` (pokud existuje)

Validace:
- má sekce `## Sprint Targets`
- má sekce `## Task Queue` s tabulkou
- každý Task Queue `ID` existuje jako backlog item
- `Order` je unikátní a začíná od 1 (nebo je aspoň monotónní)

Pokud Task Queue odkazuje na neexistující backlog item → CRITICAL + intake.

### 6) Config COMMANDS sanity

Z configu ověř:

- `COMMANDS.test` není `TBD` ani prázdné
- `COMMANDS.lint` není `TBD` *(prázdné = vypnuto)*
- `COMMANDS.format_check` není `TBD` *(prázdné = vypnuto)*

Pokud `COMMANDS.test` je `TBD` nebo prázdné:
- vytvoř intake item `intake/check-missing-test-command.md`
- reportuj **CRITICAL** (bez testů nelze bezpečně pokračovat)

Pokud `COMMANDS.lint` nebo `COMMANDS.format_check` je `TBD`:
- vytvoř intake item `intake/check-config-commands-tbd.md`
- reportuj **WARNING** (bez nich nelze enforce některé quality gates)

Pokud je `COMMANDS.lint` nebo `COMMANDS.format_check` prázdné:
- reportuj `SKIPPED`
- vytvoř intake item `intake/check-recommend-enable-lint-or-format.md` (doporučení)

Pokud `QUALITY.mode` je `strict` a lint/format jsou prázdné (`""`):
- reportuj **CRITICAL**
- vytvoř intake item `intake/check-strict-mode-missing-lint-or-format.md`
- FAIL

### 7) Volitelné: rychlé runtime checks (pokud commands existují)

Pokud repo má čistý working tree:

Spusť v tomto tvaru (aby nikdy neběžel prázdný příkaz):

```bash
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi
{COMMANDS.test}
```

Výsledek zapiš do reportu (PASS/FAIL).

Pokud by to bylo příliš drahé, zaznamenej to jako `skipped` s důvodem.

**Volitelně (framework self-test):**
- spusť statický validator:
  ```bash
  python skills/fabric-init/tools/validate_fabric.py --workspace --runnable
  ```
  Pokud failne → CRITICAL + intake item `intake/check-validator-failed.md`.

### 8) Vygeneruj audit report

Vytvoř `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` dle `{WORK_ROOT}/templates/audit-report.md`:
- summary + score
- CRITICAL/WARNING findings
- auto-fixes
- intake items created

---

## Scoring (doporučené)

- Start 100
- -30 za každý CRITICAL
- -10 za každý WARNING
- +5 pokud byly provedeny safe auto-fixes

---

## Self-check

- report existuje
- pokud byly auto-fixes, jsou popsány
- pro každý CRITICAL existuje intake item

---
name: fabric-intake
description: "Triage intake items into normalized backlog items (Epic/Story/Task/Bug/Chore/Spike). Creates/updates {WORK_ROOT}/backlog/*.md using canonical templates, regenerates {WORK_ROOT}/backlog.md index, and moves processed intake files to intake/done or intake/rejected (never deletes)."
---

# INTAKE — Triage (intake → backlog)

## Účel

Zpracovat surové vstupy v `{WORK_ROOT}/intake/` a převést je do standardizovaných backlog položek.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-intake" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-intake" --event end --status OK --report "{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Výsledek musí být:
- konzistentní s config taxonomií,
- deduplikovaný,
- připravený na prioritizaci (`fabric-prio`),
- a auditovatelný (processed intake se **přesouvá**, nemaže).

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/intake/*.md` (kanonicky podle `{WORK_ROOT}/templates/intake.md`)
- `{WORK_ROOT}/backlog/*.md` (kvůli deduplikaci)
- `{WORK_ROOT}/templates/*.md`

---

## Výstupy

- nové nebo aktualizované backlog items: `{WORK_ROOT}/backlog/{id}.md`
- regenerovaný index: `{WORK_ROOT}/backlog.md`
- intake report: `{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md`
- přesunuté intake soubory:
  - `{WORK_ROOT}/intake/done/`
  - `{WORK_ROOT}/intake/rejected/`

---

## Kanonická pravidla

1. **Jeden intake soubor = jeden intake item** (YAML frontmatter + sekce).
2. Intake se nikdy nemaže. Po zpracování se přesune do `done/` nebo `rejected/` a doplní se důvod.
3. Každý backlog item MUSÍ mít YAML frontmatter dle config schema (id/title/type/tier/status/effort/created/source/prio…).
4. `prio` z intake je vždy jen start (`0`). Finální PRIO počítá `fabric-prio`.
5. Pokud intake je nejasný → vytvoř backlog item se statusem `IDEA` a otázkami v sekci „Open questions“.

---


## FAST PATH (doporučeno) — scan → plan → apply (bez ručních přesunů/editací)

1) Seznam intake položek (strojově):

```bash
python skills/fabric-init/tools/fabric.py intake-scan --json-out "{WORK_ROOT}/reports/intake-scan-{YYYY-MM-DD}.json"
```

2) Pro každou intake položku rozhodni:
- dedupe / merge / reject / convert → backlog item (Epic/Story/Task/Bug/Chore/Spike)

3) Vygeneruj plan `{WORK_ROOT}/reports/intake-plan-{YYYY-MM-DD}.yaml`:

```yaml
schema: fabric.plan.v1
ops:
  - op: backlog.create
    fields:
      id: "<new-id>"
      title: "<title>"
      type: "Task"
      tier: "T1"
      status: "IDEA"
      effort: "M"
      source: "intake"
      created: "{YYYY-MM-DD}"
      updated: "{YYYY-MM-DD}"
  - op: fs.move
    src: "{WORK_ROOT}/intake/<file>.md"
    dest_dir: "{WORK_ROOT}/intake/done/"
  - op: backlog.index
```

4) Aplikuj deterministicky:

```bash
python skills/fabric-init/tools/fabric.py apply "{WORK_ROOT}/reports/intake-plan-{YYYY-MM-DD}.yaml"
```

---

## Postup

### 1) Načti config a připrav prostředí

- ověř existenci `{WORK_ROOT}/intake/`, `{WORK_ROOT}/backlog/`, `{WORK_ROOT}/templates/`
- pokud některý chybí → CRITICAL → vytvoř intake item `intake/intake-missing-runtime-structure.md` a FAIL

### 2) Najdi „pending“ intake soubory

Zpracuj pouze:
- `{WORK_ROOT}/intake/*.md`
- ignoruj `{WORK_ROOT}/intake/done/` a `{WORK_ROOT}/intake/rejected/`

Pokud nejsou žádné pending intake items:
- vytvoř report `reports/intake-{date}.md` s „0 items“
- DONE

### 3) Pro každý intake item proveď triage

#### 3.1 Parse intake (kanonicky)

Z intake YAML vytáhni:
- `id`, `title`, `source`, `date`, `created_by`
- `initial_type`, `raw_priority`, `linked_vision_goal`

Z těla vytáhni:
- Popis
- Kontext
- Doporučená akce

Pokud intake nemá YAML frontmatter:
- fallback (legacy): první H1 = title, zbytek = description
- do reportu napiš WARNING „legacy intake format“

#### 3.2 Deduplikace

Před vytvořením backlog itemu:
- hledej existující backlog file se stejným nebo velmi podobným title (fuzzy)
- pokud existuje:
  - přidej do existujícího backlog itemu sekci `## Intake references` s odkazem na intake file
  - intake přesun do `intake/done/` (důvod: merged/duplicate)
  - pokračuj dalším intake

#### 3.3 Urči Type

Primárně použij `initial_type`. Pokud chybí, inferuj:
- pokud popis obsahuje „bug“, „crash“, „fails“ → Bug
- pokud jde o „refactor/tooling/docs“ → Chore
- pokud jde o „research/unknown“ → Spike
- jinak Task (default)

#### 3.4 Urči Tier (T0–T3)

Použij jednoduchou heuristiku:
- raw_priority 9–10 → T0
- 6–8 → T1
- 3–5 → T2
- 1–2 → T3

Pokud `linked_vision_goal` je kritické (výslovně označené ve vision) → posuň o 1 tier výš (max T0).

#### 3.5 Urči Status (IDEA / DESIGN / READY)

- `READY`, pokud intake už obsahuje:
  - konkrétní doporučenou akci (co změnit) + hrubý test plan / evidence
- jinak `DESIGN`, pokud je zřejmý scope, ale chybí detail (bude doplněno v analyze)
- jinak `IDEA`, pokud je to jen nápad bez detailů

Effort nastav `TBD` (pokud si nejsi jistý), jinak XS/S/M/L.

#### 3.6 Vygeneruj backlog ID (deterministicky)

Pravidlo:
- prefix podle typu: `epic-`, `story-`, `task-`, `bug-`, `chore-`, `spike-`
- slug z title: lowercase + hyphen
- pokud soubor už existuje → suffix `-2`, `-3`, ...

Příklad:
- „Add auth middleware“ → `task-add-auth-middleware`

#### 3.7 Vytvoř backlog item soubor

Vytvoř `{WORK_ROOT}/backlog/{id}.md` podle odpovídající šablony:
- Epic → `{WORK_ROOT}/templates/epic.md`
- Story → `{WORK_ROOT}/templates/story.md`
- Task/Bug/Chore/Spike → `{WORK_ROOT}/templates/task.md` (změň `type:`)

Vyplň minimálně:
- `id`, `title`, `type`, `tier`, `status`, `effort`, `created`, `updated`, `source: intake`, `prio: 0`
- do těla vlož:
  - „Příkaz odemykující“ (1 věta)
  - popis + kontext z intake
  - Acceptance Criteria (aspoň 3 checkboxy; když nevíš, formuluj hypotézy)
  - „Open questions“ pokud status není READY
  - odkaz na intake (provenance)

#### 3.8 Přesuň intake do done/rejected

Standardně: přesun do `{WORK_ROOT}/intake/done/`.

Pouze pokud je intake úplně nerelevantní/spam:
- přesun do `{WORK_ROOT}/intake/rejected/` a doplň důvod.

---

### 4) Regeneruj backlog index

Po zpracování všech intake items:
1. Scan `{WORK_ROOT}/backlog/*.md` (mimo `done/`)
2. Vytáhni frontmatter: id/title/type/status/tier/effort/prio
3. Vygeneruj `{WORK_ROOT}/backlog.md` tabulku
4. Seřaď:
   - primárně PRIO desc
   - sekundárně tier (T0 před T1…)

---

### 5) Intake report

Vytvoř `{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md`:

- processed_count
- created_backlog_items (id, type, tier, status)
- duplicates merged
- rejected items
- warnings (legacy format, missing fields)

---

## Fail conditions

Pokud se nepodaří vytvořit backlog item nebo je schema nekonzistentní:
- vytvoř intake item `intake/intake-failed-{date}.md` s detailním důvodem
- neztrácej data (intake nech v place)
- reportuj CRITICAL v intake reportu

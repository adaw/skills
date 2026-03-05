---
name: fabric-intake
description: "Triage intake items into normalized backlog items (Epic/Story/Task/Bug/Chore/Spike). Creates/updates {WORK_ROOT}/backlog/*.md using canonical templates, regenerates {WORK_ROOT}/backlog.md index, and moves processed intake files to intake/done or intake/rejected (never deletes)."
---

# INTAKE — Triage (intake → backlog)

## Účel

Zpracovat surové vstupy v `{WORK_ROOT}/intake/` a převést je do standardizovaných backlog položek.

## OWNERSHIP — Backlog index

**Odpovědnost:** `fabric-intake`, `fabric-prio` a `fabric-close` MUSÍ spolupracovat na údržbě centrálního backlog indexu (`{WORK_ROOT}/backlog.md`):
- `fabric-intake` → regeneruje index po triažích
- `fabric-prio` → regeneruje po prioritizaci
- `fabric-close` → regeneruje po uzavření sprintu

**Invariant:** Index je vždy aktuální s jednotlivými backlog soubory v `{WORK_ROOT}/backlog/{id}.md` (asynchronní update je povolený, ale konsistence se musí ověřit v auditu).

---

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
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (pro přiřazení intake/backlog položek k vizi; povinné pro T0/T1)

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
6. Každý backlog item musí mít `linked_vision_goal`:
   - pokud jde přiřadit → vyplň (nejlépe přesný název pilíře/goal z vize)
   - pokud nejde přiřadit → nech prázdné, ale:
     - nastav `status: IDEA`
     - a nedovol Tier vyšší než T2 (aby se „mimo vizi“ práce nedostala do top queue)
   - pro T0/T1 je prázdné `linked_vision_goal` vždy WARNING a musí vzniknout „Open question“ / následný intake k doplnění vize

---


## FAST PATH (povinné) — scan → plan → apply (bez ručních přesunů/editací)

> **FAST PATH je primární postup.** Používej ho vždy. Sekce „Postup" níže slouží jako **reference pro rozhodovací logiku** (triage rules, vision alignment, dedup) — ne jako alternativní flow. FAST PATH volá stejnou logiku deterministicky přes tooling.

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
      linked_vision_goal: "<goal-or-empty>"
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

### 2) Najdi „pending” intake soubory

Zpracuj pouze:
- `{WORK_ROOT}/intake/*.md`
- ignoruj `{WORK_ROOT}/intake/done/` a `{WORK_ROOT}/intake/rejected/`

**Symlink validation guard (P2 fix):** Reject symlinked intake files to prevent indirect manipulation and ensure auditability.
```bash
# Symlink guard (P2 fix): reject symlinked intake files
for INTAKE_FILE in {WORK_ROOT}/intake/*.md; do
  if [ -L “$INTAKE_FILE” ]; then
    echo “WARN: skipping symlink: $INTAKE_FILE”
    mv “$INTAKE_FILE” “{WORK_ROOT}/intake/rejected/” 2>/dev/null || true
    continue
  fi
done
```

Pokud nejsou žádné pending intake items (bez symlinků):
- vytvoř report `reports/intake-{date}.md` s „0 items processed”
- DONE (vrať se orchestrátoru)

> **Clarifikace pro fabric-loop:** Intake vrací „0 items” jako normální výsledek, NE jako chybový stav. Orchestrátor pokračuje na další step (prio). Intake NENÍ loop boundary — i s 0 items lifecycle pokračuje dál.

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

Před vytvořením backlog itemu proveď **deterministickou** dedup kontrolu:

```bash
# Deterministická dedup: normalizuj title → slug → hledej existující soubor
NORMALIZED_TITLE=$(echo "{new_title}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
EXISTING=$(grep -rl "^title:.*${NORMALIZED_TITLE}" "{WORK_ROOT}/backlog/"*.md 2>/dev/null | head -1)
if [ -n "$EXISTING" ]; then
  echo "DEDUP: found existing backlog item: $EXISTING"
fi
```

- pokud existuje shoda (normalizovaný title match):
  - přidej do existujícího backlog itemu sekci `## Intake references` s odkazem na intake file
  - intake přesun do `intake/done/` (důvod: merged/duplicate)
  - pokračuj dalším intake

**Anti-patterns:**
- ❌ Nepoužívej fuzzy/LLM matching pro dedup — výsledky nejsou reprodukovatelné
- ❌ Nepřeskakuj dedup krok "protože to vypadá unikátně"

#### 3.3 Vision alignment (povinné)

Z `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md`:

- najdi nejbližší relevantní pilíř/goal/principle pro tento intake item
- nastav `linked_vision_goal`:
  - pokud už je ve frontmatter a odpovídá pojmům z vize → ponech
  - pokud chybí → doplň (krátký string; ideálně přesný název pilíře/goal)
  - pokud je zjevně mimo vizi → ponech prázdné a přidej do backlog itemu „Open questions: proč to děláme / patří to do vize?”

**Stale vision reference guard (P2 fix):** Validate that vision goal references are still present in the current vision.md.
```bash
# Stale vision reference guard (P2 fix)
if [ -n “${linked_vision_goal}” ]; then
  if ! grep -qi “${linked_vision_goal}” “{WORK_ROOT}/vision.md” 2>/dev/null; then
    echo “WARN: linked_vision_goal '${linked_vision_goal}' not found in current vision.md — may be stale”
  fi
fi
```
This check runs after vision goal assignment to detect references that may have become invalid due to vision.md updates.

**Non-goals gate:** pokud intake jasně porušuje `Non-goals` z vize → NEVYTVÁŘEJ backlog item. Přesuň intake do `intake/rejected/` a doplň důvod (cituj non-goal).

Pokud `linked_vision_goal` zůstane prázdné:
- nastav `status: IDEA`
- tier clamp: max `T2` (i kdyby raw_priority ukazovalo výš)

**T0/T1 early gate:** Pokud by tier vyšel T0 nebo T1 ale `linked_vision_goal` je prázdné:
- **NEVYTVÁŘEJ** backlog item s T0/T1 bez vision link
- Vytvoř intake item `intake/intake-t0t1-missing-vision-{id}.md` s požadavkem na doplnění vision alignment
- Původní intake přesuň do `intake/done/` s poznámkou „blocked: requires vision alignment for T0/T1"
- Tím se zabrání, aby se high-priority práce mimo vizi dostala do sprint queue

#### 3.4 Urči Type

Primárně použij `initial_type`. Pokud chybí, inferuj:
- pokud popis obsahuje „bug“, „crash“, „fails“ → Bug
- pokud jde o „refactor/tooling/docs“ → Chore
- pokud jde o „research/unknown“ → Spike
- jinak Task (default)

#### 3.5 Urči Tier (T0–T3)

Použij jednoduchou heuristiku:
- raw_priority 9–10 → T0
- 6–8 → T1
- 3–5 → T2
- 1–2 → T3

Pokud `linked_vision_goal` je kritické (výslovně označené ve vision) → posuň o 1 tier výš (max T0).

#### 3.6 Urči Status (IDEA / DESIGN / READY)

- `READY`, pokud intake už obsahuje:
  - konkrétní doporučenou akci (co změnit) + hrubý test plan / evidence
- jinak `DESIGN`, pokud je zřejmý scope, ale chybí detail (bude doplněno v analyze)
- jinak `IDEA`, pokud je to jen nápad bez detailů

Effort nastav `TBD` (pokud si nejsi jistý), jinak XS/S/M/L.

#### 3.7 Vygeneruj backlog ID (deterministicky)

Pravidlo:
- prefix podle typu: `epic-`, `story-`, `task-`, `bug-`, `chore-`, `spike-`
- slug z title: lowercase + hyphen
- pokud soubor už existuje → suffix `-2`, `-3`, ...

Příklad:
- „Add auth middleware” → `task-add-auth-middleware`

#### 3.8 Vytvoř backlog item soubor

Collision guard (P1 fix):
```bash
TARGET_FILE=”{WORK_ROOT}/backlog/{id}.md”
if [ -f “$TARGET_FILE” ]; then
  echo “WARN: backlog file $TARGET_FILE already exists — checking if duplicate”
  EXISTING_TITLE=$(grep '^title:' “$TARGET_FILE” | head -1 | sed 's/title: *//')
  if [ “$EXISTING_TITLE” != “{new_title}” ]; then
    echo “COLLISION: different title, appending suffix”
    # Append -N suffix until unique
    N=2
    while [ -f “{WORK_ROOT}/backlog/{id}-${N}.md” ]; do N=$((N+1)); done
    id=”{id}-${N}”
    TARGET_FILE=”{WORK_ROOT}/backlog/{id}.md”
  else
    echo “SKIP: duplicate intake for existing backlog item (dedup)”
    # Move intake to done/ with reason: duplicate
    continue
  fi
fi
```

Vytvoř backlog item soubor

Vytvoř `{WORK_ROOT}/backlog/{id}.md` podle odpovídající šablony:
- Epic → `{WORK_ROOT}/templates/epic.md`
- Story → `{WORK_ROOT}/templates/story.md`
- Task/Bug/Chore/Spike → `{WORK_ROOT}/templates/task.md` (změň `type:`)

Vyplň minimálně:
- `id`, `title`, `type`, `tier`, `status`, `effort`, `created`, `updated`, `source: intake`, `prio: 0`, `linked_vision_goal`
- do těla vlož:
  - „Příkaz odemykující“ (1 věta)
  - popis + kontext z intake
  - Acceptance Criteria (aspoň 3 checkboxy; když nevíš, formuluj hypotézy)
  - „Open questions“ pokud status není READY
  - odkaz na intake (provenance)

#### 3.9 Přesuň intake do done/rejected

Standardně: přesun do `{WORK_ROOT}/intake/done/`.

Pouze pokud je intake úplně nerelevantní/spam:
- přesun do `{WORK_ROOT}/intake/rejected/` a doplň důvod.

---

### 4) Regeneruj backlog index

Po zpracování všech intake items:

> **OWNERSHIP:** Backlog index (`backlog.md`) regeneraci provádí VÝHRADNĚ `fabric.py backlog-index` (deterministický, idempotentní). Nikdy neregeneruj backlog.md ručně — vždy volej:
> ```bash
> python skills/fabric-init/tools/fabric.py backlog-index
> ```
> Toto zajišťuje atomicitu a konzistenci i když více skills volá regeneraci.

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

### Idempotence a recovery

**Re-run je bezpečný.** Zpracování je idempotentní díky move semantice:
- Zpracované intake soubory se přesouvají do `intake/done/`. Při re-run jsou v `intake/` jen nezpracované.
- Pokud backlog item pro daný intake už existuje (shodné `id`) → přeskoč (dedup, nezakládej duplicitní).
- Pokud `backlog.md` regenerace selže → backlog items v `backlog/*.md` jsou zdrojem pravdy, `backlog.md` lze kdykoli přegenerovat.
- Pokud move do `done/` selže → intake soubor zůstává v `intake/` a bude zpracován při dalším run.

---

## Self-check

> **Naming clarifikace:** Intake **items** (soubory v `intake/`) pojmenovávej dle config konvence `{source}-{slug}-{date-or-id}.md`. Intake **report** (výstup skillu) je `reports/intake-{YYYY-MM-DD}.md`. Nezaměňuj.

Před návratem:
- žádné nezpracované soubory v `intake/` (vše přesunuto do `intake/done/` nebo ponecháno s vysvětlením)
- pro každý zpracovaný intake existuje odpovídající backlog item v `backlog/`
- `backlog.md` regenerován a odpovídá obsahu `backlog/*.md`
- intake report existuje v `{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md`
- duplicity rozpoznány (neztraceny, sloučeny nebo zamítnuty s důvodem)

Pokud ne → FAIL + vytvoř intake item `intake/intake-selfcheck-failed-{date}.md`.

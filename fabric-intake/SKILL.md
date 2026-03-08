---
name: fabric-intake
description: "Triage intake items into normalized backlog items (Epic/Story/Task/Bug/Chore/Spike). Creates/updates {WORK_ROOT}/backlog/*.md using canonical templates, regenerates {WORK_ROOT}/backlog.md index, and moves processed intake files to intake/done or intake/rejected (never deletes)."
---
<!-- built from: builder-template -->

# INTAKE — Triage (intake → backlog)

Zpracovat surové vstupy v `{WORK_ROOT}/intake/` a převést je do standardizovaných backlog položek.

---

## K2 Fix: Intake Processing with Counter

```bash
MAX_INTAKE=${MAX_INTAKE:-100}
COUNTER_FILE="{WORK_ROOT}/.intake-counter"
# Persist counter to disk for idempotence across re-runs
if [ -f "$COUNTER_FILE" ]; then
  INTAKE_COUNTER=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
  # Validate numeric
  echo "$INTAKE_COUNTER" | grep -qE '^[0-9]+$' || INTAKE_COUNTER=0
else
  INTAKE_COUNTER=0
fi
```

---

## §1 — Účel

**Primary Goal:** Zpracovat surové vstupy v `{WORK_ROOT}/intake/` a převést je do standardizovaných backlog položek (Epic/Story/Task/Bug/Chore/Spike).

**Why It Matters:** Bez systematické triáže se surové požadavky hromadí bez struktury, priority ani napojení na vizi. Intake zajišťuje, že každý požadavek projde deduplikací, vision alignment a standardizovaným formátem, než se dostane do backlogu.

**Scope:** Všechny soubory v `{WORK_ROOT}/intake/*.md`. Výstupem jsou backlog items, regenerovaný index, a intake report.

**Variants:**
- **default**: Full triage + backlog creation + index regeneration
- **zero items**: Pokud žádné intake items → report "0 items processed", DONE (ne error)

---

## OWNERSHIP — Backlog index

**Odpovědnost:** `fabric-intake`, `fabric-prio` a `fabric-close` MUSÍ spolupracovat na údržbě centrálního backlog indexu (`{WORK_ROOT}/backlog.md`):
- `fabric-intake` → regeneruje index po triážích
- `fabric-prio` → regeneruje po prioritizaci
- `fabric-close` → regeneruje po uzavření sprintu

**Invariant:** Index je vždy aktuální s jednotlivými backlog soubory v `{WORK_ROOT}/backlog/{id}.md` (asynchronní update je povolený, ale konsistence se musí ověřit v auditu).

---

## §2 — Protokol (povinné — NEKRÁTIT)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

```bash
# START
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-intake" \
  --event start

# END (po úspěchu)
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-intake" \
  --event end \
  --status OK \
  --report "{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md"

# ERROR (při selhání)
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-intake" \
  --event error \
  --status ERROR \
  --message "<1 věta popisující důvod selhání>"
```

Výsledek musí být:
- konzistentní s config taxonomií,
- deduplikovaný,
- připravený na prioritizaci (`fabric-prio`),
- a auditovatelný (processed intake se **přesouvá**, nemaže).

---

## §3 — Preconditions (temporální kauzalita)

```bash
# K7: Path traversal guard
for VAR in "{WORK_ROOT}" "{CODE_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in $VAR"
    exit 1
  fi
done

# --- Precondition 1: Config existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: State existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 3: Intake directory existuje ---
if [ ! -d "{WORK_ROOT}/intake" ]; then
  echo "STOP: {WORK_ROOT}/intake directory not found — run fabric-init first"
  exit 1
fi

# --- Precondition 4: Templates existují ---
if [ ! -d "{WORK_ROOT}/templates" ]; then
  echo "STOP: {WORK_ROOT}/templates directory not found"
  exit 1
fi

# --- Precondition 5: Vision existuje (for alignment check) ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "WARN: {WORK_ROOT}/vision.md not found — intake items cannot be aligned to vision"
fi

# --- State validation (K1: State Machine) ---
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-intake. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

**Dependency chain:** `fabric-init` → [fabric-intake] → `fabric-prio`

When processing intake items, enforce counter:
```bash
for intake_file in {WORK_ROOT}/intake/*.md; do
  [ -f "$intake_file" ] || continue
  # Idempotence: skip already-processed files (check done/ directory)
  BASENAME=$(basename "$intake_file")
  if [ -f "{WORK_ROOT}/intake/done/$BASENAME" ] || [ -f "{WORK_ROOT}/intake/rejected/$BASENAME" ]; then
    continue
  fi
  INTAKE_COUNTER=$((INTAKE_COUNTER + 1))
  echo "$INTAKE_COUNTER" > "$COUNTER_FILE"
  if [ "$INTAKE_COUNTER" -ge "$MAX_INTAKE" ]; then
    echo "WARN: max intake items reached ($INTAKE_COUNTER/$MAX_INTAKE)"
    break
  fi
  # ... triage and process intake item
done
```

---

## §4 — Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/intake/*.md` (kanonicky podle `{WORK_ROOT}/templates/intake.md`)
- `{WORK_ROOT}/backlog/*.md` (kvůli deduplikaci)
- `{WORK_ROOT}/templates/*.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (pro přiřazení intake/backlog položek k vizi; povinné pro T0/T1)

---

## §5 — Výstupy

- nové nebo aktualizované backlog items: `{WORK_ROOT}/backlog/{id}.md`
- regenerovaný index: `{WORK_ROOT}/backlog.md`
- intake report: `{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md`
- přesunuté intake soubory:
  - `{WORK_ROOT}/intake/done/`
  - `{WORK_ROOT}/intake/rejected/`

---

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

---

## §6 — Deterministic FAST PATH

> **FAST PATH je primární postup.** Používej ho vždy. Sekce „§7 Postup" níže slouží jako **reference pro rozhodovací logiku** (triage rules, vision alignment, dedup) — ne jako alternativní flow. FAST PATH volá stejnou logiku deterministicky přes tooling.

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

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

# K5: Intake thresholds from config.md
MAX_INTAKE_ITEMS=$(grep 'INTAKE.max_items:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MAX_INTAKE_ITEMS=${MAX_INTAKE_ITEMS:-200}
if ! echo "$MAX_INTAKE_ITEMS" | grep -qE '^[0-9]+$'; then
  MAX_INTAKE_ITEMS=200
  echo "WARN: MAX_INTAKE_ITEMS not numeric, reset to default (200)"
fi
```

> **Detailní triage pravidla a workflow:** Přečti `references/workflow.md` pomocí Read toolu.
> Obsahuje: path traversal guard, symlink validaci, dedup logiku, vision alignment,
> type/tier/status heuristiky, backlog ID generaci, collision guard, kanonická pravidla.

> **Příklady s reálnými LLMem daty (K10):** Přečti `references/examples.md` pomocí Read toolu.

Stručný přehled kroků:

1. **Načti config a připrav prostředí** — ověř runtime strukturu
2. **Najdi pending intake soubory** — filtruj done/, rejected/, symlinky
3. **Pro každý intake item proveď triage:**
   - 3.1 Parse intake YAML (s legacy fallback)
   - 3.2 Deduplikace (deterministická, slug-based)
   - 3.3 Vision alignment (povinné; T0/T1 early gate)
   - 3.4 Urči Type (Bug/Task/Chore/Spike/Story/Epic)
   - 3.5 Urči Tier (T0–T3 z raw_priority + vision boost)
   - 3.6 Urči Status (IDEA/DESIGN/READY)
   - 3.7 Vygeneruj backlog ID (deterministicky: prefix-slug)
   - 3.8 Vytvoř backlog item ze šablony (collision guard)
   - 3.9 Přesuň intake do done/rejected
4. **Regeneruj backlog index** — přes `fabric.py backlog-index`
5. **Vytvoř intake report** — processed/created/merged/rejected/warnings

### K10: Inline Example — LLMem Intake Triage

**Input:**
Raw intake item: `intake/raw-batch-endpoint.md`
```
title: "add batch endpoint"
type: feature
priority: high
description: "APIs should support /capture/batch"
```

**Output:**
```
Triage result:
Deduplicated: NO (new item)
Vision alignment: HIGH (links to "Capture scalability" goal)
Normalized: backlog/b051.md
---
title: "Add /capture/batch endpoint"
type: Task
tier: T1
status: READY
prio: 18
effort: M
linked_vision_goal: capture-scalability
```

### K10: Anti-patterns (s detekcí)
```bash
# A1: Accepting Intake Without Dedup Check
# Detection: diff <(cut -d: -f2 intake/raw-*.md) <(cut -d: -f2 backlog/*.md) | grep "<"
# Fix: Run dedup first; skip if title slug matches existing backlog item

# A2: Missing Vision Link on T0/T1
# Detection: grep "tier: T[01]" backlog/*.md | grep -v "linked_vision_goal:"
# Fix: Query vision.md for relevant goal; add linked_vision_goal field

# A3: Invalid Type
# Detection: grep "^type:" backlog/*.md | grep -v "Epic\|Story\|Task\|Bug\|Chore\|Spike"
# Fix: Map to valid type enum; default to Task if ambiguous
```

---

## §8 — Quality Gates

| Gate | Kritérium | Automatizace |
|------|-----------|-------------|
| QG1 | Všechny intake items zpracovány (žádné v `intake/` po skončení) | `ls {WORK_ROOT}/intake/*.md 2>/dev/null \| wc -l` == 0 |
| QG2 | Každý nový backlog item má validní YAML frontmatter | `python skills/fabric-init/tools/fabric.py validate-backlog` |
| QG3 | Backlog index odpovídá `backlog/*.md` | `python skills/fabric-init/tools/fabric.py backlog-index --check` |
| QG4 | Report existuje a má schema `fabric.report.v1` | grep check v report souboru |
| QG5 | Protocol log má START a END | grep check v protocol_log |
| QG6 | Žádný T0/T1 backlog item bez `linked_vision_goal` | frontmatter check |

---

## §9 — Report

Intake report `{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md`:

```markdown
---
schema: fabric.report.v1
kind: intake
created_at: "{YYYY-MM-DD}"
processed_count: N
created_count: N
merged_count: N
rejected_count: N
warnings_count: N
---

# Intake Report — {YYYY-MM-DD}

## Summary

Zpracováno N intake items. Vytvořeno N backlog items, N merged, N rejected.

## Processing

| # | Intake file | Action | Backlog ID | Type | Tier | Status |
|---|-------------|--------|------------|------|------|--------|
| 1 | ... | created | ... | ... | ... | ... |

## Dedup/Merges

| Intake file | Merged into | Reason |
|-------------|-------------|--------|

## Rejected

| Intake file | Reason |
|-------------|--------|

## Warnings

- ...
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

> **Naming clarifikace:** Intake **items** (soubory v `intake/`) pojmenovávej dle config konvence `{source}-{slug}-{date-or-id}.md`. Intake **report** (výstup skillu) je `reports/intake-{YYYY-MM-DD}.md`. Nezaměňuj.

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/intake-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Backlog index aktualizován: `{WORK_ROOT}/backlog.md` existuje a odpovídá `backlog/*.md`
- [ ] Protocol log má START a END záznam s `skill: intake`

### Quality checks
- [ ] **Všechny intake items zpracovány**: žádné nezpracované soubory v `intake/` (vše v `intake/done/` nebo vysvětleno v reportu)
- [ ] **Pro každý zpracovaný intake existuje backlog item** v `backlog/` s matching `id` a `title`
- [ ] **Duplicity odstraněny**: report obsahuje seznam duplikátů (neztraceny, sloučeny nebo zamítnuty s důvodem)
- [ ] **Report má sekce**: Summary (N itemů zpracováno), Processing, Dedup/Merges, Backlog updates, Warnings
- [ ] **Backlog.md je seřazený** dle PRIO (nebo config-specified ordering)

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/intake/`, `{WORK_ROOT}/backlog/`, `{WORK_ROOT}/reports/` nebyl modifikován
- [ ] State.md NENÍ modifikován (intake nesmí měnit phase/step)
- [ ] Žádný backlog item smazán (jen stav změněn)
- [ ] Protocol log má START i END záznam

Pokud ANY check FAIL → **FAIL + vytvoř intake item `intake/intake-selfcheck-failed-{date}.md`**.

---

## §11 — Failure Handling

| Stav | Akce |
|------|------|
| Config chybí | STOP — `fabric-init` musí běžet první |
| Intake dir chybí | STOP — `fabric-init` musí běžet první |
| Templates chybí | STOP — nelze vytvářet backlog items bez šablon |
| Vision chybí | WARN — pokračuj, ale nemůžeš alignovat na vizi |
| Backlog item se nepodaří vytvořit | Vytvoř intake `intake/intake-failed-{date}.md` s důvodem, neztrácej data |
| Schema nekonzistence | CRITICAL — reportuj v intake reportu, ponech intake v `intake/` |
| Move do done/ selže | WARN — intake zůstane v `intake/`, bude zpracován při dalším run |

**K3 escalation:** Template parsing failure (missing YAML frontmatter, corrupt file) → STOP + exit 1, ne WARN. WARN je jen pro minor validation issues (missing optional fields).

### Idempotence a recovery

**Re-run je bezpečný.** Zpracování je idempotentní díky move semantice:
- Zpracované intake soubory se přesouvají do `intake/done/`. Při re-run jsou v `intake/` jen nezpracované.
- Pokud backlog item pro daný intake už existuje (shodné `id`) → přeskoč (dedup, nezakládej duplicitní).
- Pokud `backlog.md` regenerace selže → backlog items v `backlog/*.md` jsou zdrojem pravdy, `backlog.md` lze kdykoli přegenerovat.
- Pokud move do `done/` selže → intake soubor zůstává v `intake/` a bude zpracován při dalším run.

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
depends_on: [fabric-init]
feeds_into: [fabric-prio]
phase: orientation
lifecycle_step: intake
touches_state: false
touches_git: false
estimated_ticks: 1
idempotent: true
fail_mode: fail-open  # 0 items je validní výsledek
```

### Downstream Contract

**Kdo konzumuje výstupy fabric-intake a jaká pole čte:**

- **fabric-prio** reads:
  - `{WORK_ROOT}/backlog/*.md` frontmatter: `id`, `tier`, `status`, `prio`, `effort`
  - `{WORK_ROOT}/backlog.md` index (regenerovaný intake)

- **fabric-loop** reads:
  - intake report: `processed_count` (pro work-status detekci)
  - protocol log: START/END (pro tick tracking)

- **fabric-sprint** reads:
  - `{WORK_ROOT}/backlog/*.md` s `status: READY` (intake je prerekvizita pro sprint planning)

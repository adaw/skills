---
name: fabric-prio
description: "Recalculate and normalize priority (PRIO) across all active backlog items. Uses a transparent scoring model, updates each item's frontmatter (prio + optionally effort if TBD), regenerates backlog.md sorted by PRIO, and writes a prio report with rationale and confidence."
---

# PRIO — Prioritizace backlogu

## Účel

Z backlogu udělat **seřazenou exekuční frontu**.
Výsledek musí být strojově čitelný:
- `prio:` je vyplněné ve všech aktivních backlog items,
- `{WORK_ROOT}/backlog.md` je seřazený podle PRIO,
- existuje report s vysvětlením.

## OWNERSHIP — Backlog index

**Odpovědnost:** `fabric-intake`, `fabric-prio` a `fabric-close` MUSÍ spolupracovat na údržbě centrálního backlog indexu (`{WORK_ROOT}/backlog.md`):
- `fabric-intake` → regeneruje index po triážích
- `fabric-prio` → regeneruje po prioritizaci (seřazuje podle PRIO, aktualizuje prio pole ve všech items)
- `fabric-close` → regeneruje po uzavření sprintu (DONE items, carry-over logika)

**Invariant:** Index je vždy aktuální s jednotlivými backlog soubory v `{WORK_ROOT}/backlog/{id}.md` (asynchronní update je povolený, ale konsistence se musí ověřit v auditu).

---

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-prio" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-prio" --event end --status OK --report "{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy

- `{WORK_ROOT}/config.md` (statusy, tier, WIP)
- `{WORK_ROOT}/backlog/*.md` (flat, mimo `done/`)
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (pro mapování hodnoty na vizi a sub-vize)
- `{WORK_ROOT}/backlog.md` (může být regenerováno)

---

## Výstupy

- aktualizované backlog items (frontmatter `prio:` a případně `effort:` pokud bylo `TBD`)
- regenerovaný `{WORK_ROOT}/backlog.md`
- report `{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md`

---

## Preconditions

```bash
# --- Precondition 1: Config existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: Backlog index existuje ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "STOP: {WORK_ROOT}/backlog.md not found — run fabric-intake first"
  exit 1
fi

# --- Precondition 3: Vision existuje (for impact scoring) ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "WARN: {WORK_ROOT}/vision.md not found — impact scoring will be limited"
fi

# --- Precondition 4: Backlog items directory exists ---
if [ ! -d "{WORK_ROOT}/backlog" ]; then
  echo "STOP: {WORK_ROOT}/backlog directory not found"
  exit 1
fi
```

**Dependency chain:** `fabric-intake` → [fabric-prio] → `fabric-sprint`

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

## Scoring model (transparentní)

Použij tento model:

```
PRIO = (Impact × 3) + (Urgency × 2) + (Readiness × 2) - (EffortScore × 1) - (Staleness × 1)
```

Staleness (volitelné, 0–5):
- Item v backlogu < 7 dní: 0
- 7–30 dní bez pohybu (unchanged `updated:`): 1
- 30–90 dní: 2
- 90–180 dní: 3
- \> 180 dní: 5 (a vytvoř intake item `intake/prio-stale-{id}.md` — zvážit archivaci nebo zrušení)

Škály:
- Impact: 0–10
- Urgency: 0–10
- Readiness: 0–10
- EffortScore: 0–10 (odvozeno z effort)

Mapování effort → EffortScore:
- XS=1, S=3, M=5, L=7, XL=9
- TBD: nejdřív odhadni effort (preferovaně), jinak použij M jako fallback a zapiš WARNING

> Výsledné PRIO normalizuj na integer (0–100). Důležitá je **relativní** škála.

### K10 Fix: Concrete Priority Calculation Examples

**Example 1: High-Priority Security Task**

Item: `task-b042-add-input-validation.md`
- Title: "Add Pydantic validation to /capture/event endpoint"
- Type: Bug
- Tier: T0
- Status: READY
- Effort: M (EffortScore=5)
- Blocked by: none
- Linked vision goal: "Reliability - Input validation"

Scoring:
- Impact = 8 (T0 = 8, + 1 security hotfix) = 9
- Urgency = 9 (T0 = 7, +2 DOS vulnerability blocker) = 9
- Readiness = 10 (READY status, AC complete)
- EffortScore = 5 (M = 5)
- Staleness = 0 (created this sprint)

PRIO = (9×3) + (9×2) + (10×2) - (5×1) - (0×1) = 27 + 18 + 20 - 5 = **60 (URGENT)**

**Example 2: Medium-Priority Refactoring**

Item: `task-b031-refactor-triage-service.md`
- Title: "Refactor triage service for better testability"
- Type: Task
- Tier: T2
- Status: DESIGN
- Effort: L (EffortScore=7)
- Linked vision goal: "Code Quality"

Scoring:
- Impact = 4 (T2 = 4) = 4
- Urgency = 3 (T2 = 3, not time-sensitive)
- Readiness = 5 (DESIGN status, incomplete AC)
- EffortScore = 7 (L = 7)
- Staleness = 1 (40 days since update, 7-30d range)

PRIO = (4×3) + (3×2) + (5×2) - (7×1) - (1×1) = 12 + 6 + 10 - 7 - 1 = **20 (MEDIUM)**

**Sorting algorithm (after all PRIOs calculated):**

1. Sort by PRIO descending
2. Secondary sort by Tier (T0 → T3)
3. Tertiary sort by Type (Bug/Security before Epic/Story for execution readiness)

Result: Top 20 items in backlog.md are highest-value executable work.

---


## FAST PATH (doporučeno) — scan → plan → apply (LLM rozhoduje, stroj patchuje)

1) Vyrob strojový snapshot backlogu:

```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

2) Spočítej PRIO (Impact/Urgency/Readiness/Effort/Staleness) **jen z dat** a vygeneruj plan soubor:

- napiš `{WORK_ROOT}/reports/prio-plan-{YYYY-MM-DD}.yaml` se schematem:

```yaml
schema: fabric.plan.v1
ops:
  - op: backlog.set
    id: "<backlog-id>"
    fields:
      prio: 0
      effort: "M"   # jen pokud bylo TBD a jsi si jistý
      updated: "{YYYY-MM-DD}"
  - op: backlog.index
```

3) Aplikuj plan deterministicky (žádné ruční editace frontmatter):

```bash
python skills/fabric-init/tools/fabric.py apply "{WORK_ROOT}/reports/prio-plan-{YYYY-MM-DD}.yaml"
```

To aktualizuje položky + regeneruje backlog index.

---

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-prio. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### Path Traversal Guard (K7: Input Validation)

```bash
# Path traversal guard — reject any input containing ".."
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic path inputs:
# validate_path "$BACKLOG_FILE"
# validate_path "$PRIO_REPORT"
```

### 1) Načti vizi (pro Impact)

Z `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` vytáhni:
- pillars, goals, success metrics (z core vize i sub-vizí)
- pokud backlog item explicitně odkazuje na goal/pillar (preferovaně přes `linked_vision_goal` ve frontmatter), zvyšuje to Impact

### 2) Načti backlog items

**K2 Fix: Backlog Item Iteration with Counter**

```bash
MAX_ITEMS=${MAX_ITEMS:-200}
ITEM_COUNTER=0
```

Projdi všechny soubory:
```bash
find {WORK_ROOT}/backlog -maxdepth 1 -type f -name "*.md" | while read backlog_file; do
  ITEM_COUNTER=$((ITEM_COUNTER + 1))
  if [ "$ITEM_COUNTER" -ge "$MAX_ITEMS" ]; then
    echo "WARN: max backlog items reached ($ITEM_COUNTER/$MAX_ITEMS)"
    break
  fi
  # ... process item
done
```

Pokud počet backlog itemů je velký (např. > 200), použij **dvoufázové skórování**, aby to škálovalo:

- **FAST pass (O(N))**: pro všechny itemy parsuj jen YAML frontmatter (nečti celé tělo) a spočítej „quick PRIO“ z `tier/status/type/effort/blocked_by/depends_on`.
- **DEEP pass (O(K))**: otevři celé tělo jen pro:
  - top `K=50` podle quick PRIO, a
  - itemy s chybějícím `prio` nebo `effort=TBD`.
  V DEEP pass můžeš upravit `Impact/Urgency/Readiness` podle AC, rizik, vazby na vizi.

Pravidlo: i ve FAST mode musí být výstup deterministický a všechny itemy dostanou `prio:` (nižší confidence pro FAST-only).

Ignoruj:
- `done/`
- `README*`

Pro každý item načti YAML:
- `id`, `title`, `type`, `tier`, `status`, `effort`, `prio` (stávající), `depends_on`, `blocked_by`, `linked_vision_goal`

Pokud chybí `title` nebo `type` → vytvoř intake item `intake/prio-schema-missing-{id}.md` a dej itemu PRIO=0 (dokud se neopraví).

### 3) Urči skóre faktorů

**Impact (0–10)**
- Tier baseline:
  - T0: 8
  - T1: 6
  - T2: 4
  - T3: 2
- Bug/Security hotfix může dostat +1 až +2
- Pokud item mapuje přímo na vision goal (např. `linked_vision_goal` není prázdné): +1

**Vision-fit gate (aby backlog neujížděl mimo směr):**
- Pokud `tier` je `T0` nebo `T1` a `linked_vision_goal` je prázdné → penalizuj Impact o `-3` (min 0) a vytvoř intake item:
  - `{WORK_ROOT}/intake/prio-missing-vision-link-{id}.md`
  - do něj napiš: „Doplňte/ověřte napojení backlog itemu na vizi (goal/pillar) nebo snižte tier/archivujte.“

**Urgency (0–10)**
- BLOCKED blocker pro T0 chain: 9–10
- časově citlivé (release/regrese): 8–10
- jinak:
  - T0: 7
  - T1: 5
  - T2: 3
  - T3: 1–2

**Readiness (0–10)**
- READY: 8–10
- DESIGN: 4–7
- IDEA: 1–3
- IN_PROGRESS/IN_REVIEW: drž vysoko (8), ale tyto itemy se typicky neplánují jako nové (WIP=1)

**Effort**
- Pokud `effort=TBD`: odhadni (XS–XL) na základě:
  - počet dotčených souborů (pokud uvedeno)
  - nová integrace vs drobná změna
  - riziko a nejasnost
- Pokud nedokážeš odhadnout: použij M a zapiš WARNING do reportu.

### 4) Spočítej PRIO a zapiš do itemu

Pro každý item:
- spočítej PRIO podle modelu
- zapiš `prio: <int>` do YAML frontmatter
- pokud jsi odhadoval effort z TBD → aktualizuj `effort:` a zapiš do reportu

> Neměň `status` (to řeší analyze/implement/review/close).

### 5) Regeneruj backlog.md

Vygeneruj `{WORK_ROOT}/backlog.md` jako tabulku:

| ID | Title | Type | Status | Tier | Effort | PRIO |

Seřaď:
1. PRIO desc
2. Tier (T0 → T3)
3. Type priority (Bug/Task před Epic/Story, aby byly exekuční věci nahoře)

### 6) Vytvoř prio report

`{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md` musí obsahovat:

- Top 20 itemů (tabulka) + jejich factor breakdown (Impact/Urgency/Readiness/EffortScore)
- Warnings:
  - effort odhad z TBD
  - items se schématem mimo kontrakt
  - items bez AC (readiness penalty)
  - T0/T1 items bez `linked_vision_goal` (vision-fit gate)
- Doporučení pro sprint planning (např. „vyber prvních 5 READY tasks“)

---

## Self-check

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Backlog index aktualizován: `{WORK_ROOT}/backlog.md` reflektuje nové prio
- [ ] Protocol log má START a END záznam s `skill: prio`

### Quality checks
- [ ] **Každý aktivní backlog item má `prio` integer** (1–100, bez duplicit na stejné úrovni)
- [ ] **Backlog.md je seřazený podle PRIO** (vzestupně nebo sestupně, konsistentně)
- [ ] **Report obsahuje**: Summary (N itemů reprioritizováno), Before/After tabulka, Justification per item, Warnings
- [ ] **Prio justifikace**: Každá velká změna (jump >20) má vysvětlení (risk/value/dependency)
- [ ] **Backlog item metadatas aktualizovány** v `backlog/*.md` frontmatter: `prio: N`

### Invariants
- [ ] Žádný backlog item smazán nebo duplikován (jen prio změněn)
- [ ] State.md NENÍ modifikován (prio nesmí měnit phase/step)
- [ ] Config.md NENÍ modifikován
- [ ] Protocol log má START i END záznam

Pokud ANY check FAIL → **FAIL + vytvoř intake item `intake/prio-failed-{date}.md`** (CRITICAL v reportu).

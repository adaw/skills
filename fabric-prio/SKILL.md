---
name: fabric-prio
description: "Recalculate and normalize priority across all active backlog items using transparent scoring. Updates frontmatter, regenerates sorted backlog.md, and produces report with rationale. Prevents chaotic backlog and enables objective sprint planning."
---

<!-- built from: builder-template -->

# PRIO — Prioritizace backlogu

---

## §1 — Účel

Z backlogu udělat **seřazenou exekuční frontu**.
Výsledek musí být strojově čitelný:
- `prio:` je vyplněné ve všech aktivních backlog items,
- `{WORK_ROOT}/backlog.md` je seřazený podle PRIO,
- existuje report s vysvětlením.

Bez PRIO skill backlog zůstane chaoticky seřazený a sprint planning bude hádání. S PRIO má tým objektivní podklady pro rozhodování.

---

## §2 — Protokol (povinné — NEKRÁTIT)

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "prio" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "prio" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "prio" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

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

# --- Precondition 5: State validation ---
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "orientation" ]; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-prio"
  exit 1
fi
```

**Dependency chain:** `fabric-intake` → [fabric-prio] → `fabric-sprint`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (statusy, tier, WIP)
- `{WORK_ROOT}/backlog.md` (index, může být regenerován)
- `{WORK_ROOT}/backlog/*.md` (flat, mimo `done/`)
- `{WORK_ROOT}/state.md` (phase validation)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (mapování hodnoty na vizi)

---

## §5 — Výstupy

### Primární (vždy)
- Aktualizované backlog items (frontmatter `prio:` a případně `effort:` pokud bylo `TBD`)
- Regenerovaný `{WORK_ROOT}/backlog.md` (tabulka seřazená podle PRIO)
- Report: `{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/prio-*.md` (schénata chyby, stálost, chybějící vision link)

---

## §6 — Deterministic FAST PATH

Než začneš analyzovat / hodnotit, proveď deterministické kroky:

```bash
# 1. Path validation — reject any input containing ".."
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# 2. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 3. Backlog scan (json snapshot)
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

---

## §7 — Postup (JÁDRO SKILLU)

### 7.1) Načti vizi (pro Impact scoring)

**Co:** Z `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` vytáhni pillars, goals, success metrics. Backlog item, který explicitně odkazuje na goal/pillar (přes `linked_vision_goal`), dostane bonus v Impact.

**Jak (detailní instrukce):**
1. Parsuj `vision.md` do hierarchie: pillar → goal → metric
2. Pro každý backlog item kontroluj `linked_vision_goal` frontmatter
3. Je-li vyplněno a existuje v vizi → Impact +1 bonus
4. Je-li prázdné u T0/T1 → penalizuj Impact o -3 (min 0) a vytvoř intake item

**Minimum:** Vision goals načteny, bonus/penalty správně aplikován.

**Anti-patterns:**
- Neignoruй chybějící vision.md (pokračuj s WARN, ne FAIL)
- Neaplikuj vision bonus za běžné backlog itemy (jen explicitní linked_vision_goal)

### 7.2) Načti a parsuj backlog items

**Co:** Projdi všechny soubory v `{WORK_ROOT}/backlog/` (mimo `done/`, mimo README), extrahuj frontmatter YAML.

**Jak (detailní instrukce):**
```bash
MAX_ITEMS=${MAX_ITEMS:-200}
ITEM_COUNTER=0
find {WORK_ROOT}/backlog -maxdepth 1 -type f -name "*.md" | while read backlog_file; do
  ITEM_COUNTER=$((ITEM_COUNTER + 1))
  if [ "$ITEM_COUNTER" -ge "$MAX_ITEMS" ]; then
    echo "WARN: max backlog items reached ($ITEM_COUNTER/$MAX_ITEMS)"
    break
  fi
  # Parsuj: id, title, type, tier, status, effort, prio, depends_on, blocked_by, linked_vision_goal
done
```

Je-li počet backlog itemů > 200, použij **dvoufázové skórování**:
- **FAST pass (O(N)):** parsuj jen YAML frontmatter, spočítej „quick PRIO"
- **DEEP pass (O(K)):** otevři celé tělo jen pro top 50 a items s chybějícím `prio` nebo `effort=TBD`

**Minimum:** Všechny itemy parsovány, chybějící `title` nebo `type` → intake item `prio-schema-missing-{id}.md`, item dostane PRIO=0.

**Anti-patterns:**
- Neignoruй itemy bez schématu (vytvoř intake item)
- Neprocházej `done/` nebo `README*`

### 7.3) Urči skóre faktorů (Impact, Urgency, Readiness, EffortScore)

**Co:** Spočítej čtyři faktory pro každý item podle přehledných tabulek.

**Jak (detailní instrukce):**

**Impact (0–10):**
- Tier baseline: T0=8, T1=6, T2=4, T3=2
- Bug/Security hotfix: +1 až +2
- Item mapuje přímo na vision goal: +1

**Urgency (0–10):**
- BLOCKED blocker pro T0 chain: 9–10
- Časově citlivé (release/regrese): 8–10
- Jinak: T0=7, T1=5, T2=3, T3=1–2

**Readiness (0–10):**
- READY: 8–10
- DESIGN: 4–7
- IDEA: 1–3
- IN_PROGRESS/IN_REVIEW: 8 (ale WIP=1, neplánují se jako nové)

**Effort → EffortScore:**
- XS=1, S=3, M=5, L=7, XL=9
- TBD: odhadni (preferovaně), jinak M + WARNING do reportu

**Vision-fit gate:** T0/T1 bez `linked_vision_goal` → penalizuj Impact -3 (min 0) a vytvoř intake item `prio-missing-vision-link-{id}.md`.

**Minimum:** Čtyři faktory spočítány, viditelné v tabulce Top 20 v reportu.

### 7.4) Spočítej PRIO a zapiš do item frontmatter

**Co:** Aplikuj transparentní model: `PRIO = (Impact × 3) + (Urgency × 2) + (Readiness × 2) - (EffortScore × 1) - (Staleness × 1)`.

**Jak:**
```bash
# Pro každý item:
PRIO=$((($IMPACT * 3) + ($URGENCY * 2) + ($READINESS * 2) - ($EFFORT_SCORE * 1) - ($STALENESS * 1)))

# Normalizuj na 0–100 (relativní škála je důležitá)
PRIO_NORM=$(($PRIO * 100 / 100))  # nebo use fabric.py apply

# Zapiš do frontmatter: prio: <int>
```

**Staleness (0–5):**
- < 7 dní: 0
- 7–30 dní bez pohybu: 1
- 30–90 dní: 2
- 90–180 dní: 3
- \> 180 dní: 5 + intake item `prio-stale-{id}.md`

**Monotonicity guard:** `updated:` field NESMÍ jít zpět. Pokud nový `updated` < stávající, drž starou hodnotu.

**Minimum:** Všechny itemy mají `prio:` integer (1–100).

**Anti-patterns:**
- Neměň `status` (to řeší analyze/implement/review/close)
- Nepoužívej magic čísla (vždy viditel model)

### 7.5) Spočítej konkrétní příklady (K10 Fix)

**Příklad 1: High-Priority Security Task**
```
Item: task-b042-add-input-validation.md
Impact = 9 (T0=8 + 1 security) | Urgency = 9 (T0=7 + 2 DOS) | Readiness = 10 | EffortScore = 5 (M) | Staleness = 0
PRIO = (9×3) + (9×2) + (10×2) - (5×1) - (0×1) = 27 + 18 + 20 - 5 = 60 (URGENT)
```

**Příklad 2: Medium-Priority Refactoring**
```
Item: task-b031-refactor-triage-service.md
Impact = 4 (T2) | Urgency = 3 (T2, not urgent) | Readiness = 5 (DESIGN) | EffortScore = 7 (L) | Staleness = 1 (40 days)
PRIO = (4×3) + (3×2) + (5×2) - (7×1) - (1×1) = 12 + 6 + 10 - 7 - 1 = 20 (MEDIUM)
```

### 7.6) Regeneruj backlog.md

**Co:** Vytvoř tabulku v `{WORK_ROOT}/backlog.md` s všemi itemy, seřazenou podle PRIO.

**Jak:**
```
| ID | Title | Type | Status | Tier | Effort | PRIO |
|----|-------|------|--------|------|--------|------|
```

Pořadí:
1. PRIO desc
2. Tier (T0 → T3)
3. Type priority (Bug/Task před Epic/Story)

**Minimum:** Tabulka existuje, seřazena podle PRIO, reflektuje aktuální frontmatter.

### 7.7) Vytvoř prio report

**Co:** Report `{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md` s analýzou.

**Jak:**
- Top 20 itemů (tabulka) + factor breakdown (Impact/Urgency/Readiness/EffortScore/Staleness)
- Warnings: effort odhad z TBD, schématické chyby, items bez AC, T0/T1 bez vision link
- Doporučení pro sprint planning

**Šablona:**
```md
---
schema: fabric.report.v1
kind: prio
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# prio — Report {YYYY-MM-DD}

## Souhrn
Reprioritizovány N itemů, top 20 hotovy pro sprint planning. Warnings: M, Stale items: K.

## Top 20 podle PRIO
| ID | Title | PRIO | Impact | Urgency | Readiness | EffortScore |
|...

## Warnings
- Effort TBD estimates: ...
- Missing schema: ...
- T0/T1 without vision link: ...
- Stale items (>180d): ...

## Recommendations
- Vyber prvních 5 READY tasks pro sprint
- Zvážit archivaci stálých itemů
```

**Minimum:** Report existuje, má povinné sekce (Souhrn, Top 20, Warnings), YAML frontmatter s schematem.

---

## §8 — Quality Gates

### Gate 1: Backlog file existence
```bash
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "FAIL: backlog.md was not regenerated"
  # → intake item
  exit 1
fi
```

### Gate 2: Report existence & schema
```bash
REPORT="{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md"
if [ ! -f "$REPORT" ]; then
  echo "FAIL: report not created"
  exit 1
fi

if ! grep -q "^schema: fabric.report.v1" "$REPORT"; then
  echo "FAIL: report missing schema frontmatter"
  exit 1
fi
```

### Gate 3: All active items have prio
```bash
MISSING_PRIO=$(find "{WORK_ROOT}/backlog" -maxdepth 1 -name "*.md" -exec grep -L '^prio:' {} \;)
if [ -n "$MISSING_PRIO" ]; then
  echo "FAIL: items missing prio:"
  echo "$MISSING_PRIO"
  exit 1
fi
```

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md` s schematem:

```md
---
schema: fabric.report.v1
kind: prio
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# prio — Report {YYYY-MM-DD}

## Souhrn
{1–3 věty co skill udělal: N itemů reprioritizováno, backlog.md regenerován, top 20 hotovy}

## Top 20 podle PRIO (s factor breakdown)
| ID | Title | PRIO | Impact | Urgency | Readiness | EffortScore | Staleness |
|...

## Warnings & Intake Items
- Effort estimates from TBD: {list}
- Missing schema (items set to PRIO=0): {list}
- T0/T1 without vision link: {list}
- Stale items (>180d): {list}

## Recommendations
- Doporučení pro sprint planning
- Archivace / rework guidance
```

---

## §10 — Self-check (povinný)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/prio-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Backlog index aktualizován: `{WORK_ROOT}/backlog.md` reflektuje nové prio
- [ ] Protocol log má START a END záznam s `skill: prio`

### Quality checks
- [ ] **Každý aktivní backlog item má `prio` integer** (1–100)
- [ ] **Backlog.md je seřazený podle PRIO** (sestupně, konsistentně)
- [ ] **Report obsahuje**: Souhrn, Top 20 tabulka, Warnings, Doporučení
- [ ] **Prio justifikace**: Velké změny (jump >20) mají vysvětlení
- [ ] **Backlog item metadatas aktualizovány** v `backlog/*.md` frontmatter: `prio: N`

### Invarianty
- [ ] Žádný backlog item smazán nebo duplikován (jen prio změněn)
- [ ] State.md NENÍ modifikován (prio nesmí měnit phase/step)
- [ ] Config.md NENÍ modifikován
- [ ] Protocol log má START i END záznam

Pokud ANY check FAIL → **report FAIL + vytvoř intake item `prio-failed-{date}.md`**.

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí backlog.md | STOP + protokol error log + jasná zpráva |
| FAST PATH | fabric.py selže | WARN + pokračuj manuálně |
| Postup (§7) | Nelze spočítat PRIO | STOP + protocol error log + intake item |
| Quality Gate | Gate FAIL | Report FAIL + intake item |
| Self-check | Check FAIL | Report WARN + intake item |

**Obecné pravidlo:** Skill je fail-open vůči VOLITELNÝM vstupům (vision.md chybí → pokračuj s WARNING) a fail-fast vůči POVINNÝM vstupům (backlog.md chybí → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: orientation
step: prio

# Oprávnění
may_modify_state: false
may_modify_backlog: true     # fabric-prio aktualizuje prio ve všech items
may_modify_code: false
may_create_intake: true      # pro schema errors, vision links, stale items

# Pořadí v pipeline
depends_on: [fabric-intake]
feeds_into: [fabric-sprint]
```

---

## OWNERSHIP — Backlog index

**Odpovědnost:** `fabric-intake`, `fabric-prio` a `fabric-close` MUSÍ spolupracovat na údržbě centrálního backlog indexu (`{WORK_ROOT}/backlog.md`):
- `fabric-intake` → regeneruje index po triážích
- `fabric-prio` → regeneruje po prioritizaci (seřazuje podle PRIO, aktualizuje prio pole ve všech items)
- `fabric-close` → regeneruje po uzavření sprintu (DONE items, carry-over logika)

**Invariant:** Index je vždy aktuální s jednotlivými backlog soubory v `{WORK_ROOT}/backlog/{id}.md` (asynchronní update je povolený, ale konsistence se musí ověřit v auditu).

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

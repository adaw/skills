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

### 1) Načti vizi (pro Impact)

Z `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` vytáhni:
- pillars, goals, success metrics (z core vize i sub-vizí)
- pokud backlog item explicitně odkazuje na goal/pillar (preferovaně přes `linked_vision_goal` ve frontmatter), zvyšuje to Impact

### 2) Načti backlog items

Projdi všechny soubory:
```bash
find {WORK_ROOT}/backlog -maxdepth 1 -type f -name "*.md"
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

- Každý aktivní backlog item má `prio` integer
- backlog.md je seřazený podle PRIO
- report existuje

Pokud ne → vytvoř intake item `intake/prio-failed-{date}.md` + CRITICAL v reportu.

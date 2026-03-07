# Prioritization Scoring Logic — fabric-prio

## 7.2) Načti a parsuj backlog items

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

---

## 7.3) Urči skóre faktorů (Impact, Urgency, Readiness, EffortScore)

**Co:** Spočítej čtyři faktory pro každý item podle přehledných tabulek.

**Jak (detailní instrukce):**

### Impact (0–10)

- **Tier baseline:**
  - T0 = 8
  - T1 = 6
  - T2 = 4
  - T3 = 2

- **Bonuses:**
  - Bug/Security hotfix: +1 až +2
  - Item mapuje přímo na vision goal: +1
  - Critical path blocker: +1

- **Penalties:**
  - T0/T1 bez `linked_vision_goal`: -3 (min 0) + intake item

### Urgency (0–10)

- **BLOCKED blocker pro T0 chain:** 9–10 (if blocking other T0s)
- **Časově citlivé (release/regrese):** 8–10 (deadline < 3 days)
- **Jinak dle Tier:**
  - T0 = 7–8
  - T1 = 5–6
  - T2 = 3–4
  - T3 = 1–2

### Readiness (0–10)

- **READY:** 8–10 (can start immediately)
- **DESIGN:** 4–7 (design done, not ready to code)
- **IDEA:** 1–3 (concept only)
- **IN_PROGRESS/IN_REVIEW:** 8 (но WIP=1, neplánují se jako nové)

### Effort → EffortScore

- **XS (< 2h):** 1
- **S (2–4h):** 3
- **M (4–8h):** 5
- **L (1–3 days):** 7
- **XL (> 3 days):** 9
- **TBD:** odhadni (preferovaně M=5), jinak WARN do reportu

---

## 7.4) Spočítej PRIO a zapiš do item frontmatter

**Co:** Aplikuj transparentní model: `PRIO = (Impact × 3) + (Urgency × 2) + (Readiness × 2) - (EffortScore × 1) - (Staleness × 1)`.

**Jak:**
```bash
# Pro každý item:
PRIO=$((($IMPACT * 3) + ($URGENCY * 2) + ($READINESS * 2) - ($EFFORT_SCORE * 1) - ($STALENESS * 1)))

# Normalizuj na 1–100 (relativní škála je důležitá)
PRIO_NORM=$((($PRIO * 100) / 100))  # nebo use fabric.py apply

# Zapiš do frontmatter: prio: <int>
```

### Staleness (0–5)

- **< 7 dní:** 0
- **7–30 dní bez pohybu:** 1
- **30–90 dní:** 2
- **90–180 dní:** 3
- **> 180 dní:** 5 + intake item `prio-stale-{id}.md`

### Monotonicity Guard

`updated:` field NESMÍ jít zpět. Pokud nový `updated` < stávající, drž starou hodnotu (neaktualizuj).

**Minimum:** Všechny itemy mají `prio:` integer (1–100).

**Anti-patterns:**
- Neměň `status` (to řeší analyze/implement/review/close)
- Nepoužívej magic čísla (vždy viditel model)

---

## 7.5) Spočítej konkrétní příklady (K10 Fix)

### Příklad 1: High-Priority Security Task

```
Item: task-b042-add-input-validation.md

Faktor Breakdown:
Impact = 9 (T0=8 + 1 security hotfix)
Urgency = 9 (T0=7 + 2 DOS vulnerability urgency)
Readiness = 10 (READY status)
EffortScore = 5 (M estimate)
Staleness = 0 (created today)

PRIO = (9×3) + (9×2) + (10×2) - (5×1) - (0×1)
     = 27 + 18 + 20 - 5 - 0
     = 60 (URGENT — execute immediately)
```

### Příklad 2: Medium-Priority Refactoring

```
Item: task-b031-refactor-triage-service.md

Faktor Breakdown:
Impact = 4 (T2=4, no bonus)
Urgency = 3 (T2=3, not urgent)
Readiness = 5 (DESIGN status)
EffortScore = 7 (L estimate)
Staleness = 1 (40 days without update)

PRIO = (4×3) + (3×2) + (5×2) - (7×1) - (1×1)
     = 12 + 6 + 10 - 7 - 1
     = 20 (MEDIUM — backlog, low urgency)
```

### Příklad 3: Low-Priority Tech Debt

```
Item: task-b001-refactor-logger.md

Faktor Breakdown:
Impact = 2 (T3=2)
Urgency = 1 (T3=1, no blocker)
Readiness = 3 (IDEA status)
EffortScore = 9 (XL estimate)
Staleness = 5 (190 days stale) → triggers stale item intake

PRIO = (2×3) + (1×2) + (3×2) - (9×1) - (5×1)
     = 6 + 2 + 6 - 9 - 5
     = 0 (LOWEST — archive or close)
```

---

## Vision-Fit Gate

T0/T1 bez `linked_vision_goal`:
- Penalizuj Impact -3 (min 0)
- Vytvoř intake item `prio-missing-vision-link-{id}.md`
- Flag v reportu jako WARNING

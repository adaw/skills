---
name: fabric-vision
description: "Analyze and validate project vision documents extracting goals, pillars, constraints, success metrics, and decision principles. Produces vision report and generates intake items for incomplete/ambiguous specifications preventing drift."
---

<!-- built from: builder-template -->

# fabric-vision — Analýza vize + quality gates pro „směr"

---

## §1 — Účel

Zajistit, že agent ví proč projekt existuje, co je cílem (a co není), jak poznáme úspěch, a jaké jsou principy rozhodování. Bez kvalitní vize se backlog rozpadne na náhodnou práci. Skill analyzuje core vision.md a sub-vize v {VISIONS_ROOT}, detekuje konflikty a zjistí, zda je vize dosažitelná.

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "vision" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "vision" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "vision" \
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

# --- Precondition 2: State existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 3: Vision dokument existuje ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "STOP: {WORK_ROOT}/vision.md not found — run fabric-init with vision template first"
  exit 1
fi

# --- Precondition 4: Visions directory exists ---
mkdir -p "{WORK_ROOT}/fabric/visions"

# State validation — check current phase is compatible
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "orientation" ]; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-vision. Expected: orientation"
  exit 1
fi
```

**Dependency chain:** `fabric-init` → [fabric-vision] → `fabric-gap` (and others)

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/vision.md` — core vize (purpose, pillars, principles, constraints)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/fabric/visions/*.md` — sub-vize a rozšíření (ekonomika, bezpečnost, governance, architektonické vize, roadmap detaily…)

**Vztah core vision ↔ sub-vize:** `vision.md` je kořenový dokument definující proč, co a jak. Sub-vize v `{VISIONS_ROOT}/` rozvíjejí jednotlivé pilíře do hloubky. Core `vision.md` by měl na sub-vize odkazovat. Sub-vize NESMÍ odporovat core vizi.

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/vision-improve-*.md` (schema: `fabric.intake_item.v1`) — když chybí klíčové části

---

## §6 — Deterministic FAST PATH

Než začneš analyzovat, proveď deterministické kroky:

```bash
# 1. State validation
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "orientation" ]; then
  echo "STOP: Wrong phase: $CURRENT_PHASE"
  exit 1
fi

# 2. Path traversal guard
validate_path() {
  if echo "$1" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $1"
    exit 1
  fi
}

validate_path "{WORK_ROOT}/vision.md"
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### K2: Counter initialization and validation
```bash
# K5: Read from config.md
CONFIG_MAX_CAP=$(grep 'VISION.max_capabilities:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MAX_CAPABILITIES=${CONFIG_MAX_CAP:-${MAX_CAPABILITIES:-200}}

# K2: Counter initialization
CAP_COUNTER=0

# K2: Numeric validation
if ! echo "$MAX_CAPABILITIES" | grep -qE '^[0-9]+$'; then
  MAX_CAPABILITIES=200
  echo "WARN: MAX_CAPABILITIES not numeric, reset to default (200)"
fi
```

Postup je organizován do 5 hlavních kroků. Detailní instrukce, bash skripty, příklady a anti-patterns najdeš v **references/workflow.md**. Zde je přehled:

### 7.1) Načti a strukturalizuj vizi

**Co:** Extrahuj pilíře, cíle, principy, non-goals, metriky a constraints z core vision.md a sub-vize.

**Jak:** Bash skripty na extrakci:
- Pilíře: `grep "^## " vision.md`
- Cíle per pilíř: awk/grep na sekci pod pilířem
- Principy, Non-goals, Constraints, Metriky: section extraction

**Minimum:** Extrahované pilíře, ≥1 cíl, ≥3 principy, ≥1 non-goal, ≥1 constraint.

**Anti-patterns:**
- Nic neextrahovat (chybný regex)
- Počítat duplicity (musíš deduplikovat klíčová slova)

→ Detaily v **references/workflow.md § 1: Načti a strukturalizuj vizi**

### 7.2) Vision quality gates — Scoring-based assessment

**Co:** Vyhodnoť strukturální korektnost (jsou všechny povinné sekce?), metriky kvalitu (měřitelné + time-bound?), non-goals rozumnost (mají zdůvodnění?), constraints evidenci.

**Jak:** Bash skripty na:
- Structural score: kontrola přítomnosti sekcí
- Metrics good %: podíl měřitelných metrik
- Non-goals reasoned %: podíl zdůvodněných non-goals
- Constraints measured %: podíl měřitelných constraints

**Minimum:** Structural score ≥3/4; aspoň 1 good metric, 1 reasoned non-goal, 1 measured constraint.

**Quality Gate Verdict:** PASS pokud structural=4 AND metrics≥50% AND non-goals≥50% AND constraints≥50%; jinak FAIL.

→ Detaily v **references/workflow.md § 2: Vision quality gates**

### 7.3) Per-pillar kvantitativní assessment

**Co:** Pro každý pilíř spočítej: Total Goals, Backlog Coverage %, Done Items, Implementation %, Drift, Verdict.

**Jak:** Bash na vyhledávání v backlog/, počítání statusů (DONE/IN_PROGRESS), detekci driftu z poslední aktivity.

**Minimum:** Každý pilíř má: číselný Coverage %, Impl %, Drift (LOW/MED/HIGH), Verdict (ON_TRACK/CAUTION/DEVIATION).

→ Detaily v **references/workflow.md § 3: Per-pillar assessment**

### 7.4) Detekcí ambiguity a konfliktů

**Co:** Najdi rozpory mezi core vizí a sub-vizemi; vágní cíle bez metrik; chybějící definice cílového uživatele; osiřelé sub-vize.

**Jak:** Bash keyword extraction, conflict detection patterns (local vs. cloud, simple vs. complex), orphan detection.

**Minimum:** Detekuj aspoň 3 typy problémů (structural gaps, metric vagueness, conflicts).

→ Detaily v **references/workflow.md § 4: Detekce ambiguity a konfliktů**

### 7.5) Vytvoř vision report

**Co:** Napište strukturovaný report s Extracted Artifacts, Quality Gate Assessment, Per-Pillar Assessment, Realism Assessment, Top Risks, Backlog Implications, Intake Items.

**Jak:** Template v §9 níže.

**Minimum:** Report MUSÍ mít: Executive Summary, Extracted Artifacts, Quality Gates, Per-Pillar table s ≥1 pilířem, Top 5 Risks (≥3 items), Realism Verdict.

→ Detaily v **references/workflow.md § 5: Report creation** a **references/examples.md**

### K10: Inline Example — LLMem Vision Analysis

**Input:**
```
vision.md pillars: [Capture, Triage, Recall] with goals:
- Capture: deterministic event logging (no LLM in path)
- Triage: regex-based secrets detection & hashing
- Recall: cosine + Jaccard scoring, injection format
Non-goals: inference, fine-tuning, real-time streaming
```

**Output:**
Report excerpt:
```
## Extracted Artifacts
Pillars: 3 (Capture, Triage, Recall)
Principles: 6 found (fail-open, deterministic, event-sourced, PII-safe, …)
Coverage: 100% (all pillars → backlog items)
Quality Gate: PASS (4/4 structural checks)
```

### K10: Anti-patterns (s detekcí)
```bash
# A1: Undocumented Pillar
# Detection: grep -c "^## " vision.md && grep -c "WORK_ROOT/backlog" backlog.md | diff
# Fix: Add backlog items linking to each pillar in vision.md

# A2: Vague Success Metrics
# Detection: grep "success\|metric" vision.md | grep -v "%" | grep -v "days"
# Fix: Rewrite as measurable + time-bound (e.g., "80% test coverage by sprint 5")

# A3: Conflicting Principles
# Detection:
grep "^- " "{WORK_ROOT}/vision.md" | sort > /tmp/vision_principles.txt
for f in "{WORK_ROOT}"/visions/*.md; do grep "^- " "$f" 2>/dev/null; done | sort > /tmp/sub_principles.txt
comm -12 /tmp/vision_principles.txt /tmp/sub_principles.txt | head -5
# Pokud duplicity → pravděpodobný konflikt. Fix: Consolidate or note trade-offs in Non-Goals
```

---

## §8 — Quality Gates (pokud skill má gates)

### Gate 1: Report Validation

```bash
REPORT="${WORK_ROOT}/reports/vision-$(date +%Y-%m-%d).md"

# Check 1: Report exists and has content
if [ ! -f "$REPORT" ] || [ ! -s "$REPORT" ]; then
  echo "FAIL: Report missing or empty"
  exit 1
fi

# Check 2: Required sections exist
REQUIRED_SECTIONS=("Executive Summary" "Extracted Artifacts" "Quality Gate Assessment" "Per-Pillar Assessment" "Top 5 Risks")
for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "^## $section" "$REPORT"; then
    echo "FAIL: Missing section: $section"
    exit 1
  fi
done

# Check 3: Per-Pillar Assessment has ≥1 pillar row
PILLAR_ROWS=$(grep "^| [^P]" "$REPORT" | grep -v "Pilíř" | wc -l)
if [ "$PILLAR_ROWS" -lt 1 ]; then
  echo "FAIL: Per-Pillar Assessment is empty"
  exit 1
fi

# Check 4: All pillar rows have numeric Coverage %
INCOMPLETE_COVERAGE=$(grep "^| [^P]" "$REPORT" | grep -v "[0-9]\+%" | wc -l)
if [ "$INCOMPLETE_COVERAGE" -gt 0 ]; then
  echo "FAIL: $INCOMPLETE_COVERAGE pillar rows missing Coverage %"
  exit 1
fi

# Check 5: Drift and Verdict values are valid
INVALID_DRIFTS=$(grep "^| [^P]" "$REPORT" | grep -v "LOW\|MEDIUM\|HIGH" | wc -l)
INVALID_VERDICTS=$(grep "^| [^P]" "$REPORT" | grep -v "ON_TRACK\|CAUTION\|DEVIATION" | wc -l)
if [ "$INVALID_DRIFTS" -gt 0 ] || [ "$INVALID_VERDICTS" -gt 0 ]; then
  echo "FAIL: Invalid Drift or Verdict values"
  exit 1
fi

echo "✓ Report validation PASSED"
```

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md` s tímto schematem:

```md
---
schema: fabric.report.v1
kind: vision
step: "vision"
version: "1.0"
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# Vision Analysis Report — {date}

## Executive Summary
{1-2 věty shrnutí: je vize jasná, měřitelná, dosažitelná?}

## Extracted Artifacts

### Purpose/Mission
{Z vision.md, 1-3 věty}

### Pillars ({pillar_count} celkem)
- Pillar 1: {Popis}
- Pillar 2: {Popis}

### Principles ({principle_count} celkem)
{Vyjmenování}

### Goals by Pillar
- **Pillar 1** ({goal_count} goals):
  - Goal A: {Měřitelná? Deadline?}

### Non-Goals ({non_goal_count} celkem)
{Vyjmenování s vysvětlením}

### Success Metrics ({metric_count} celkem, {measured_pct}% measurable)
{Vyjmenování; flag které jsou vágní}

## Quality Gate Assessment

### Structural Validation
| Check | Result | Evidence |
|-------|--------|----------|
| Principles ≥3 | {PASS/FAIL} | Found {N} |
| Goals ≥1 | {PASS/FAIL} | Found {N} |
| Non-goals ≥1 | {PASS/FAIL} | Found {N} |
| Constraints ≥1 | {PASS/FAIL} | Found {N} |

**Structural Score: {X}/4**

### Metrics Quality
{GOOD}/{TOTAL} measurable + time-bound
{List weak metrics}

### Non-Goals Reasoning
{REASONED}/{TOTAL} have explicit reasoning

### Constraints Evidence
{MEASURED}/{TOTAL} measurable + reasoned

**Quality Gate Verdict: {PASS ✓ / FAIL ✗}**

### Vision Realism Assessment
- Pillar count: {N} (target: ≤7) → {✓ OK / ⚠ WARN}
- Max goals/pillar: {N} (target: ≤10) → {✓ OK / ⚠ WARN}
- Conflicting goals: {0 / list} → {✓ None / ⚠ CRITICAL}
- Timeline estimate: {N} sprints → {✓ OK / ⚠ WARN}

**Realism Verdict: {REALISTIC / CAUTION / UNREALISTIC}**

## Per-Pillar Assessment

| Pilíř | Total Goals | Coverage % | Done Items | Impl % | Last Activity | Drift | Verdict |
|-------|---|---|---|---|---|---|---|
| {Pillar 1} | {N} | {X}% | {N} | {Y}% | {date} | {LOW/MEDIUM/HIGH} | {ON_TRACK/CAUTION/DEVIATION} |

## Sub-Vision Alignment
{List sub-visions and conflicts, or "No sub-visions"}

## Top 5 Risks & Gaps
1. **Risk:** {Description} → **Mitigation:** {Action}

## Backlog Implications
Based on vision, recommended priorities...

## Intake Items Generated
{List generated items or "None"}
```

---

## §10 — Self-check (povinný — BLOKUJÍCÍ ENFORCEMENT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md`
- [ ] Report není prázdný

### Quality checks
- [ ] Report má: Executive Summary
- [ ] Report má: Extracted Artifacts (Purpose/Mission/Pillars/Principles/Goals/Non-goals/Metrics)
- [ ] Report má: Quality Gate Assessment (all 4 validation categories)
- [ ] Report má: Per-Pillar Assessment s ≥1 pilířem
  - [ ] Každý pilíř má: Total Goals, Coverage %, Done Items, Implementation %, Drift, Verdict (čísla, ne placeholdery)
- [ ] Report má: Vision Realism Assessment
- [ ] Report má: Top 5 Risks s ≥3 items
- [ ] Pokud Quality Gates FAIL: existe intake item `{WORK_ROOT}/intake/vision-improve-*.md` s konkrétními gaps

### Invarianty
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován
- [ ] Protocol log obsahuje START i END záznam

**ENFORCEMENT:** Run Gate 1 validation bash (§8) before marking DONE. Pokud nějaký check FAIL → **exit 1 a nepokračuj**.

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí prereq soubor | STOP + jasná zpráva |
| FAST PATH | Validace selže | STOP + exit 1 |
| Struktura vize | Chybí povinné sekce | WARN + vytvoř intake item |
| Quality gates | <50% metrics good | FAIL + intake item |
| Self-check | Check FAIL | Report FAIL + intake item |

**Obecné pravidlo:** Skill je fail-fast na POVINNÝCH vstupech (chybí → STOP). Volitelné vstupy (sub-vize) → pokračuj s WARNING.

**K3 escalation:** Pokud vision.md NEMŮŽE být vytvořen (disk full, permissions) → STOP + exit 1. Intake-only WARN je pro quality failures.

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
phase: orientation
step: vision
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true
depends_on: [fabric-init]
feeds_into: [fabric-architect, fabric-gap, fabric-sprint]
```

---

## Odkazy

- **Detailní workflow:** [references/workflow.md](./references/workflow.md)
- **Příklady s daty:** [references/examples.md](./references/examples.md)

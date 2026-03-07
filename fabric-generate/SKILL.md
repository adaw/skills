---
name: fabric-generate
description: "Autonomously generate high-value work items from vision goals, security/quality gaps, and codebase signals when backlog is thin. Produces 0–8 intake items with strong deduplication preventing spam and maintaining quality."
---

<!-- built from: builder-template -->

## §1 — Účel

Když backlog nemá dost kvalitních položek nebo projekt stagnuje, `fabric-generate` vytvoří další smysluplnou práci:
- zrychlí vývoj,
- zvýší bezpečnost,
- zlepší kvalitu testů a dokumentace,
- a posune projekt směrem k vizi.

Bez generace backlog zůstane chudinský, implementátor stagnuje. Generace používá determinismus (codebase scanning + vision alignment heuristics, ne LLM rozhodování) pro kandidáty, pak inteligentní deduplikaci proti existujícím položkám.

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci zapiš do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "generate" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "generate" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "generate" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

```bash
# --- Precondition 1: state.md existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: Verifikuj phase ---
PHASE=$(grep -E '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$PHASE" | grep -qE '^(orientation|planning|implementation|closing|utility)$'; then
  echo "STOP: Invalid phase='$PHASE' in state.md"
  exit 1
fi

# --- Precondition 3: config.md existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 4: Backlog kontrola (volitelná optimalizace) ---
CURRENT_SPRINT=$(grep -E '^current_sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ -n "$CURRENT_SPRINT" ] && [ "$CURRENT_SPRINT" != "null" ]; then
  echo "INFO: Active sprint detected — will generate only if backlog < 10 READY items"
fi
```

**Dependency chain:** `fabric-init → [fabric-generate]`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/vision.md` nebo `{VISIONS_ROOT}/*.md`
- `{WORK_ROOT}/backlog.md` + backlog items (pro dedup)
- `{WORK_ROOT}/templates/intake.md` (šablona output)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/decisions/INDEX.md` + `decisions/*.md`
- `{WORK_ROOT}/specs/INDEX.md` + `specs/*.md`
- poslední reporty: `architect-*.md`, `gap-*.md`, `check-*.md`, `review-*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` (pro evidence)

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- 0–8 intake items: `{WORK_ROOT}/intake/generate-{slug}.md` (schema: `fabric.intake_item.v1`)

Výstup jsou **intake items** (ne přímo backlog), aby triage (`fabric-intake`) zachovala standardní pipeline.
Poznámka: 0 items je OK (backlog zdravý, deduplikace omezila). V takovém případě vždy vytvoř report.

---

## §6 — Deterministic FAST PATH

Než začneš analyzovat/generovat, proveď deterministické kroky (bez LLM):

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index

# 3. Backlog snapshot pro dedup (povinný)
python skills/fabric-init/tools/fabric.py backlog-scan \
  --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"

# 4. K2 Fix: Initialize generation counter
MAX_ITEMS=${MAX_ITEMS:-100}
GENERATION_COUNTER=0

if ! echo "$MAX_ITEMS" | grep -qE '^[0-9]+$'; then
  MAX_ITEMS=100
  echo "WARN: MAX_ITEMS not numeric, reset to default (100)"
fi
```

Použij backlog snapshot pro počet READY/DESIGN položek, deduplikaci, rozhodnutí zda generovat.

---

## §7 — Postup (JÁDRO SKILLU)

Detailní kroky viz `references/7-POSTUP.md`.

Shrnutí:
1. **7.1 Zjisti, jestli generovat** — Backlog index: pokud < 10 READY → generuj; jinak jen quality improvements
2. **7.2 Discovery zdroje** — Scan 7 kategorií (Security, Reliability, Tests, Docs, Performance, DX, Governance); kandidáty se evidence
3. **7.3 Vision alignment** — HIGH/MED/LOW + zdůvodnění (reference na vision.md goals)
4. **7.4 Deduplikace** — Backlog snapshot dedup; skip existující; log evidence
5. **7.5 Vytvoř items** — Top 3–8 deduplikovaných; max 8; source=generate; priority 1–10; evidence
6. **7.6 Generate report** — Schema fabric.report.v1; souhrn, state, sources, dedup tabulka, items tabulka, warnings

---

## §8 — Quality Gates

Žádné; skill je read-only analýza.

---

## §9 — Report

```md
---
schema: fabric.report.v1
kind: generate
run_id: "{RUN_ID}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# generate — Report {YYYY-MM-DD}

## Souhrn
{1–3 věty: kolik items, proč}

## State
- Backlog status: READY={N}, DESIGN={M}
- Generation decision: YES / NO (reason)

## Discovery sources
- Security: {N} candidates
- Reliability: {N}
- Test quality: {N}
- Docs drift: {N}
- Performance: {N}
- DX: {N}
- Governance: {N}
Total before dedup: {N}

## Deduplication
| Candidate | Reason |
|-----------|--------|
| ... | duplicate of backlog-XXX |

Total after dedup: {N}

## Generated intake items
| Title | Type | Priority | Alignment | Evidence |
|-------|------|----------|-----------|----------|
| ... | Task | 9 | HIGH | gap report |

Total: {N} items (max 100 respected)

## Warnings
{seznam nebo "none"}
```

---

## §10 — Self-check (povinný)

### Existence checks
- [ ] Report: `{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md` s `schema: fabric.report.v1`
- [ ] Backlog snapshot: `{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json`
- [ ] Protocol log: START a END záznam s `skill: generate`
- [ ] Všechny generated items: `{WORK_ROOT}/intake/generate-{slug}.md`

### Quality checks
- [ ] Report má: Souhrn, State, Discovery sources, Dedup evidence, Generated items, Warnings
- [ ] Max 8 items (ne více)
- [ ] Každý item: title, source=generate, initial_type, raw_priority (1-10), evidence
- [ ] Dedup ověření: tabulka backlog kontroly, žádný duplikát
- [ ] Dedup evidence: seznam skippnutých + vysvětlení

### Invariants
- [ ] Žádný file mimo `reports/` a `intake/` modifikován
- [ ] Backlog.md, Config.md, Vision.md NEJSOU modifikovány
- [ ] Protocol log má START i END

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | state.md chybí | STOP + „run fabric-init first" |
| FAST PATH | backlog-scan selže | WARN + continue (dedup aproximativní) |
| Discovery | Nula kandidátů | WARN + report (OK — backlog zdravý) |
| Postup | Intake create fail | ERROR + protocol error + intake item |
| Self-check | Check fail | Report WARN + integrity item |

**Obecné:** Fail-open na VOLITELNÝCH (reports chybí → WARNING), fail-fast na POVINNÝCH (config chybí → STOP).

---

## §12 — Metadata

```yaml
phase: utility
step: autonomous_work_generation
may_modify_state: false
may_modify_backlog: false
may_create_intake: true
may_modify_code: false
depends_on: [fabric-init]
feeds_into: [fabric-intake]
```

---

## Anti-patterns (ZAKÁZÁNO)

- **A1: Duplicate Intake** — Backlog dedup check; skip existující
- **A2: Empty Intake** — Title + description povinné
- **A3: Invalid Priority** — Raw_priority 1–10; clamp na hranice
- **A4: Vague Candidates** — Evidence MUSÍ: konkrétní file/pattern/report + řádek
- **A5: Vision Misalignment** — LOW alignment jen kritická security/operational
- **A6: Generation Loop** — Counter + numeric validation (K2); max MAX_ITEMS

---

## K2 Fix: Generation Loop with Counter

```bash
while read -r candidate; do
  GENERATION_COUNTER=$((GENERATION_COUNTER + 1))

  if ! echo "$GENERATION_COUNTER" | grep -qE '^[0-9]+$'; then
    GENERATION_COUNTER=0
    echo "WARN: GENERATION_COUNTER corrupted, reset to 0"
  fi

  if [ "$GENERATION_COUNTER" -ge "$MAX_ITEMS" ]; then
    echo "WARN: max candidates reached ($GENERATION_COUNTER/$MAX_ITEMS)"
    break
  fi
  GENERATED_ITEMS+=("$candidate")
done
```

---

## K4 Fix: Git Safety

Skill NESMÍ provádět git operace. K4 je N/A.

---

## K7 Fix: Path Traversal Guard

```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}
```

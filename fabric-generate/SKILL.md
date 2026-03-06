---
name: fabric-generate
description: "Autonomously generate high-value work when the system has nothing urgent to do. Uses vision alignment + codebase signals (architect/gap/check/review) to propose 0–8 actionable intake items (source=generate) and writes a generate report. Strong deduplication to avoid spam."
---

# GENERATE — Autonomní generování work items (vision-aligned)

## Účel

Když backlog nemá dost kvalitních položek nebo projekt stagnuje, `fabric-generate` vytvoří další smysluplnou práci:
- zrychlí vývoj,
- zvýší bezpečnost,
- zlepší kvalitu testů a dokumentace,
- a posune projekt směrem k vizi.

## Preconditions — State & Phase Validation

**PŘED jakoukoli prací ověř:**

```bash
# 1. Verify state.md exists
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# 2. Verify phase is one of: orientation, planning, implementation, closing, utility
PHASE=$(grep -E '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$PHASE" | grep -qE '^(orientation|planning|implementation|closing|utility)$'; then
  echo "STOP: Invalid phase='$PHASE' in state.md — expected one of: orientation, planning, implementation, closing, utility"
  exit 1
fi

# 3. fabric-generate runs in utility phase (anytime, no sprint binding)
# If sprint is active but backlog is healthy → skip generation
CURRENT_SPRINT=$(grep -E '^current_sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ -n "$CURRENT_SPRINT" ] && [ "$CURRENT_SPRINT" != "null" ]; then
  echo "INFO: Active sprint detected (sprint=$CURRENT_SPRINT) — will generate only if backlog < 10 READY items"
fi
```

---

## K2 Fix: Generation Loop with Counter

```bash
MAX_ITEMS=${MAX_ITEMS:-100}
GENERATION_COUNTER=0
GENERATED_ITEMS=()

# Validate MAX_ITEMS is numeric (K2 tight validation)
if ! echo "$MAX_ITEMS" | grep -qE '^[0-9]+$'; then
  MAX_ITEMS=100
  echo "WARN: MAX_ITEMS not numeric, reset to default (100)"
fi
```

When scanning vision goals, gaps, or codebase for generation candidates:
```bash
# Counter prevents infinite loops during item generation
while read -r candidate; do
  GENERATION_COUNTER=$((GENERATION_COUNTER + 1))

  # Numeric validation of counter (K2 strict check)
  if ! echo "$GENERATION_COUNTER" | grep -qE '^[0-9]+$'; then
    GENERATION_COUNTER=0
    echo "WARN: GENERATION_COUNTER corrupted, reset to 0"
  fi

  if [ "$GENERATION_COUNTER" -ge "$MAX_ITEMS" ]; then
    echo "WARN: max generated items reached ($GENERATION_COUNTER/$MAX_ITEMS)"
    break
  fi
  GENERATED_ITEMS+=("$candidate")
done
```

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-generate" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-generate" --event end --status OK --report "{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Výstup jsou **intake items** (ne přímo backlog), aby triage (`fabric-intake`) zachovala standardní pipeline.

> Poznámka: **0 items je OK** (např. backlog je zdravý nebo deduplikace nedovolí nic nového). V takovém případě stále vytvoř report.

## K10 Fix: Generation Examples with Real LLMem Data

Here are concrete examples of generated intake items aligned with LLMem vision and gaps:

**Example 1: Gap-driven generation — Missing rate limiting**

Gap detected: POST /capture/event has no rate limiting (CRITICAL security gap from gap report)
Generated intake item: `intake/generate-add-rate-limiting-middleware.md`
```yaml
title: "Add rate limiting middleware to /capture/event endpoint"
source: generate
initial_type: Task
raw_priority: 8
linked_vision_goal: "Reliability - Rate Limiting"
reasoning: "Security gap: DOS vulnerability on public endpoint. Gap report: HIGH impact. Effort: S (1 day). Vision-aligned with reliability pillar."
```

**Example 2: Test coverage generation — Undocumented module**

Gap/check detected: `triage/patterns.py` has 0% test coverage (from check report)
Generated intake item: `intake/generate-add-tests-for-patterns.md`
```yaml
title: "Add comprehensive test suite for triage/patterns.py secret detection"
source: generate
initial_type: Task
raw_priority: 6
reasoning: "Code quality: Triage patterns module (5 functions) untes. Coverage: 0%. Estimated effort: M (2 days). Critical path for triage reliability."
```

**Example 3: Docs generation — Missing API documentation**

Gap detected: 3 API endpoints exist in code but not documented (from fabric-gap docs check)
Generated intake item: `intake/generate-document-recall-api.md`
```yaml
title: "Document /recall endpoint with usage examples and parameters"
source: generate
initial_type: Chore
raw_priority: 5
reasoning: "User discovery: /recall endpoint is critical but undocumented. Gap report flagged. Effort: S (4 hours). Quick win."
```

**Generation report summary:**
- Scanned: 22 vision goals, 7 security gaps, 5 coverage gaps
- Deduplicated against existing backlog: 15 candidates → 3 unique items generated (dedupe removed 12 near-duplicates)
- Generated intake items: 3 (max 8 respected)
- Total effort: 5.5 days (within reasonable buffer)

---

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

---

## FAST PATH (doporučeno) — backlog snapshot strojově

Pro rychlost a determinismus si nejdřív vyrob snapshot backlogu:

```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

Použij ho pro:
- počet READY/DESIGN položek,
- deduplikaci title/id,
- rychlé zhodnocení, zda má smysl generovat.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (sub-vize pro širší kontext)
- `{WORK_ROOT}/backlog.md` + backlog items (pro dedup)
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`
- poslední reporty (pokud existují):
  - `reports/architect-*.md`
  - `reports/gap-*.md`
  - `reports/check-*.md`
  - `reports/review-*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` (rychlý scan)

---

## Výstupy

- 0–8 intake items v `{WORK_ROOT}/intake/` dle `{WORK_ROOT}/templates/intake.md`:
  - `source: generate`
  - `initial_type` typicky `Chore/Task/Bug`
  - `raw_priority` 3–10
- report `{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md`

---

## Guardrails (anti-spam)

1. Max 8 nových intake itemů na běh.
2. Každý item musí mít:
   - 1 větu „proč“ (value/risk),
   - evidence (soubor/pattern nebo „missing“),
   - doporučenou akci.
3. Silná deduplikace:
   - pokud existuje podobný backlog item, negeneruj duplicitu; místo toho přidej poznámku do existujícího itemu nebo vytvoř intake „clarify existing“.

---

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="orientation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-generate. Expected: $EXPECTED_PHASES"
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
# validate_path "$OUTPUT_FILE"
```

### 1) Zjisti, jestli je potřeba generovat

Podívej se do backlog indexu:
- pokud je v backlogu < 10 položek se statusem `READY` nebo `DESIGN` (a nejsou DONE) → generuj
- pokud backlog je zdravý → vygeneruj max 3 „quality improvements“ nebo nic

### 2) Discovery zdroje (7 kategorií)

Vygeneruj kandidáty z těchto oblastí:

1) **Security**  
- input validation, secrets hygiene, dependency risk, authz boundaries

2) **Reliability & Error handling**  
- retries/timeouts, cancellation, logging, observability

3) **Test quality**  
- chybějící tests pro kritické moduly, flaky tests, missing regression for recent bugs

4) **Docs drift**  
- veřejné API bez docs, chybějící usage examples

5) **Performance**  
- hot paths, N^2 loops, unnecessary I/O

6) **Developer Experience**  
- CI gates, pre-commit, faster local dev loop

7) **Architektonická governance**
- chybějící ADR/spec pro klíčové oblasti
- drift: kód proti accepted ADR / active spec
- stale proposed ADR (> stale_proposed_days)
- stale draft specs (> stale_draft_days)

### 3) Vision alignment scoring (jednoduše)

Pro každý kandidát napiš do reportu (ber v úvahu core vizi i sub-vize z `{VISIONS_ROOT}/`):
- alignment HIGH/MEDIUM/LOW
- proč (který goal/pillar, z core nebo sub-vize)

LOW alignment může projít jen pokud jde o kritickou bezpečnost/operational věc.

### 4) Deduplikace

Před vytvořením intake itemu:
- zkontroluj backlog titles + intake pending titles (podobnost)
- pokud existuje:
  - nevytvářej duplicitu
  - do reportu napiš „deduped”

**Dedup pseudokód (P2 work quality):**
```python
def dedup_items(items: list[Item]) -> list[Item]:
    seen = set()
    result = []
    for item in items:
        key = normalize(item.title)  # lowercase, strip special chars
        if key not in seen:
            seen.add(key)
            result.append(item)
        else:
            log(f”DEDUP: skipping {item.id} (duplicate of {key})”)
    return result
```

### 5) Vytvoř intake items (top 3–8)

Použij `{WORK_ROOT}/templates/intake.md`:
- `source: generate`
- `initial_type`:
  - Bug pro regresní/defekt
  - Chore pro tooling/CI
  - Task pro implementační změny
  - Spike pro research/unknown
- `raw_priority`:
  - 9–10 pro security/reliability critical
  - 6–8 pro high impact
  - 3–5 pro nice-to-have

**Konkrétní příklady generovaných itemů:**

**Příklad 1: Security gap (Chore, prio 9)**
```yaml
---
schema: fabric.intake_item.v1
title: "Add OpenAI API key validation to environment setup"
source: generate
initial_type: Chore
raw_priority: 9
created: "2026-03-06"
status: new
---
## Kontext
Scanning {CODE_ROOT}/src/llmem/api/server.py shows environment variables loaded without validation.
Config defaults to empty string if OPENAI_KEY missing, risking silent failures.

## Doporučená akce
1. Add precondition check in fabric-init bootstrap: `if [ -z "$OPENAI_KEY" ]; then echo "STOP: OPENAI_KEY required"; exit 1; fi`
2. Document in config.md REQUIRED_ENV_VARS section
3. Create test: test_missing_openai_key_stops_bootstrap
```

**Příklad 2: Test coverage gap (Task, prio 7)**
```yaml
---
schema: fabric.intake_item.v1
title: "Add edge case tests for triage_event() empty content scenario"
source: generate
initial_type: Task
raw_priority: 7
created: "2026-03-06"
status: new
---
## Kontext
File: {CODE_ROOT}/src/llmem/triage/heuristics.py, function triage_event()
Coverage: 62% (target ≥80% for core modules). Missing: empty content edge case.

## Doporučená akce
1. Add test_triage_event_empty_content: ensure no index error when content=""
2. Add test_triage_event_whitespace_only: content="   " should be treated as empty
3. Coverage should jump to ≥78% after
```

**Příklad 3: Docs drift (Chore, prio 5)**
```yaml
---
schema: fabric.intake_item.v1
title: "Document RecallQuery.allow_secrets contract in API docs"
source: generate
initial_type: Chore
raw_priority: 5
created: "2026-03-06"
status: new
---
## Kontext
Code added `allow_secrets` field to RecallQuery (decision D0001), but {DOCS_ROOT}/api.md not updated.
Public API users won't know the field exists.

## Doporučená akce
1. Update {DOCS_ROOT}/api.md RecallQuery section: add `allow_secrets: bool (default: false)` + explanation
2. Add usage example: curl with allow_secrets=true
3. Verify link to ADR-D0001
```

### 6) Generate report

`reports/generate-{YYYY-MM-DD}.md`:
- kolik itemů vzniklo
- pro každý:
  - title
  - category
  - alignment (HIGH/MED/LOW)
  - raw_priority
  - evidence
- deduped candidates

---

## Self-check

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Backlog snapshot existuje (pokud byl spuštěn FAST PATH): `{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json`
- [ ] Protocol log má START a END záznam s `skill: generate`
- [ ] Všechny vygenerované intake items existují v `{WORK_ROOT}/intake/`

### Quality checks
- [ ] Report obsahuje povinné sekce: Summary (kolik items vygenerováno), Discovery sources, Dedup evidence, Warnings
- [ ] Max 8 intake items vygenerováno (ne více)
- [ ] Každý item má: título, evidence (konkrétní soubor/pattern), doporučenou akci, raw_priority
- [ ] Dedup ověření: **žádný item se neduplikuje** s existujícím backlog entrym (ověřeno v reportu)
- [ ] Dedup evidence: report měl seznam kontrolovaných backlog itemů a vysvětlení proč vygenerovaný item je nový

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/reports/` a `{WORK_ROOT}/intake/` nebyl modifikován
- [ ] Backlog.md NENÍ modifikován (fabric-generate jen vytváří intake, ne backlog)
- [ ] Config.md NENÍ modifikován (fabric-generate je read-only k configu)
- [ ] Vision.md NENÍ modifikován
- [ ] Protocol log má START i END záznam

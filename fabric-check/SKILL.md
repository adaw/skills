---
name: fabric-check
description: "Consistency and quality audit of the Fabric workspace. Validates directory structure, templates, backlog item schemas, backlog index, sprint plan integrity, and basic code health signals (via configured COMMANDS). Applies safe auto-fixes (e.g., regenerate backlog.md) and creates intake items for anything requiring human/agent follow-up. Writes an audit report."
---

# CHECK — Konzistenční audit + safe auto-fix

## Účel

Najít rozbité invariants dřív, než se pipeline rozjede dál:
- špatné cesty / chybějící adresáře
- rozbitá metadata (YAML schema)
- backlog index mimo sync
- sprint plán nevalidní
- config COMMANDS chybí

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-check" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-check" --event end --status OK --report "{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Aplikovat jen **bezpečné** automatické opravy (idempotentní) a vše ostatní převést na intake items.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/*.md`
- `{WORK_ROOT}/sprints/*.md`
- `{WORK_ROOT}/templates/*.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (pro vision-fit lint)
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` (existence + volitelné commands)

---

## Výstupy

- audit report: `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` (dle `{WORK_ROOT}/templates/audit-report.md`)
- safe auto-fix changes (např. regenerace backlog.md)
- intake items pro CRITICAL/WARNING:
  - `{WORK_ROOT}/intake/check-*.md`

---

## Status taxonomie (z config.md)

Backlog statusy musí být:
`IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE`

---

## Postup

### 1) Strukturální integrita workspace

Ověř existenci:
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/vision.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/` + `backlog/done/`
- `{WORK_ROOT}/intake/` + `intake/done/` + `intake/rejected/`
- `{WORK_ROOT}/reports/`
- `{WORK_ROOT}/sprints/`
- `{WORK_ROOT}/analyses/`
- `{WORK_ROOT}/templates/`
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`
- `{WORK_ROOT}/reviews/` + `reviews/INDEX.md`

CRITICAL pokud chybí → vytvoř intake item `check-missing-structure.md`.

### 2) Templates integrity

Ověř, že v `{WORK_ROOT}/templates/` existují povinné šablony (viz config).
Pokud chybí → WARNING + intake.

### 3) Backlog item schema audit

Z `{WORK_ROOT}/config.md` načti kontrakty:
- `SCHEMA.backlog_item`
- `ENUMS.statuses`, `ENUMS.tiers`, `ENUMS.efforts`, `ENUMS.types`

Pro každý `{WORK_ROOT}/backlog/*.md` (mimo `backlog/done/`):
- parse YAML frontmatter
- ověř povinné klíče:
  - `schema`, `id`, `title`, `type`, `tier`, `status`, `effort`, `created`, `updated`, `source`, `prio`
- validuj hodnoty:
  - `schema` == `SCHEMA.backlog_item`
  - `status` ∈ `ENUMS.statuses`
  - `type` ∈ `ENUMS.types`
  - `tier` ∈ `ENUMS.tiers`
  - `effort` ∈ `ENUMS.efforts`
  - `prio` je integer
  - filename odpovídá `id` (např. `{id}.md`)

Safe auto-fix (idempotentní):
- pokud chybí `schema`, doplň `schema: <SCHEMA.backlog_item>`
- pokud chybí `updated`, doplň `updated: {YYYY-MM-DD}`
- pokud chybí `prio`, doplň `prio: 0` (a reportuj WARNING; prio to později přepočítá)

Ne-safe (→ intake + WARNING/CRITICAL):
- chybějící `id` nebo `title`
- `schema` existuje, ale je **jiný** než očekávaný (drift)
- nevalidní status/type/tier/effort

### 3.1) Vision-fit lint (backlog ↔ vize)

Cíl: zabránit tomu, aby se backlog stal „košem na všechno“.

Pro každý backlog item (mimo `done/`):
- načti `tier` a `linked_vision_goal` (pokud existuje)

Pravidla:
- pokud `tier` je `T0` nebo `T1` a `linked_vision_goal` chybí nebo je prázdné:
  - vytvoř intake item `{WORK_ROOT}/intake/check-missing-vision-link-{id}.md`
  - do něj napiš: co chybí (goal/pillar), a návrh: doplnit `linked_vision_goal` nebo snížit tier
  - reportuj jako WARNING (neblokuje to okamžitě běh, ale musí se to řešit)

- pokud `linked_vision_goal` je vyplněné, ale **neobjevuje se** ani v `{WORK_ROOT}/vision.md` ani v `{VISIONS_ROOT}/*.md`:
  - vytvoř intake item `{WORK_ROOT}/intake/check-unknown-vision-link-{id}.md`
  - reportuj WARNING („vision drift / překlep / chybí sub-vize“)

### 4) Backlog index sync

Regeneruj „expected“ tabulku z backlog itemů a porovnej s `{WORK_ROOT}/backlog.md`.

Pokud nesedí:
- safe auto-fix: přepiš backlog.md na kanonickou tabulku (seřazení PRIO desc)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```
- zapiš do reportu jako FIXED


### 4.1) Governance integrity (decisions/specs/reviews)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py governance-index
python skills/fabric-init/tools/fabric.py governance-scan
```

Vyhodnoť:
- chybějící `INDEX.md` → WARNING + intake (nebo auto-fix přes `governance-index`)
- proposed ADR starší než `GOVERNANCE.decisions.stale_proposed_days` → WARNING + intake
- draft SPEC starší než `GOVERNANCE.specs.stale_draft_days` → WARNING + intake
- missing `date`/`status` ve governance souborech → WARNING + intake (oprava: doplnit metadata)

Pozn.: `governance-index` je safe auto-fix (jen přegeneruje indexy).


### 5) Sprint plan audit (pokud existuje)

Najdi aktuální sprint:
- ze `state.md` (`sprint: N`)
- sprint file: `{WORK_ROOT}/sprints/sprint-{N}.md` (pokud existuje)

Validace:
- má sekce `## Sprint Targets`
- má sekce `## Task Queue` s tabulkou
- každý Task Queue `ID` existuje jako backlog item
- `Order` je unikátní a začíná od 1 (nebo je aspoň monotónní)

Pokud Task Queue odkazuje na neexistující backlog item → CRITICAL + intake.

### 6) Config COMMANDS sanity

Z configu ověř:

- `COMMANDS.test` není `TBD` ani prázdné
- `COMMANDS.lint` není `TBD` *(prázdné = vypnuto)*
- `COMMANDS.format_check` není `TBD` *(prázdné = vypnuto)*

Pokud `COMMANDS.test` je `TBD` nebo prázdné:
- vytvoř intake item `intake/check-missing-test-command.md`
- reportuj **CRITICAL** (bez testů nelze bezpečně pokračovat)

Pokud `COMMANDS.lint` nebo `COMMANDS.format_check` je `TBD`:
- vytvoř intake item `intake/check-config-commands-tbd.md`
- reportuj **WARNING** (bez nich nelze enforce některé quality gates)

Pokud je `COMMANDS.lint` nebo `COMMANDS.format_check` prázdné:
- reportuj `SKIPPED`
- vytvoř intake item `intake/check-recommend-enable-lint-or-format.md` (doporučení)

Pokud `QUALITY.mode` je `strict` a lint/format jsou prázdné (`""`):
- reportuj **CRITICAL**
- vytvoř intake item `intake/check-strict-mode-missing-lint-or-format.md`
- FAIL

### 7) Volitelné: rychlé runtime checks (pokud commands existují)

Pokud repo má čistý working tree:

Spusť v tomto tvaru (aby nikdy neběžel prázdný příkaz):

```bash
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi
{COMMANDS.test}
```

Výsledek zapiš do reportu (PASS/FAIL).

#### Auto-fix (safe, idempotentní)

Pokud lint nebo format check failne a config má příslušný fix příkaz, **spusť auto-fix a opakuj gate**:

1. **Lint fail** + `COMMANDS.lint_fix` není prázdné → spusť `{COMMANDS.lint_fix}`, pak znovu `{COMMANDS.lint}`.
2. **Format fail** + `COMMANDS.format` není prázdné → spusť `{COMMANDS.format}`, pak znovu `{COMMANDS.format_check}`.

Auto-fix smí proběhnout **max 1×** per gate. Pokud po auto-fixu gate stále failne → zapiš do reportu jako FAIL a vytvoř intake item.

Pokud auto-fix něco opravil, commitni změny:
```bash
git add -A && git commit -m "chore: auto-fix lint/format (fabric-check)"
```

Pokud by to bylo příliš drahé, zaznamenej to jako `skipped` s důvodem.

**Volitelně (framework self-test):**
- spusť statický validator:
  ```bash
  python skills/fabric-init/tools/validate_fabric.py --workspace --runnable
  ```
  Pokud failne → CRITICAL + intake item `intake/check-validator-failed.md`.

### 7.1) Stale detection (backlog items + epics)

```bash
# Stale detection: items beze změny >30 dní
TODAY_EPOCH=$(date +%s)
for ITEM in {WORK_ROOT}/backlog/*.md; do
  [ -f "$ITEM" ] || continue
  UPDATED=$(grep '^updated:' "$ITEM" | awk '{print $2}')
  if [ -n "$UPDATED" ]; then
    ITEM_EPOCH=$(date -d "$UPDATED" +%s 2>/dev/null || echo 0)
    DAYS_OLD=$(( (TODAY_EPOCH - ITEM_EPOCH) / 86400 ))
    ITEM_TYPE=$(grep '^type:' "$ITEM" | awk '{print $2}')
    ITEM_ID=$(basename "$ITEM" .md)
    # Stale thresholds: Epic >60d, ostatní >30d
    if [ "$ITEM_TYPE" = "Epic" ] && [ "$DAYS_OLD" -gt 60 ]; then
      echo "WARN: stale Epic $ITEM_ID (${DAYS_OLD}d unchanged)"
    elif [ "$ITEM_TYPE" != "Epic" ] && [ "$DAYS_OLD" -gt 30 ]; then
      echo "WARN: stale item $ITEM_ID (${DAYS_OLD}d unchanged)"
    fi
  fi
done
```

Stale items zapiš do audit reportu + vytvoř intake items pro top 5 nejstarších.

### 7.2) Report freshness monitoring

```bash
# Report freshness: GAP ≤30d, PRIO ≤45d, CHECK ≤15d
check_report_freshness() {
  local PATTERN="$1"
  local MAX_DAYS="$2"
  local LABEL="$3"
  LATEST=$(ls -t {WORK_ROOT}/reports/${PATTERN}*.md 2>/dev/null | head -1)
  if [ -z "$LATEST" ]; then
    echo "WARN: no $LABEL report found"
  else
    REPORT_DATE=$(grep '^created_at:\|^date:' "$LATEST" | head -1 | awk '{print $2}' | cut -c1-10)
    if [ -n "$REPORT_DATE" ]; then
      REPORT_EPOCH=$(date -d "$REPORT_DATE" +%s 2>/dev/null || echo 0)
      DAYS_OLD=$(( (TODAY_EPOCH - REPORT_EPOCH) / 86400 ))
      if [ "$DAYS_OLD" -gt "$MAX_DAYS" ]; then
        echo "WARN: $LABEL report is ${DAYS_OLD}d old (max ${MAX_DAYS}d)"
      fi
    fi
  fi
}

check_report_freshness "gap-" 30 "GAP"
check_report_freshness "prio-" 45 "PRIO"
check_report_freshness "check-" 15 "CHECK"
check_report_freshness "vision-" 60 "VISION"
```

### 7.3) Spec completeness check (READY items)

Pro READY items v backlogu ověř minimální kvalitu:
```bash
for ITEM in {WORK_ROOT}/backlog/*.md; do
  STATUS=$(grep '^status:' "$ITEM" | awk '{print $2}')
  [ "$STATUS" = "READY" ] || continue
  ITEM_ID=$(basename "$ITEM" .md)
  MISSING=""
  # Musí mít ≥2 věty popisu (ne jen title)
  BODY_LINES=$(sed -n '/^---$/,/^---$/!p' "$ITEM" | grep -c '\S')
  [ "$BODY_LINES" -lt 3 ] && MISSING="${MISSING} popis(<3 řádky)"
  # Musí mít effort (ne TBD)
  EFFORT=$(grep '^effort:' "$ITEM" | awk '{print $2}')
  [ "$EFFORT" = "TBD" ] || [ -z "$EFFORT" ] && MISSING="${MISSING} effort"
  # Musí mít ≥1 AC
  grep -q '\- \[.\]' "$ITEM" 2>/dev/null || MISSING="${MISSING} AC"
  if [ -n "$MISSING" ]; then
    echo "WARN: READY item $ITEM_ID missing:${MISSING}"
  fi
done
```

### 7.4) E2E endpoint coverage ratio

```bash
# Počet definovaných routes vs E2E testů
if [ -d "{CODE_ROOT}/api/" ]; then
  ROUTE_COUNT=$(grep -rn '@app\.\(get\|post\|put\|delete\)' {CODE_ROOT}/api/ 2>/dev/null | wc -l)
  E2E_TEST_COUNT=$(grep -rn 'def test.*e2e\|def test.*integration\|def test.*api' {TEST_ROOT}/ 2>/dev/null | wc -l)
  RATIO=0
  if [ "$ROUTE_COUNT" -gt 0 ]; then
    RATIO=$(( E2E_TEST_COUNT * 100 / ROUTE_COUNT ))
  fi
  echo "E2E coverage: $E2E_TEST_COUNT tests / $ROUTE_COUNT routes = ${RATIO}%"
  if [ "$RATIO" -lt 50 ]; then
    echo "WARN: E2E coverage ${RATIO}% < 50% target"
  fi
fi
```

### 7.5) Confidence scoring per check

Pro každý finding v audit reportu přidej confidence level:
- **HIGH (95%+):** Deterministický check (file existence, schema validation, enum match)
- **MEDIUM (70-95%):** Heuristický check (stale detection — threshold může být neadekvátní, grep-based code search)
- **LOW (<70%):** Best-effort check (doc coverage estimation, complexity heuristics)

Formát v reportu: `| Finding | Severity | Confidence | Detail |`

### 7.6) Process Map Freshness validation

Ověř existenci a kvalitu process map dokumentace:

```bash
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
TODAY_EPOCH=$(date +%s)
PROCESS_MAP_FINDINGS=""

# Kontrola existence process-map.md
if [ ! -f "$PROCESS_MAP" ]; then
  # Process map chybí — kritické jen pokud je projekt za Sprint 1
  CURRENT_SPRINT=$(grep '^sprint:' {WORK_ROOT}/state.md 2>/dev/null | awk '{print $2}')
  CURRENT_SPRINT=${CURRENT_SPRINT:-1}
  if [ "$CURRENT_SPRINT" -gt 1 ]; then
    echo "CRITICAL: process-map.md is missing (Sprint ${CURRENT_SPRINT} > 1)"
    PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **CRITICAL:** Process map chybí (Sprint ${CURRENT_SPRINT} > 1) → intake: process-map-missing"
  else
    echo "INFO: process-map.md doesn't exist yet (Sprint 1)"
  fi
else
  # Kontrola freshness (updated field)
  UPDATED=$(grep '^updated:' "$PROCESS_MAP" | awk '{print $2}')
  if [ -n "$UPDATED" ]; then
    UPDATED_EPOCH=$(date -d "$UPDATED" +%s 2>/dev/null || echo 0)
    DAYS_OLD=$(( (TODAY_EPOCH - UPDATED_EPOCH) / 86400 ))
    if [ "$DAYS_OLD" -gt 7 ]; then
      echo "WARN: process-map.md is ${DAYS_OLD}d old (>7d stale)"
      PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **HIGH:** Process map stale (${DAYS_OLD}d old) → intake: process-map-stale"
    else
      echo "PASS: process-map.md is fresh (${DAYS_OLD}d old)"
    fi
  else
    echo "WARN: process-map.md missing 'updated:' field"
    PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **MEDIUM:** Process map missing updated field"
  fi

  # Kontrola orphan count (UNIMPLEMENTED/ORPHAN markers)
  ORPHAN_COUNT=$(grep -c 'UNIMPLEMENTED\|ORPHAN' "$PROCESS_MAP" 2>/dev/null || echo 0)
  if [ "$ORPHAN_COUNT" -gt 0 ]; then
    echo "INFO: process-map.md has $ORPHAN_COUNT orphan/unimplemented entries"
    PROCESS_MAP_FINDINGS="${PROCESS_MAP_FINDINGS}
- **INFO:** Process map contains ${ORPHAN_COUNT} UNIMPLEMENTED/ORPHAN entries"
  fi
fi
```

Výstupy:
- Pokud `process-map.md` neexistuje a `state.sprint > 1` → vytvoř intake item `intake/check-process-map-missing.md`, reportuj **CRITICAL**
- Pokud `process-map.md` existuje ale `updated` je >7 dní starý → vytvoř intake item `intake/check-process-map-stale.md`, reportuj **HIGH**
- Pokud `process-map.md` má >0 UNIMPLEMENTED/ORPHAN → zaznamenej do reportu jako INFO (orientační)
- Přílož `$PROCESS_MAP_FINDINGS` do audit reportu

### 8) Vygeneruj audit report

Vytvoř `{WORK_ROOT}/reports/check-{YYYY-MM-DD}.md` dle `{WORK_ROOT}/templates/audit-report.md`:
- summary + score
- CRITICAL/WARNING findings
- auto-fixes
- intake items created

---

## Scoring (doporučené)

- Start 100
- -30 za každý CRITICAL
- -10 za každý WARNING
- +5 pokud byly provedeny safe auto-fixes

---

## Self-check

- report existuje
- pokud byly auto-fixes, jsou popsány
- pro každý CRITICAL existuje intake item

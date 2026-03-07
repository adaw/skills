---
name: fabric-archive
description: "Archive completed work safely. Moves DONE backlog items from backlog/ to backlog/done/, creates immutable snapshots under archive/, and archives sprint plans and reports. Preserves provenance for audits without deleting history."
---

<!-- built from: builder-template -->

# fabric-archive — Archivace (immutable snapshots)

---

## §1 — Účel

Po uzavření sprintu archivuje completed work do immutable snapshots a čistí aktivní backlog.
Bez archivace by se backlog nahromadil a audit trail by byl neznatelný.

Skill:
- Přesunuje DONE backlog items ze `{WORK_ROOT}/backlog/` do `{WORK_ROOT}/backlog/done/`
- Vytváří imutabilní snapshoty do `{WORK_ROOT}/archive/backlog/`, `archive/sprints/`, `archive/reports/`
- Archivuje sprint plány a klíčové reporty
- **Nezmaž historii** — vše zůstává dostupné pro audity a provenance tracking

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "archive" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "archive" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "archive" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

```bash
# K1: Phase validation — archive runs in closing only
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "closing" ]; then
  echo "STOP: fabric-archive requires phase=closing, current=$CURRENT_PHASE"
  exit 1
fi

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

# --- Precondition 3: Close report existuje ---
# K6: Dependency enforcement — close report MUST exist
CLOSE_REPORT=$(ls -t "{WORK_ROOT}/reports/close-"*.md 2>/dev/null | head -1)
if [ -z "$CLOSE_REPORT" ]; then
  echo "STOP: No close report found — fabric-close must run before fabric-archive"
  exit 1
fi

# --- Precondition 4: Backlog a archive struktura ---
[ ! -d "{WORK_ROOT}/backlog" ] && echo "STOP: backlog directory not found" && exit 1
mkdir -p "{WORK_ROOT}/archive/backlog" "{WORK_ROOT}/archive/sprints" "{WORK_ROOT}/archive/reports"
```

**Dependency chain:** `fabric-close` → [fabric-archive] → (archive complete, next sprint begins)

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md` (sprint N)
- `{WORK_ROOT}/backlog/*.md` (active items)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/sprints/sprint-{N}.md`
- `{WORK_ROOT}/reports/close-sprint-*.md`, `check-*.md`, `docs-*.md`, `prio-*.md`

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)
- Snapshoty: `{WORK_ROOT}/archive/backlog/{id}-{YYYY-MM-DD}.md` (immutable)

### Vedlejší (podmínečně)
- Sprint plan snapshot: `{WORK_ROOT}/archive/sprints/sprint-{N}-{YYYY-MM-DD}.md`
- Report snapshots: `{WORK_ROOT}/archive/reports/{report_name}-{YYYY-MM-DD}.md`
- Quarantine (konflikty): `{WORK_ROOT}/archive/quarantine/{id}-{YYYY-MM-DD}.md`
- Intake items: `{WORK_ROOT}/intake/archive-{slug}.md` (schema: `fabric.intake_item.v1`)

---

## §6 — Deterministic FAST PATH

Než začneš s archivací, spusť deterministické kroky:

```bash
python skills/fabric-init/tools/fabric.py archive-sprint > \
  "{WORK_ROOT}/reports/archive-sprint-{SPRINT_NUMBER}-{YYYY-MM-DD}.json"

# Kontrola výstupu — pokud ok=false, zapiš error do reportu a STOP
ARCHIVE_OK=$(jq -r '.ok' "{WORK_ROOT}/reports/archive-sprint-{SPRINT_NUMBER}-{YYYY-MM-DD}.json" 2>/dev/null)
if [ "$ARCHIVE_OK" != "true" ]; then
  echo "WARN: archive-sprint returned false — check JSON for details"
fi
```

---

## §7 — Postup (JÁDRO SKILLU)

Viz. `references/postup-detailed.md` pro implementační kroky. Zde je overview:

### 7.1) State Validation (K1)
Ověř že `phase: closing` v state.md — pokud ne, STOP.

### 7.2) Path Validation (K7)
Pro všechny dynamic paths: odmítni `..` (path traversal).

### 7.2.5) Counter Initialization (K2)
```bash
MAX_ITEMS_PER_ARCHIVE=${MAX_ITEMS_PER_ARCHIVE:-1000}
ARCHIVE_COUNTER=0

# K2: Numeric validation
if ! echo "$MAX_ITEMS_PER_ARCHIVE" | grep -qE '^[0-9]+$'; then
  MAX_ITEMS_PER_ARCHIVE=1000
  echo "WARN: MAX_ITEMS_PER_ARCHIVE not numeric, reset to default (1000)"
fi

# K5: Read from config.md
CONFIG_MAX=$(grep 'ARCHIVE.max_items_per_run:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
MAX_ITEMS_PER_ARCHIVE=${CONFIG_MAX:-$MAX_ITEMS_PER_ARCHIVE}
RETENTION_DAYS=$(grep 'ARCHIVE.retention_days:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
RETENTION_DAYS=${RETENTION_DAYS:-365}
```

### 7.3) Najdi DONE backlog items
Iteruj `{WORK_ROOT}/backlog/*.md`, vyber ty s `status: DONE` a `merge_commit` != null.
Max items per run z config.md: `ARCHIVE.max_items_per_run` (default: 1000). Retention days: `ARCHIVE.retention_days` (default: 365).

### 7.4) Přesuň DONE items do backlog/done/
Safe move pattern: `cp → diff → rm`. Pokud conflict v backlog/done/, move to quarantine.

### 7.5) Snapshot do archive/backlog
Zkopíruj každý DONE item (po move) do `archive/backlog/{id}-{YYYY-MM-DD}.md`. Immutable.

### 7.6) Archivuj sprint plán a reporty
Copy `sprints/sprint-{N}.md` (sprint plan) a key reports (close-*.md, check-*.md, docs-*.md) do `archive/sprints/` a `archive/reports/`.

### 7.7) Archive report
Vytvoř `reports/archive-{YYYY-MM-DD}.md` s frontmatter a tabulkami:
- Moved items (Item ID | Status | Destination | Snapshot)
- Archived reports (Artifact | Source | Destination)

### K10: Inline Example — LLMem Sprint 3 Archive

**Input:** Sprint 3 close: 3 DONE items (task-b015, task-b012, epic-e003) with merge_commit evidence, close reports from previous sprint archived.
**Output:** 3 snapshots in archive/backlog/{id}-2026-03-06.md, sprint-3.md copied to archive/sprints/, close-sprint-3-*.md copied to archive/reports/, report showing 3 items moved, 0 conflicts, retention policy enforced.

### K10: Anti-patterns (s detekcí)
```bash
# A1: Archiving non-DONE items — Detection: grep -E 'status: (IN_PROGRESS|DESIGN|READY)' {WORK_ROOT}/backlog/done/*.md
# A2: Missing backlog/done/ destination on move — Detection: ls {WORK_ROOT}/archive/backlog/ | wc -l vs grep MOVED {report}
# A3: YAML frontmatter not preserved in snapshots — Detection: ! grep -q '^---$' {WORK_ROOT}/archive/backlog/*-{date}.md
# A4: Archiving without retention_days check — Detection: task age < config.md ARCHIVE.retention_days but archived anyway
```

---

## §8 — Quality Gates

Skill fabric-archive nemá programmatic quality gates (bash/test příkazy).
Kontroly jsou v self-check (§10).

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: archive
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# archive — Report {YYYY-MM-DD}

## Souhrn

{Počet itemů archivovaných, snapshots vytvořených, konfliktů}

## Přesunuté items

| Item ID | Destination | Snapshot |
|---------|-------------|----------|
| ... | backlog/done/... | archive/backlog/... |

## Archivované reporty

| Artifact | Destination |
|----------|-------------|
| ... | archive/reports/... |

## Warnings

{Seznam nebo "žádné"}
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Archive snapshoty existují v `{WORK_ROOT}/archive/backlog/{id}-{date}.md`
- [ ] Sprint plan snapshot existuje (pokud byl na vstupu)
- [ ] Protocol log má START a END záznam

### Quality checks
- [ ] Report obsahuje povinné sekce: Souhrn, Přesunuté items, Archivované reporty
- [ ] DONE items jsou odstraněny z `{WORK_ROOT}/backlog/` (nejsou tam víc)
- [ ] Snapshoty mají identický obsah jako original items (diff -q verification)
- [ ] Všechny archivované itemy jsou zmíněny v reportu
- [ ] Žádné konflikty (quarantine je prázdný) nebo jsou intake items vytvořeny

### Invariants
- [ ] Jen DONE items jsou archivovány (status != DONE → nikdy do archive)
- [ ] State.md NENÍ modifikován (archive je read-only)
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl změněn
- [ ] Protocol log má START i END záznam

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí config/state | STOP + jasná zpráva |
| Phase Validation | phase != closing | STOP + zpráva o aktuální fázi |
| Item Discovery | 0 DONE items | OK status, report "0 items", END |
| Item Move | Copy verify selhala | ERROR + source preserved + intake |
| Item Move | Konflikt v done/ | WARN + move to quarantine + intake |
| Report | Write failure | ERROR + intake item |
| Self-check | Check FAIL | Report WARN + intake item |

Fail-open pro VOLITELNÉ vstupy (chybí reporty → WARNING).
Fail-fast pro POVINNÉ vstupy (chybí config → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
phase: closing
step: archive

may_modify_state: false       # archive je read-only k state
may_modify_backlog: true      # přesunuje items do backlog/done/
may_modify_code: false
may_create_intake: true

depends_on:
  - fabric-close

feeds_into:
  - fabric-sprint
```

---

## Anti-patterns (ZAKÁZÁNO)

- **A1: Archive active (non-DONE) items** — Nearchivuj s `status != DONE` — jen hotové položky se archivují
- **A2: Delete instead of move to archive/** — NESMÍ smazat; vždy kopíruj do `archive/` a pak teprve odstraň z aktivního backlog/
- **A3: Archive without preserving YAML frontmatter** — Snapshoty MUSÍ mít identické YAML; diff -q verifikace
- **A4: Skip quarantine for items with missing fields** — Konflikty MUSÍ jít do quarantine, ne přepisovat; intiake item pro každý konflikt
- **A5: Archive bez retention policy** — NESMÍ archivovat bez ověření retention_days z config.md. Příklad: LLMem task-b001 ze sprintu 1 (6 měsíců starý) — archivuj. Ale task-b015 ze sprintu 3 (tento týden) — NEPATŘÍ do archive, jen do backlog/done/.

---

## Acceptance Criteria (MINIMUM)

Archive MUSÍ obsahovat:
1. **Archive report** s YAML frontmatter (schema: `fabric.report.v1`)
2. **Snapshoty** v `archive/backlog/`, `archive/sprints/`, `archive/reports/`
3. **Moved items** — DONE items v `backlog/done/`, ne v `backlog/`
4. **Backlog cleanup** — archivované itemy se neobjeví v `backlog/`

Chybí-li kterýkoli bod → report WARN + intake item.

---

## K10 Fix: Archive Operation Example (LLMem Data)

```
Sprint 3 archival:
- task-b015, task-b012, epic-e003 → MOVED to backlog/done/
- 3 snapshots created in archive/backlog/{id}-2026-03-06.md
- sprint-3.md → COPIED to archive/sprints/sprint-3-2026-03-06.md
- close-sprint-3-*.md → COPIED to archive/reports/
- Report: archive-2026-03-06.md (3 items, 0 conflicts)
```

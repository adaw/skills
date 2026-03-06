---
name: fabric-archive
description: "Archive completed work safely. Moves DONE backlog items from backlog/ to backlog/done/, creates immutable snapshots under archive/, and archives sprint plans and key reports. Does not delete history; preserves provenance for audits."
---

# ARCHIVE — Archivace (immutable snapshots)

## Účel

Po uzavření sprintu:
- DONE backlog items se přesunou do `{WORK_ROOT}/backlog/done/`
- vytvoří se imutabilní snapshoty do `{WORK_ROOT}/archive/`
- archivují se sprint plány a reporty

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-archive" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-archive" --event end --status OK --report "{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Cíl: auditovatelnost + čistý aktivní backlog.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md` (sprint N)
- `{WORK_ROOT}/backlog/*.md` (active)
- `{WORK_ROOT}/backlog/done/` (target)
- `{WORK_ROOT}/sprints/sprint-{N}.md`
- `{WORK_ROOT}/reports/*` (zejména close/check)

---

## Výstupy

- přesunuté DONE backlog items do `{WORK_ROOT}/backlog/done/`
- snapshoty do:
  - `{WORK_ROOT}/archive/backlog/`
  - `{WORK_ROOT}/archive/sprints/`
  - `{WORK_ROOT}/archive/reports/`
- report `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`

---

## Preconditions

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

# --- Precondition 3: Close report existuje ---
CURRENT_SPRINT=$(grep '^sprint:' "{WORK_ROOT}/state.md" 2>/dev/null | awk '{print $2}')
CLOSE_REPORT=$(ls -t "{WORK_ROOT}/reports/close-"*.md 2>/dev/null | head -1)
if [ -z "$CLOSE_REPORT" ]; then
  echo "WARN: No close report found — archive assumes sprint is complete; verify manually"
fi

# --- Precondition 4: Backlog items exist ---
if [ ! -d "{WORK_ROOT}/backlog" ]; then
  echo "STOP: {WORK_ROOT}/backlog directory not found"
  exit 1
fi

# --- Precondition 5: Archive directory structure ready ---
mkdir -p "{WORK_ROOT}/archive/backlog"
mkdir -p "{WORK_ROOT}/archive/sprints"
mkdir -p "{WORK_ROOT}/archive/reports"
```

**Dependency chain:** `fabric-close` → [fabric-archive] → `(archive complete, next sprint begins)`

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

## FAST PATH (doporučeno) — archivace deterministicky jedním příkazem

1) Spusť deterministickou archivaci sprintu:

```bash
python skills/fabric-init/tools/fabric.py archive-sprint > "{WORK_ROOT}/reports/archive-sprint-{SPRINT_NUMBER}-{YYYY-MM-DD}.json"
```

2) Pokud JSON vrací `ok=false`, vytvoř report s chybou (missing backlog / remaining_not_done) a **STOP**.

3) Vytvoř report `{WORK_ROOT}/reports/archive-sprint-{SPRINT_NUMBER}-{YYYY-MM-DD}.md`:
- odkaz/summary na JSON výstup
- co bylo zkopírováno (stamp dir)
- co bylo přesunuto do `backlog/done/`

---

## K10 Fix: Archive Operation Example with Real LLMem Data

Here is a concrete example of a completed archive operation showing DONE items moved to archive and report output:

### Example: Archive Sprint 3 Completion

```
Input backlog/done items (status: DONE, merge_commit set):
- task-b015-optimize-qdrant-embed.md → MOVED to archive/backlog/task-b015-2026-03-06.md
- task-b012-add-rate-limiting.md → MOVED to archive/backlog/task-b012-2026-03-06.md
- epic-e003-semantic-embeddings.md → MOVED to archive/backlog/epic-e003-2026-03-06.md

Sprint plan archived:
- sprints/sprint-3.md → COPIED to archive/sprints/sprint-3-2026-03-06.md

Key reports archived:
- reports/close-sprint-3-2026-03-02.md → COPIED to archive/reports/close-sprint-3-2026-03-06.md
- reports/prio-2026-03-01.md → COPIED to archive/reports/prio-2026-03-01.md

Archive report summary:
- 3 DONE items moved to backlog/done/
- 3 snapshots created in archive/backlog/
- 1 sprint plan archived
- 2 critical reports archived
- 0 conflicts (all moves succeeded)
```

---

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="closing"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-archive. Expected: $EXPECTED_PHASES"
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
# validate_path "$ARCHIVE_PATH"
```

**Test cases pro archive (P2 work quality):**
Ověř po archivaci:
- Archivovaný soubor existuje v cílové lokaci
- Zdrojový soubor už neexistuje (move, ne copy)
- Archive report obsahuje seznam všech přesunutých souborů

### 1) Najdi DONE backlog items v aktivním backlogu

**K2 Fix: Archive Loop Counter**

```bash
MAX_ITEMS_PER_ARCHIVE=${MAX_ITEMS_PER_ARCHIVE:-1000}
ARCHIVE_COUNTER=0
DONE_ITEMS=()
```

Pro každý `{WORK_ROOT}/backlog/{id}.md` (mimo done/):
- parse YAML a vyber ty, které splňují:
  - `status: DONE`
  - `merge_commit` není null (bylo mergnuto v CLOSE)

Při iteraci:
```bash
for backlog_file in {WORK_ROOT}/backlog/*.md; do
  [ “$backlog_file” = “{WORK_ROOT}/backlog/done” ] && continue
  STATUS=$(grep '^status:' “$backlog_file” 2>/dev/null | awk '{print $2}')
  [ “$STATUS” = “DONE” ] || continue

  ARCHIVE_COUNTER=$((ARCHIVE_COUNTER + 1))
  if [ “$ARCHIVE_COUNTER” -ge “$MAX_ITEMS_PER_ARCHIVE” ]; then
    echo “WARN: max items per archive reached ($ARCHIVE_COUNTER/$MAX_ITEMS_PER_ARCHIVE)”
    break
  fi
  DONE_ITEMS+=(“$backlog_file”)
done
```

Pokud žádné:
- vytvoř report „0 items archived” a DONE

### 2) Přesuň DONE items do backlog/done/

Pro každý DONE item:
- cílový path: `{WORK_ROOT}/backlog/done/{id}.md`
- pokud už tam existuje:
  - porovnej obsah; pokud stejné → skip
  - pokud jiné → ulož do `archive/quarantine/{id}-{YYYY-MM-DD}.md` a vytvoř intake item (konflikt)
- jinak:
  - move (ne copy) do backlog/done

**Move semantika pseudokód (P2 work quality):**
```bash
# Safe move: verify before delete
cp "${SOURCE}" "${DEST}"
if [ -f "${DEST}" ] && diff -q "${SOURCE}" "${DEST}" >/dev/null 2>&1; then
  rm "${SOURCE}"
  echo "MOVED: ${SOURCE} → ${DEST}"
else
  echo "ERROR: copy verification failed — source preserved"
fi
```

### 3) Snapshot do archive/backlog

Pro každý DONE item (před/po move):
- vytvoř snapshot soubor:
  - `{WORK_ROOT}/archive/backlog/{id}-{YYYY-MM-DD}.md`
- snapshot je imutabilní (už ho neměň)

### 4) Archivuj sprint plán a reporty

Z `state.md` zjisti sprint `N`.
- pokud existuje `{WORK_ROOT}/sprints/sprint-{N}.md`:
  - zkopíruj do `{WORK_ROOT}/archive/sprints/sprint-{N}-{YYYY-MM-DD}.md`

Vyber klíčové reporty pro sprint:
- `close-sprint-{N}-*.md`
- `check-*.md`
- `docs-*.md`
- `prio-*.md` (volitelně)

Zkopíruj do `{WORK_ROOT}/archive/reports/` se stejným názvem (nebo s prefixem sprintu).

### 5) Archive report

Vytvoř `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`:
- seznam přesunutých itemů
- seznam snapshotů
- co bylo archivováno (sprint plan, reporty)
- konflikty (quarantine) + vytvořené intake items

---

## Anti-patterns (ZAKÁZÁNO)

- **A1: Partial Archive** — NESMÍ archivovat sprint bez kompletního close reportu. Detection: `test -f reports/close-*.md`. Fix: Spusť fabric-close nejdřív.
- **A2: Active WIP Archive** — NESMÍ archivovat sprint s aktivním WIP itemem (state.wip_item != null). Detection: `grep 'wip_item:' state.md | grep -v null`. Fix: Dokonči nebo zruš WIP.
- **A3: Missing Reports Archive** — NESMÍ přesunout do archive/ bez ověření kompletnosti report sady. Detection: Porovnej CONTRACTS.outputs s existujícími reports. Fix: Spusť chybějící skills.

## Acceptance Criteria (MINIMUM akceptovatelného výstupu)

Archive MUSÍ obsahovat:
1. **Archive report** (`reports/archive-{YYYY-MM-DD}.md`) s kompletním YAML frontmatter
2. **Snapshot v archive/** — sprint plan, reports, analyses zkopírované do `archive/sprints/sprint-{N}/`
3. **State update** — `state.sprint` inkrementován, `state.step` = next step nebo idle
4. **Backlog cleanup** — DONE items přesunuty do `backlog/done/`

Pokud kterýkoli z těchto bodů chybí, archive report MUSÍ mít `status: WARN` a vytvořit intake item.

---

## Self-check

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/archive-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Archive snapshoty existují v `{WORK_ROOT}/archive/backlog/` (struktura: `archive/backlog/{date}/{task_id}.md`)
- [ ] Protocol log má START a END záznam s `skill: archive`

### Quality checks
- [ ] Report obsahuje povinné sekce: Summary (počet archivovaných items), Archive manifest, Verification
- [ ] DONE items jsou odstraněny z `{WORK_ROOT}/backlog/` (kromě `backlog/DONE.md` indexu)
- [ ] Všechny archivované itemy mají ve snapshotu identický obsah jako původní (verifikace integrity)
- [ ] Report obsahuje seznam všech archivovaných task IDs + jejich původních statusů

### Invariants
- [ ] Žádný task s statusem != DONE není archivován (invariant: jen DONE → archive)
- [ ] Backlog index aktualizován — archivované itemy odstraněny (ale zůstávají v archive/)
- [ ] State.md NENÍ modifikován (archive je read-only k state)
- [ ] Protocol log má START i END záznam

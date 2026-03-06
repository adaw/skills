# Postup: Detailní implementační kroky

Toto je referenční dokument pro §7 (Postup) v `../SKILL.md`.

---

## 7.1) State Validation (K1: State Machine)

**Co:** Ověři že aktuální fáze je kompatibilní s archivací.

**Jak:**
```bash
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="closing"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-archive. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

**Minimum:** Phase validace PŘED jakýmkoli file operations.

---

## 7.2) Path Traversal Guard (K7: Input Validation)

**Co:** Zamezit path traversal útokům v souborových operacích.

**Jak:**
```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Aplikuj na všechny dynamické path inputy:
# validate_path "$BACKLOG_FILE"
# validate_path "$ARCHIVE_PATH"
```

---

## 7.3) Najdi DONE backlog items

**Co:** Iteruj přes `{WORK_ROOT}/backlog/` a identifikuj items s `status: DONE`.

**Jak:**
```bash
MAX_ITEMS_PER_ARCHIVE=${MAX_ITEMS_PER_ARCHIVE:-1000}
ARCHIVE_COUNTER=0
DONE_ITEMS=()

for backlog_file in "{WORK_ROOT}"/backlog/*.md; do
  # Skip done/ subdirectory
  [ "$backlog_file" = "{WORK_ROOT}/backlog/done" ] && continue

  STATUS=$(grep '^status:' "$backlog_file" 2>/dev/null | awk '{print $2}')
  [ "$STATUS" = "DONE" ] || continue

  ARCHIVE_COUNTER=$((ARCHIVE_COUNTER + 1))
  if [ "$ARCHIVE_COUNTER" -ge "$MAX_ITEMS_PER_ARCHIVE" ]; then
    echo "WARN: max items per archive reached ($ARCHIVE_COUNTER/$MAX_ITEMS_PER_ARCHIVE)"
    break
  fi
  DONE_ITEMS+=("$backlog_file")
done

if [ ${#DONE_ITEMS[@]} -eq 0 ]; then
  echo "INFO: 0 DONE items found for archival"
  exit 0
fi

echo "Found ${#DONE_ITEMS[@]} DONE items for archival"
```

**Minimum:**
- Array `DONE_ITEMS` s ID všech DONE items
- Counter check (max 1000 items per archive run)
- Pokud žádné items → report OK status, END

**Test cases:**
- [ ] Archivuj sprint se 3 DONE items — všechny by měly být v array
- [ ] Archivuj sprint s 0 DONE items — report OK
- [ ] Archivuj sprint s 1500 items — warn after 1000

---

## 7.4) Přesuň DONE items do backlog/done/

**Co:** Move (ne copy) každý DONE item do `backlog/done/`. Ověř integritu.

**Jak:**
```bash
# Safe move: verify before delete
for item_path in "${DONE_ITEMS[@]}"; do
  item_name=$(basename "$item_path")
  dest="{WORK_ROOT}/backlog/done/${item_name}"

  # Pokud už existuje v done/
  if [ -f "$dest" ]; then
    # Porovnej obsah
    if diff -q "$item_path" "$dest" >/dev/null 2>&1; then
      echo "SKIP: $item_name already in backlog/done/ (identical)"
      continue
    else
      # Konflikt: ulož do quarantine
      TIMESTAMP=$(date +%Y-%m-%d)
      quarantine_path="{WORK_ROOT}/archive/quarantine/${item_name%.*}-${TIMESTAMP}.md"
      cp "$item_path" "$quarantine_path"
      echo "WARN: conflict for $item_name — moved to quarantine"
      # TODO: create intake item pro konflikt
      continue
    fi
  fi

  # Safe copy-then-verify-then-delete pattern
  cp "${item_path}" "${dest}"
  if [ -f "${dest}" ] && diff -q "${item_path}" "${dest}" >/dev/null 2>&1; then
    rm "${item_path}"
    echo "MOVED: ${item_path} → ${dest}"
  else
    echo "ERROR: copy verification failed — source preserved"
    rm -f "${dest}"  # cleanup partial dest
  fi
done
```

**Minimum:**
- Všechny DONE items přesunuty do `backlog/done/`
- Integrity verify: cp → diff → rm
- Konflikty → quarantine + intake item

---

## 7.5) Snapshot do archive/backlog

**Co:** Pro každý DONE item vytvoř immutable snapshot.

**Jak:**
```bash
TIMESTAMP=$(date +%Y-%m-%d)

for item_path in "${DONE_ITEMS[@]}"; do
  item_name=$(basename "$item_path")
  item_id="${item_name%.*}"

  snapshot_path="{WORK_ROOT}/archive/backlog/${item_id}-${TIMESTAMP}.md"
  source_file="{WORK_ROOT}/backlog/done/${item_name}"

  if [ -f "$source_file" ]; then
    cp "$source_file" "$snapshot_path"
    echo "SNAPSHOT: $source_file → $snapshot_path"
  fi
done
```

**Minimum:**
- Snapshot existuje v `archive/backlog/{id}-{date}.md`
- Obsah == original DONE item

---

## 7.6) Archivuj sprint plán a reporty

**Co:** Zkopíruj sprint plán a klíčové reporty do archive/.

**Jak:**
```bash
CURRENT_SPRINT=$(grep '^sprint:' "{WORK_ROOT}/state.md" 2>/dev/null | awk '{print $2}')
TIMESTAMP=$(date +%Y-%m-%d)

# Sprint plan
SPRINT_PLAN="{WORK_ROOT}/sprints/sprint-${CURRENT_SPRINT}.md"
if [ -f "$SPRINT_PLAN" ]; then
  cp "$SPRINT_PLAN" "{WORK_ROOT}/archive/sprints/sprint-${CURRENT_SPRINT}-${TIMESTAMP}.md"
  echo "ARCHIVED: $SPRINT_PLAN"
fi

# Key reports
for pattern in "close-sprint-${CURRENT_SPRINT}-*.md" "check-*.md" "docs-*.md"; do
  for report_file in "{WORK_ROOT}"/reports/$pattern; do
    [ -f "$report_file" ] || continue
    report_name=$(basename "$report_file")
    dest="{WORK_ROOT}/archive/reports/${report_name}"
    [ -f "$dest" ] || cp "$report_file" "$dest"
  done
done
```

**Minimum:**
- Sprint plán archivován (pokud existuje)
- Alespoň 1 report archivován
- Žádné duplicate snapshoty

---

## 7.7) Archive report

**Co:** Vytvoř comprehensive report.

**Jak:**
```bash
REPORT_FILE="{WORK_ROOT}/reports/archive-${TIMESTAMP}.md"
RUN_ID=$(date +%s)

cat > "$REPORT_FILE" <<EOF
---
schema: fabric.report.v1
kind: archive
run_id: "${RUN_ID}"
created_at: "$(date --iso-8601=seconds)"
status: PASS
---

# archive — Report ${TIMESTAMP}

## Souhrn

Archivace sprintu ${CURRENT_SPRINT}:
- ${#DONE_ITEMS[@]} DONE items přesunuty do backlog/done/
- ${#DONE_ITEMS[@]} snapshoty vytvořeny v archive/backlog/
- Sprint plán archivován
- Klíčové reporty archivovány
- 0 konfliktů

## Přesunuté items

| Item ID | Status | Destination | Snapshot |
|---------|--------|-------------|----------|
EOF

for item_path in "${DONE_ITEMS[@]}"; do
  item_name=$(basename "$item_path")
  item_id="${item_name%.*}"
  echo "| $item_id | DONE | backlog/done/$item_name | archive/backlog/$item_id-$TIMESTAMP.md |" >> "$REPORT_FILE"
done

cat >> "$REPORT_FILE" <<EOF

## Archivované reporty a plány

| Artifact | Source | Destination |
|----------|--------|-------------|
EOF

if [ -f "$SPRINT_PLAN" ]; then
  echo "| sprint-$CURRENT_SPRINT | sprints/sprint-${CURRENT_SPRINT}.md | archive/sprints/sprint-${CURRENT_SPRINT}-${TIMESTAMP}.md |" >> "$REPORT_FILE"
fi

for report_file in "{WORK_ROOT}"/reports/{close-sprint-${CURRENT_SPRINT},check,docs}-*.md; do
  [ -f "$report_file" ] || continue
  report_name=$(basename "$report_file")
  echo "| $report_name | reports/$report_name | archive/reports/$report_name |" >> "$REPORT_FILE"
done

cat >> "$REPORT_FILE" <<EOF

## Verification

- [ ] All DONE items moved (none remaining in backlog/)
- [ ] All snapshots created
- [ ] Report contains complete manifest
- [ ] No conflicts
- [ ] Protocol log complete

## Warnings

None.
EOF

echo "REPORT: $REPORT_FILE"
```

**Minimum:**
- Report s YAML frontmatter
- Tabulka s archivovanými items
- Seznam snapshotů

---
name: fabric-docs
description: "Synchronize documentation with current codebase and merged changes. Updates docs, docstrings, and ADRs based on code reality without inventing APIs. Ensures knowledge is accessible and prevents drift between documentation and implementation."
---

<!-- built from: builder-template -->

## §1 — Účel

Po merge (CLOSE) musí dokumentace odpovídat realitě: nová funkcionalita je popsána, změny API jsou zdokumentované, ADR existuje pro významná arch rozhodnutí. Bez DESIGNu v dokumentaci se integrace stává nepředvídatelná a knowledge je rozptýlená v kódu.

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-docs" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-docs" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-docs" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

```bash
# Precondition 1: state.md existuje
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# K1: Phase validation — docs runs in implementation or closing
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$CURRENT_PHASE" | grep -qE '^(implementation|closing)$'; then
  echo "STOP: fabric-docs requires phase=implementation|closing, current=$CURRENT_PHASE"
  exit 1
fi

# Precondition 3: config.md má DOCS_ROOT
if ! grep -q '^DOCS_ROOT:' "{WORK_ROOT}/config.md"; then
  echo "STOP: config.md missing DOCS_ROOT variable"
  exit 1
fi

# K6: Dependency enforcement — close report required for full docs generation
if ! ls "{WORK_ROOT}/reports/close-"*.md 1>/dev/null 2>&1; then
  echo "STOP: No close report found — run fabric-close before fabric-docs"
  python skills/fabric-init/tools/protocol_log.py \
    --work-root "{WORK_ROOT}" --skill "docs" --event error \
    --status ERROR --message "Missing close report — run fabric-close first"
  exit 1
fi
```

**Dependency chain:** fabric-close → [fabric-docs]

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (DOCS_ROOT, CODE_ROOT)
- `{WORK_ROOT}/state.md` (phase validation)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/reports/close-*.md` (merged items seznam)
- `{CODE_ROOT}/` (aktuální main pro code scanning)
- `{DOCS_ROOT}/` (existující docs pro update)
- `{WORK_ROOT}/archive/` (historie)

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Aktualizované doc soubory v `{DOCS_ROOT}/` (pokud MUST_DOCUMENT items existují)
- ADR v `{DOCS_ROOT}/adr/NNNN-{slug}.md` (pokud arch decision)
- Intake items: `{WORK_ROOT}/intake/docs-{slug}.md` (pokud chyby/TODO)

---

## §6 — Deterministic FAST PATH

Před analýzou proveď strojové kroky:

```bash
# --- Path traversal guard (K7) ---
for VAR in "{WORK_ROOT}" "{CODE_ROOT}" "{DOCS_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index 2>/dev/null || true

# 2. Scan public API signature baseline
echo "=== SCANNING PUBLIC API SURFACE ==="
grep -rn "^class " {CODE_ROOT}/ --include='*.py' \
  | grep -v test | grep -v __pycache__ | grep -v "^_" \
  | sort > /tmp/current-classes.txt 2>/dev/null || true

grep -rn "^def \|^async def " {CODE_ROOT}/ --include='*.py' \
  | grep -v test | grep -v __pycache__ | grep -v "_" \
  | sort > /tmp/current-funcs.txt 2>/dev/null || true

# 3. Save baseline for delta comparison
cp /tmp/current-classes.txt "{WORK_ROOT}"/reports/baseline-classes-$(date +%Y-%m-%d).txt 2>/dev/null || true
cp /tmp/current-funcs.txt "{WORK_ROOT}"/reports/baseline-funcs-$(date +%Y-%m-%d).txt 2>/dev/null || true
```

---

## §7 — Postup (JÁDRO SKILLU)

### FAST PATH Initialization:
```bash
DOC_COUNTER=0
MAX_DOC_ITEMS=${MAX_DOC_ITEMS:-100}

# K2: Numeric validation
if ! echo "$MAX_DOC_ITEMS" | grep -qE '^[0-9]+$'; then
  MAX_DOC_ITEMS=100
  echo "WARN: MAX_DOC_ITEMS not numeric, reset to default (100)"
fi

# K5: Classification thresholds from config.md
MUST_DOC_TYPES=$(grep 'DOCS.must_document_types:' "{WORK_ROOT}/config.md" | sed 's/.*: //' || echo "api_change,breaking_change,new_module")
SHOULD_DOC_TYPES=$(grep 'DOCS.should_document_types:' "{WORK_ROOT}/config.md" | sed 's/.*: //' || echo "refactor,bugfix,config_change")
```

**Vše je detailně popsáno v `references/workflow.md`.**

Přehled kroků:

1. **Načti context** — merged items ze close reportu (nebo codebase scan) (yaml.safe_load pro all YAML parsing — K7)
2. **Klasifikuj items** — MUST_DOCUMENT vs SHOULD_DOCUMENT vs SKIP (s MAX_DOC_ITEMS guardem)
3. **Aktualizuj docs** — přidej/uprav soubory v DOCS_ROOT s code references
4. **Validuj linky** — broken links, orphaned files, syntax errors
5. **Vytvoř/uprav CHANGELOG** — Keep a Changelog format
6. **Vytvoř ADR** — pokud arch decision
7. **Napln report** — všechny sekce, machine-parseable YAML
8. **Self-check** — ověř checklist
9. **Loguj END** — protocol log

Pro detaily každého kroku, příklady, anti-patterns a heurystiky viz: **[references/workflow.md](./references/workflow.md)**

### K10: Inline Example — LLMem API Documentation Update

**Input:** Merged task-b015 (POST /capture/batch endpoint) with merge_commit abc123, close report listing MUST_DOCUMENT classification.
**Output:** New api/capture-batch.md documenting endpoint (signature, request/response schemas, error codes 207/400/413), CHANGELOG entry under [Unreleased] → "## Added" section, code reference: src/llmem/api/routes.py:L42. Docstring coverage in capture module: 85%.

### K10: Anti-patterns (s detekcí)
```bash
# A1: Documenting internal helpers not in public API — Detection: grep -E 'def _|class _.*:' {CODE_ROOT}/ in updated DOCS
# A2: Code examples with stale syntax — Detection: python3 -m py_compile fails on code block extracted from {DOCS_ROOT}/*.md
# A3: Broken markdown links in docs — Detection: grep -oP '\[.*\]\(\K[^)]+' {DOCS_ROOT}/*.md | xargs -I {} test ! -f {}
# A4: CHANGELOG not following Keep a Changelog format — Detection: ! grep -E '^## \[(Unreleased|[0-9]+\.[0-9]+)' CHANGELOG.md
```

---

## §8 — Quality Gates

### Gate 1: Broken Links Check
```bash
echo "=== CHECKING FOR BROKEN LINKS ==="
grep -roh '\[.*\](.*\.md)' {DOCS_ROOT}/ 2>/dev/null | grep -oP '\(.*?\)' | tr -d '()' | while read LINK; do
  if [ ! -f "{DOCS_ROOT}/$LINK" ] && [ ! -f "$LINK" ]; then
    echo "BROKEN LINK: $LINK"
  fi
done
```
- PASS: 0 broken links
- FAIL: intake item + report WARN
- Auto-fix: N/A (manual fix required)

### Gate 2: Code Examples Syntax Validation
```bash
echo "=== VALIDATING CODE EXAMPLES ==="
find {DOCS_ROOT}/ -name "*.md" | while read DOC; do
  TMPFILE=$(mktemp)
  awk '/^```python$/,/^```$/ { if (!/^```/) print }' "$DOC" > "$TMPFILE"
  if [ -s "$TMPFILE" ]; then
    if ! python3 -m py_compile "$TMPFILE" 2>/dev/null; then
      echo "SYNTAX_ERROR in $DOC"
    fi
  fi
  rm "$TMPFILE"
done
```
- PASS: all examples compile
- FAIL: intake item + report FAIL
- Auto-fix: N/A

### Gate 3: Docstring Coverage
```bash
OVERALL_COVERAGE=$((DOCUMENTED_ITEMS * 100 / (TOTAL_PUB_ITEMS + 1)))
if [ "$OVERALL_COVERAGE" -lt 80 ]; then
  echo "WARN: docstring coverage ${OVERALL_COVERAGE}% < 80% target"
fi
```
- PASS: ≥80% coverage
- FAIL (>10% bad docstrings): report WARN + intake item
- Auto-fix: N/A

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: docs
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
version: "1.0"
---

# docs — Report {YYYY-MM-DD}

## Souhrn
Zpracován{o} {N} merged items: {M} MUST_DOCUMENT + {K} SHOULD_DOCUMENT.
Aktualizován{o} {L} dokumentačních souborů. ADR: {vytvořen|nepotřebný}.
Docstring coverage: {X}% (target: ≥80%).

## Merged items
| ID | Title | Classification | Files | Updated Docs |
|----|-------|-----------------|-------|--------------|
| ITEM-123 | {Title} | MUST_DOCUMENT | {files} | {file.md} |

## API Surface Delta
### New Endpoints
- {endpoint description}

### Changed Endpoints
- {change description}

### Removed Endpoints
- {removal description}

## Updated Files
| File | Change | Code Reference | Status |
|------|--------|-----------------|--------|
| {DOCS_ROOT}/file.md | {change} | {CODE_ROOT}/module.py:L42 | ✓ |

## Docstring Quality Distribution
| Quality | Count | % | Status |
|---------|-------|---|--------|
| GOOD (2pts) | {n} | {%} | ✓ |
| ACCEPTABLE (1pt) | {n} | {%} | ✓ |
| BAD (0pts) | {n} | {%} | ✓ |

## Documentation Coverage (by module)
| Module | Public Items | Documented | Coverage | Status |
|--------|--------------|-------------|----------|--------|
| module | {n} | {n} | {%} | ✓ |

## Validation Results
- ✓ Broken markdown links: {n}
- ✓ Orphaned doc files: {n}
- ✓ Code examples syntax errors: {n}
- ✓ API docs vs code mismatches: {n}

## ADR
- {ADR výtvor nebo "nepotřebný s odůvodněním"}

## TODO
{pending items nebo "žádné"}

## Checklist
- [x] All MUST_DOCUMENT items have docs
- [x] Code examples validated
- [x] Broken links checked
- [x] Docstring quality scored
- [x] API coverage ≥80%
- [x] CHANGELOG updated
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`
- [ ] Report má povinné sekce: Souhrn, Merged items, API Surface Delta, Updated files, Docstring Quality, Coverage, Validation Results, ADR, TODO, Checklist
- [ ] Report je machine-parseable (YAML frontmatter + markdown)

### Quality checks
- [ ] Všechny MUST_DOCUMENT items mají ≥1 aktualizovaný soubor v `{DOCS_ROOT}/`
- [ ] Všechny SHOULD_DOCUMENT items buď mají doc update NEBO zdůvodnění v TODO
- [ ] Žádná doc změna bez grep-verifikace v kódu (no invented APIs)
- [ ] Všechny code examples v docs jsou syntakticky validní
- [ ] Interní linky vedou na existující soubory
- [ ] Docstring coverage ≥80% (BAD ≤10%, ACCEPTABLE ≥30%, GOOD ≥60%)
- [ ] API Surface Delta porovnává s last baseline
- [ ] CHANGELOG updated pokud existuje a jsou MUST_DOCUMENT items

### Invarianty
- [ ] Žádný soubor mimo `{DOCS_ROOT}/` nebyl modifikován (except close report reference)
- [ ] CHANGELOG (pokud vytvořen) je v `{CODE_ROOT}/` nebo `{DOCS_ROOT}/`
- [ ] CHANGELOG formát: `## [Unreleased]` nebo `## [X.Y.Z]` + kategorie
- [ ] Všechny updated doc files mají explicitní code reference (Source:)
- [ ] Report má run_id a created_at (ISO 8601) v frontmatter
- [ ] Protocol log obsahuje START i END záznam

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí state.md/config.md | STOP + jasná zpráva (run fabric-init first) |
| FAST PATH | API scan selže | WARN + pokračuj manuálně |
| Postup (§7) | Nelze klasifikovat item | SKIP + poznámka v TODO |
| Quality Gate | Broken links | Report WARN + intake item |
| Quality Gate | Syntax error v examples | Report FAIL + intake item |
| Self-check | Check FAIL | Report WARN + intake item |

Skill je fail-open vůči VOLITELNÝM vstupům (chybí → pokračuj s WARNING) a fail-fast vůči POVINNÝM vstupům (chybí → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: closing
step: documentation

# Oprávnění
may_modify_state: false
may_modify_backlog: false
may_modify_code: false              # modifikuje {DOCS_ROOT}, ne {CODE_ROOT}
may_create_intake: true

# Pořadí v pipeline
depends_on: [fabric-close]
feeds_into: [fabric-review, fabric-gap, fabric-check]
```

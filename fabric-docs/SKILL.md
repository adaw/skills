---
name: fabric-docs
description: "Synchronize documentation with the current codebase and recent merged changes. Updates {DOCS_ROOT}/ (and optionally in-code docstrings/README) based on code reality, adds/updates ADRs if needed, and writes a docs sync report. Never invent APIs that are not in code."
---

# DOCS — Dokumentace sync (code → docs)

## Účel

Po merge (CLOSE) musí dokumentace odpovídat realitě:
- nová funkcionalita je popsána,
- změny API jsou zdokumentované,
- ADR existuje pro významná arch rozhodnutí.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-docs" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-docs" --event end --status OK --report "{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).

`fabric-docs` je konzervativní: **nepřidává vymyšlené informace**.

## Preconditions — State & Phase Validation

**PŘED jakoukoli prací ověř:**

```bash
# 1. Verify state.md exists
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# 2. Verify phase: fabric-docs runs in implementation/closing phases
PHASE=$(grep -E '^phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if ! echo "$PHASE" | grep -qE '^(implementation|closing)$'; then
  echo "WARN: fabric-docs should run in implementation or closing phase, but phase='$PHASE' — continuing with caution"
fi

# 3. Verify config.md has DOCS_ROOT defined
if ! grep -q '^DOCS_ROOT:' "{WORK_ROOT}/config.md"; then
  echo "STOP: config.md missing DOCS_ROOT variable"
  exit 1
fi
```

---

## Downstream Contract (WQ7 fix)

**Which downstream skills read the docs report and what fields they consume:**

- **fabric-gap** reads:
  - `Documentation Coverage (by module)` table → columns: Module, Public Items, Documented, Coverage %
  - `Docstring Quality Distribution` → to warn if BAD items > 10% of public API
  - `CHANGELOG.md` status → whether user-facing changes are tracked

- **fabric-review** reads:
  - `API Surface Delta` section → New/Changed/Removed endpoints to validate against backlog
  - `Validation Results` section → Broken link count (must be 0)

---

## Git Safety (K4)

This skill does NOT perform git operations. K4 is N/A.

---

## Vstupy

- `{WORK_ROOT}/config.md` (DOCS_ROOT, CODE_ROOT)
- `{WORK_ROOT}/reports/close-sprint-*-*.md` (co se mergnulo)
- `{CODE_ROOT}/` (aktuální main)
- `{DOCS_ROOT}/` (existující docs)
- volitelně `{WORK_ROOT}/archive/` (historie)

---

## Výstupy

- aktualizované docs soubory v `{DOCS_ROOT}/`
- volitelně nové ADR v `{DOCS_ROOT}/adr/` (pokud projekt používá)
- report `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`

---

## Postup

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="closing"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-docs. Expected: $EXPECTED_PHASES"
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
# validate_path "$DOC_PATH"
```

### 1) Načti context

1. Otevři poslední `close` report a vylistuj:
   - merged items (ID + title)
   - změny chování / API (pokud jsou v reportu)
2. Pro každý merged item:
   - najdi backlog item (pro popis a AC)
   - najdi dotčené soubory (sekce „Dotčené soubory” nebo diff, pokud existuje)

**MINIMUM:** seznam ≥1 merged item(u) s ID, title, a dotčenými soubory

### K2 Fix: Loop Termination Guard

```bash
MAX_DOC_UPDATES=${MAX_DOC_UPDATES:-500}
DOC_UPDATE_COUNTER=0

# Validate MAX_DOC_UPDATES is numeric (K2 tight validation)
if ! echo "$MAX_DOC_UPDATES" | grep -qE '^[0-9]+$'; then
  MAX_DOC_UPDATES=500
  echo "WARN: MAX_DOC_UPDATES not numeric, reset to default (500)"
fi
```

When updating documentation files, add termination guard:
```bash
while read -r doc_file; do
  DOC_UPDATE_COUNTER=$((DOC_UPDATE_COUNTER + 1))

  # Numeric validation of counter (K2 strict check)
  if ! echo "$DOC_UPDATE_COUNTER" | grep -qE '^[0-9]+$'; then
    DOC_UPDATE_COUNTER=0
    echo "WARN: DOC_UPDATE_COUNTER corrupted, reset to 0"
  fi

  if [ "$DOC_UPDATE_COUNTER" -ge "$MAX_DOC_UPDATES" ]; then
    echo "WARN: max documentation updates reached ($DOC_UPDATE_COUNTER/$MAX_DOC_UPDATES)"
    break
  fi
  # ... process doc_file
done
```

### 1.1) Proaktivní code scanning (POVINNÉ)

Místo čekání na close report, AKTIVNĚ skenuj kód a najdi co v docs chybí. Spustit POVINNĚ:

```bash
#!/bin/bash
# Extract all public API signatures from current codebase
echo “=== SCANNING PUBLIC API SURFACE ===”
grep -rn “^class “ {CODE_ROOT}/ --include='*.py' \
  | grep -v test | grep -v __pycache__ | grep -v “^_” \
  | sort > /tmp/current-classes.txt

grep -rn “^def \|^async def “ {CODE_ROOT}/ --include='*.py' \
  | grep -v test | grep -v __pycache__ | grep -v “_” \
  | sort > /tmp/current-funcs.txt

# Save current scan as baseline for next time
cp /tmp/current-classes.txt {WORK_ROOT}/reports/baseline-classes-$(date +%Y-%m-%d).txt
cp /tmp/current-funcs.txt {WORK_ROOT}/reports/baseline-funcs-$(date +%Y-%m-%d).txt

# Detect signature changes: compare with last baseline
LAST_CLASSES=$(ls -t {WORK_ROOT}/reports/baseline-classes-*.txt 2>/dev/null | head -2 | tail -1)
if [ -n “$LAST_CLASSES” ]; then
  echo “Comparing with: $LAST_CLASSES”
  diff -u “$LAST_CLASSES” /tmp/current-classes.txt | grep '^[+-]' | grep -v '^[+-][+-]' > /tmp/class-changes.txt || true
  if [ -s /tmp/class-changes.txt ]; then
    echo “Class signature changes detected:”
    cat /tmp/class-changes.txt
  fi
fi

# Find undocumented public items
echo “=== SCANNING DOCSTRING COVERAGE ===”
TOTAL_PUB_ITEMS=0
DOCUMENTED_ITEMS=0
declare -A COVERAGE_BY_MODULE

for FILE in $(grep -h '^' /tmp/current-classes.txt /tmp/current-funcs.txt | cut -d: -f1 | sort -u); do
  ITEM_COUNT=$(grep “^$FILE:” /tmp/current-classes.txt /tmp/current-funcs.txt | wc -l)
  DOC_COUNT=0

  while IFS= read -r LINE; do
    LINENUM=$(echo “$LINE” | cut -d: -f2)
    NEXTLINE=$((LINENUM + 1))
    if sed -n “${NEXTLINE}p” “$FILE” 2>/dev/null | grep -qE '^\s+”””'; then
      DOC_COUNT=$((DOC_COUNT + 1))
    fi
  done < <(grep “^$FILE:” /tmp/current-classes.txt /tmp/current-funcs.txt)

  MODULE=$(echo “$FILE” | sed 's|{CODE_ROOT}/||' | sed 's|\.py||')
  COVERAGE_BY_MODULE[“$MODULE”]=”$DOC_COUNT/$ITEM_COUNT”
  TOTAL_PUB_ITEMS=$((TOTAL_PUB_ITEMS + ITEM_COUNT))
  DOCUMENTED_ITEMS=$((DOCUMENTED_ITEMS + DOC_COUNT))
done

OVERALL_COVERAGE=$((DOCUMENTED_ITEMS * 100 / (TOTAL_PUB_ITEMS + 1)))
echo “Overall docstring coverage: ${OVERALL_COVERAGE}% ($DOCUMENTED_ITEMS / $TOTAL_PUB_ITEMS)”
echo “By module:”
for MOD in “${!COVERAGE_BY_MODULE[@]}”; do
  echo “  $MOD: ${COVERAGE_BY_MODULE[$MOD]}”
done

# Detect undocumented items per module
echo “=== UNDOCUMENTED PUBLIC ITEMS ===”
while IFS= read -r LINE; do
  FILE=$(echo “$LINE” | cut -d: -f1)
  LINENUM=$(echo “$LINE” | cut -d: -f2)
  ITEM=$(echo “$LINE” | cut -d: -f3-)
  NEXTLINE=$((LINENUM + 1))
  if ! sed -n “${NEXTLINE}p” “$FILE” 2>/dev/null | grep -qE '^\s+”””'; then
    echo “UNDOCUMENTED: $FILE:$LINENUM — $ITEM”
  fi
done < <(cat /tmp/current-classes.txt /tmp/current-funcs.txt)

# Compare with docs to find missing documentation
echo “=== MISSING DOC FILES ===”
# For each public module, check if corresponding doc exists
for PYMOD in $(grep '^' /tmp/current-classes.txt /tmp/current-funcs.txt | cut -d: -f1 | sed 's|{CODE_ROOT}/||' | sed 's|\.py||' | sort -u); do
  DOCFILE=$(echo “$PYMOD” | sed 's|/|-|g')
  if [ ! -f “{DOCS_ROOT}/$DOCFILE.md” ] && [ ! -f “{DOCS_ROOT}/api/$DOCFILE.md” ]; then
    echo “MISSING DOC: $PYMOD (expected: {DOCS_ROOT}/$DOCFILE.md or {DOCS_ROOT}/api/$DOCFILE.md)”
  fi
done
```

**Výstup:**
- seznam class/function signature CHANGES od poslední baseline
- DOCSTRING COVERAGE % (target ≥80%)
- seznam UNDOCUMENTED public items (s file:line)
- seznam MISSING doc files
- module-by-module coverage breakdown

Použij jako DOPLNĚK ke close reportu (ne náhradu). Když najdeš undocumented items → přidej do TODO sekce reportu.

### 1.5) Filled-in example: LLMem docs report (WQ2 fix)

Here is a realistic docs sync example with actual LLMem data:

```markdown
---
schema: fabric.report.v1
kind: docs
run_id: “docs-2026-03-06-xyz789”
created_at: “2026-03-06T15:45:00Z”
status: PASS
version: “1.0”
---

# docs — Report 2026-03-06

## Souhrn
Zpracováno 8 merged items: 5 MUST_DOCUMENT + 3 SHOULD_DOCUMENT. Aktualizováno 6 dokumentačních souborů. ADR-005 vytvořen pro nový recall scoring. Docstring coverage 87% (target: ≥80%).

## API Surface Delta

### New Endpoints
- POST /memories/{instance_id} — Create memory directly (MUST_DOCUMENT)
- POST /memories/{instance_id}/{memory_id}/tombstone — Soft-delete memory (MUST_DOCUMENT)

### Changed Endpoints
- GET /recall — Added budget_tokens parameter (MUST_DOCUMENT)

### Docstring Quality Distribution
| Quality | Count | % | Status |
|---------|-------|---|--------|
| GOOD (2pts) | 32 | 68% | ✓ PASS |
| ACCEPTABLE (1pt) | 12 | 25% | ✓ PASS |
| BAD (0pts) | 3 | 7% | ✓ PASS |
| **Average Score** | — | **163%** | **✓ PASS** |

## Documentation Coverage (by module)
| Module | Public Items | Documented | Coverage | Status |
|--------|--------------|-------------|----------|--------|
| llmem.api.routes | 8 | 8 | 100% | ✓ |
| llmem.services | 12 | 11 | 92% | ✓ |
| llmem.triage | 6 | 5 | 83% | ⚠️ WARN |
| llmem.storage | 10 | 10 | 100% | ✓ |
| **TOTAL** | **36** | **34** | **94%** | **✓ PASS** |

## Validation Results
- ✓ Broken markdown links: 0
- ✓ Orphaned doc files: 0
- ✓ Code examples with syntax errors: 0
- ✓ API docs vs code mismatches: 0
```

### 2) Zjisti, co je „doc-worthy” (POVINNÉ pro KAŽDÝ item) — Anti-patterns with detection (WQ4 fix)

**Klasifikace je POVINNÁ – bez ní nelze skončit report.**

Rozhodovací strom (aplikuj SEKVENCIÁLNĚ):

```bash
#!/bin/bash
# Helper: Classify each merged item
classify_merged_item() {
  local ITEM_ID=”$1”
  local TITLE=”$2”
  local AFFECTED_FILES=”$3”  # newline-separated file paths

  # Check 1: API/public interface change?
  if echo “$AFFECTED_FILES” | grep -qE “api/|routes/|models\.py|config\.py”; then
    if echo “$AFFECTED_FILES” | grep -qvE “test_|__pycache__”; then
      echo “MUST_DOCUMENT”
      echo “  Reason: Public API surface change (endpoint/model/config)”
      return 0
    fi
  fi

  # Check 2: Breaking change? (removed endpoints, renamed params)
  if echo “$TITLE” | grep -qiE “remov|deprecat|break|break.*chang”; then
    echo “MUST_DOCUMENT”
    echo “  Reason: Breaking change detected”
    return 0
  fi

  # Check 3: Security-relevant?
  if echo “$TITLE” | grep -qiE “secret|auth|encrypt|password|token|api.?key|credential”; then
    echo “MUST_DOCUMENT”
    echo “  Reason: Security-relevant change”
    return 0
  fi

  # Check 4: Configuration change?
  if echo “$AFFECTED_FILES” | grep -qE “config\.py|\.env|settings”; then
    echo “MUST_DOCUMENT”
    echo “  Reason: Configuration change”
    return 0
  fi

  # Check 5: README or behavior affecting users?
  if echo “$AFFECTED_FILES” | grep -qE “README|setup\.py|requirements|Dockerfile|docker-compose”; then
    echo “MUST_DOCUMENT”
    echo “  Reason: User-facing infrastructure/setup change”
    return 0
  fi

  # Check 6: Performance/performance characteristic change?
  if echo “$TITLE” | grep -qiE “optim|perform|speed|latency|throughput|memory|cach”; then
    echo “SHOULD_DOCUMENT”
    echo “  Reason: Performance characteristic documented in README or perf guide”
    return 0
  fi

  # Check 7: Behavior change (not just refactor)?
  if echo “$TITLE” | grep -qiE “fix|chang.*behav|adjust|tuning|threshold”; then
    # But is it test-only or comment-only?
    if echo “$AFFECTED_FILES” | grep -qvE “test_|comments|docstrings”; then
      echo “SHOULD_DOCUMENT”
      echo “  Reason: Internal behavior change affecting integration”
      return 0
    fi
  fi

  # Check 8: Pure formatting/test-only/comment-only?
  if echo “$AFFECTED_FILES” | grep -qE “^test_|^_test\.py|\.pyc|__pycache__” \
     || echo “$TITLE” | grep -qiE “format|lint|typo|comment”; then
    if ! echo “$AFFECTED_FILES” | grep -qE “api/|routes/|models|config”; then
      echo “SKIP”
      echo “  Reason: Test-only or formatting change, no public API impact”
      return 0
    fi
  fi

  # Default: when in doubt, SHOULD_DOCUMENT
  echo “SHOULD_DOCUMENT”
  echo “  Reason: Unknown impact — erring on side of documentation”
}

# Example usage (call for each merged item):
# classify_merged_item “ITEM-123” “Add new memory recall endpoint” “src/llmem/api/routes/recall.py”
```

**Kategorie (mutually exclusive):**

1. **MUST_DOCUMENT** (pokud platí kterýkoli):
   - Nový/změněný/odstraněný veřejný endpoint, třída, CLI command
   - Breaking change (removed API, renamed parameter, signature change)
   - Bezpečnostní změna (secret handling, auth, encryption)
   - Konfigurace změna (nový env var, config soubor, default value)
   - User-facing infrastruktura (Docker, setup, install instrukce)

2. **SHOULD_DOCUMENT** (pokud platí):
   - Interní refactoring s dopadem na chování (ne jen rename)
   - Performance změna (s benchmarkem nebo charakteristikou)
   - Oprava behavior-bugu (ne jen linting)

3. **SKIP** (pokud platí VŠECHNY):
   - Čistě formatovací změny (kód vypadá stejně)
   - Jen testy (test-only files, fixtures)
   - Jen komentáře (docstring tweaks bez změny func chování)
   - Bez vlivu na veřejné API

**MINIMUM:** Pro KAŽDÝ merged item ve close reportu vytvoř řádek:

```
| {ID} | {Title} | MUST_DOCUMENT | {files} | {reason} |
```

Pokud je klasifikace nejasná → defaultuj SHOULD_DOCUMENT.

### 3) Aktualizuj docs (konzistentně s kódem)

- Přidávej odkazy na konkrétní moduly/entrypoints v `{CODE_ROOT}/`.
- Pokud existují README, aktualizuj je.
- Pokud projekt používá doc generator (MkDocs, Sphinx, Docusaurus), dodrž strukturu.

**Pravidlo:** Vždy ověř informaci v kódu nebo testech.

**MINIMUM:** Pro každý doc-worthy item ≥1 aktualizovaný soubor v `{DOCS_ROOT}/` s explicitní linkováním na code

#### 3.1) Validation & Link checking

Před tím, než dokončíš doc update, musí projít kontroly:

```bash
#!/bin/bash
# Validation: broken links in docs
echo "=== CHECKING FOR BROKEN LINKS ==="
grep -roh '\[.*\](.*\.md)' {DOCS_ROOT}/ 2>/dev/null | grep -oP '\(.*?\)' | tr -d '()' | while read LINK; do
  # Resolve relative link
  DOC_DIR=$(dirname "{DOCS_ROOT}/$LINK" 2>/dev/null | head -1)
  if [ ! -f "{DOCS_ROOT}/$LINK" ] && [ ! -f "$LINK" ]; then
    echo "BROKEN LINK: $LINK"
  fi
done

# Validation: orphaned doc files (not referenced anywhere)
echo "=== CHECKING FOR ORPHANED DOCS ==="
find {DOCS_ROOT}/ -name "*.md" -type f | while read DOC; do
  BASENAME=$(basename "$DOC" .md)
  if ! grep -r --include="*.md" "$BASENAME" {DOCS_ROOT}/ | grep -q "\.md)" && \
     [ "$DOC" != "{DOCS_ROOT}/README.md" ] && \
     [ "$DOC" != "{DOCS_ROOT}/index.md" ]; then
    echo "ORPHANED: $DOC (not referenced from other docs)"
  fi
done

# Validation: API docs match current code signatures
echo "=== CHECKING API DOCS vs CODE ==="
# Extract all endpoints from API docs
grep -roh "^###.*\`/.*\`" {DOCS_ROOT}/api/ 2>/dev/null | sort > /tmp/doc-endpoints.txt
# Extract all endpoints from code
grep -rn "@app\.\|@router\." {CODE_ROOT}/api/routes/ --include="*.py" 2>/dev/null \
  | grep -oP "(?<=['\"])/[^'\"]*" | sort > /tmp/code-endpoints.txt
# Diff
echo "Endpoints in docs but not in code:"
comm -23 /tmp/doc-endpoints.txt /tmp/code-endpoints.txt || true
echo "Endpoints in code but not in docs:"
comm -13 /tmp/doc-endpoints.txt /tmp/code-endpoints.txt || true
```

#### 3.2) Code example validation

Všechny code examples v docs musí být syntakticky správné:

```bash
#!/bin/bash
echo "=== VALIDATING CODE EXAMPLES ==="
# Extract Python code blocks from all docs
find {DOCS_ROOT}/ -name "*.md" | while read DOC; do
  TMPFILE=$(mktemp)
  # Extract Python code blocks: ```python ... ```
  awk '/^```python$/,/^```$/ { if (!/^```/) print }' "$DOC" > "$TMPFILE"

  if [ -s "$TMPFILE" ]; then
    if ! python3 -c "import ast; ast.parse(open('$TMPFILE').read())" 2>/dev/null; then
      echo "SYNTAX ERROR in $DOC:"
      python3 -m py_compile "$TMPFILE" 2>&1 | head -3
    fi
  fi
  rm "$TMPFILE"
done
```

#### 3.3) Docstring quality scoring

Každý public item musí splňovat kvalitu. Scoring:

| Quality | Definition | Points | Example |
|---------|-----------|--------|---------|
| BAD | `"""Capture."""` (1 slovo, bez Args/Returns) | 0 | Jedno slovo |
| ACCEPTABLE | `"""Capture an event and store memories."""` (1 věta, bez parametrů) | 1 | Popis cíle |
| GOOD | Full docstring: popis + Args + Returns + (Raises/Example) | 2 | Komplexní |

```bash
#!/bin/bash
echo "=== DOCSTRING QUALITY SCORING ==="
declare -A QUALITY_SCORES
QUALITY_SCORES[BAD]=0
QUALITY_SCORES[ACCEPTABLE]=1
QUALITY_SCORES[GOOD]=2

TOTAL_SCORE=0
TOTAL_COUNT=0

for FILE in $(find {CODE_ROOT}/ -name "*.py" | grep -v test | grep -v __pycache__); do
  while IFS= read -r LINE; do
    LINENUM=$(echo "$LINE" | cut -d: -f2)
    NEXTLINE=$((LINENUM + 1))
    DOCSTRING=$(sed -n "${NEXTLINE}p" "$FILE" 2>/dev/null)

    if [ -n "$DOCSTRING" ]; then
      # Count lines (longer = better)
      DOCLINES=$(echo "$DOCSTRING" | wc -l)

      # Check for Args, Returns, Raises
      COMPLETENESS=0
      echo "$DOCSTRING" | grep -q "Args:" && COMPLETENESS=$((COMPLETENESS + 1))
      echo "$DOCSTRING" | grep -q "Returns:" && COMPLETENESS=$((COMPLETENESS + 1))

      if [ "$DOCLINES" -gt 5 ] && [ "$COMPLETENESS" -ge 2 ]; then
        QUALITY="GOOD"
      elif [ "$DOCLINES" -gt 2 ]; then
        QUALITY="ACCEPTABLE"
      else
        QUALITY="BAD"
      fi

      SCORE=${QUALITY_SCORES[$QUALITY]}
      TOTAL_SCORE=$((TOTAL_SCORE + SCORE))
      TOTAL_COUNT=$((TOTAL_COUNT + 1))
    fi
  done < <(grep -n "^def \|^async def \|^class " "$FILE")
done

AVG_QUALITY=$((TOTAL_SCORE * 100 / (TOTAL_COUNT + 1)))
echo "Average docstring quality score: ${AVG_QUALITY}% ($TOTAL_SCORE / $TOTAL_COUNT)"
echo "Target: ≥150% (avg 1.5 points per item = ACCEPTABLE or better)"
```

#### 3.4) Dokumentační struktura: co musíš aktualizovat

Pro KAŽDÝ MUST_DOCUMENT item:
- Najdi odpovídající dokumentační soubor v `{DOCS_ROOT}/`
- Pokud neexistuje → vytvoř nový
- Aktualizuj s:
  - **Co:** Nová feature/API, změna konfigurace
  - **Kde:** Cesta v kódu s explicitním linkováním: `{CODE_ROOT}/{relative_path}` (EXAMPLE: `src/llmem/api/routes/recall.py`)
  - **Příklad:** Minimálně 1 runnable code example
  - **Parametry:** Pokud endpoint/func → popis ALL parametrů (povinné, typ, default)
  - **Zpět na kód:** Odkaz "Source:" na GitHub/dokonce — (EXAMPLE: `[RecallService.recall()](../../src/llmem/services/recall.py#L42)`)

**Anti-patterns with detection bash + fix procedures (WQ4):**

**Anti-pattern A: Undocumented public endpoint**
- Detection bash: `grep -rn '@app\.\|@router\.' {CODE_ROOT}/api/routes/ --include="*.py" | grep -oP "(?<=['\"])/[^'\"]*" | while read route; do if ! grep -q "$route" {DOCS_ROOT}/api/ 2>/dev/null; then echo "UNDOCUMENTED: $route"; fi; done`
- Fix procedure:
  1. For each undocumented route, create/update docs file in {DOCS_ROOT}/api/
  2. Include: endpoint path, HTTP method, request/response schema, example call
  3. Verify with grep: `grep -r "/recall" {DOCS_ROOT}/api/`

**Anti-pattern B: Code examples with outdated function signature**
- Detection bash: `find {DOCS_ROOT}/ -name "*.md" -exec grep -l '```python' {} \; | while read f; do awk '/^```python$/,/^```$/ { if (!/^```/) print }' "$f" > /tmp/code.py && python3 -m py_compile /tmp/code.py 2>/dev/null || echo "SYNTAX_ERROR: $f"; done`
- Fix procedure:
  1. Run examples through Python syntax checker
  2. Update function calls to match current API (check code for actual signatures)
  3. Test: re-run syntax check, should pass

**Anti-pattern C: Docstring quality = BAD (single word or no Args/Returns)**
- Detection bash: `find {CODE_ROOT} -name "*.py" | xargs grep -A2 '^def \|^class ' | grep -A1 '"""' | grep '"""' | grep -E '^\s+"""[^\"]{1,20}"""' | head -20`
- Fix procedure:
  1. For each BAD docstring (1-word like `"""Capture."""`), expand:
     - Add one sentence describing purpose
     - For functions with params, add Args: section
     - For functions with return, add Returns: section
  2. Target: minimum ACCEPTABLE (2+ sentences + Args + Returns for public functions)

**Anti-pattern D: Docs reference non-existent code locations**
- Detection bash: `grep -roh 'src/llmem/[^)]*\.py' {DOCS_ROOT}/ | sort -u | while read path; do if [ ! -f "{CODE_ROOT}/$path" ]; then echo "MISSING_FILE: $path"; fi; done`
- Fix procedure:
  1. Collect all referenced file paths from docs
  2. Verify each exists in CODE_ROOT
  3. Update stale paths or remove broken references

**Anti-pattern E: Missing MUST_DOCUMENT classification for breaking change**
- Detection bash: `grep -i 'remov\|deprecat\|break.*chang\|signature.*chang' {WORK_ROOT}/reports/close-sprint*.md | grep -v 'MUST_DOCUMENT' | head -10`
- Fix procedure:
  1. Find each breaking change in close report
  2. Ensure it's classified MUST_DOCUMENT
  3. Create/update corresponding doc file with migration guidance

### 4) CHANGELOG update (POVINNÉ pro VŠECHNY MUST_DOCUMENT items)

CHANGELOG je záznam o user-facing změnách. Pokud existuje, MUSÍ být aktualizován.

#### 4.1) CHANGELOG existence & format check

```bash
#!/bin/bash
# Check if CHANGELOG exists
if [ ! -f "{DOCS_ROOT}/CHANGELOG.md" ] && [ ! -f "{CODE_ROOT}/CHANGELOG.md" ]; then
  echo "CHANGELOG NOT FOUND"
  # If there are user-facing changes, this is an issue
  if grep -q "MUST_DOCUMENT" /tmp/classification-results.txt; then
    echo "⚠️ WARNING: No CHANGELOG but MUST_DOCUMENT items found. Create one or explain why N/A."
  fi
else
  CHANGELOG_FILE=$(find {DOCS_ROOT} {CODE_ROOT} -name "CHANGELOG.md" 2>/dev/null | head -1)
  echo "CHANGELOG found: $CHANGELOG_FILE"

  # Validate format: must follow Keep a Changelog format
  # https://keepachangelog.com/
  if ! grep -q "^## \[\(Unreleased\|[0-9]\)" "$CHANGELOG_FILE"; then
    echo "⚠️ WARNING: CHANGELOG format invalid. Expected '## [Unreleased]' or '## [version]'"
  fi

  # Check if current sprint has entry
  CURRENT_DATE=$(date +%Y-%m-%d)
  if ! grep -q "^## \[Unreleased\]" "$CHANGELOG_FILE"; then
    echo "⚠️ WARNING: No '[Unreleased]' section in CHANGELOG"
  fi
fi
```

#### 4.2) Entry template (Keep a Changelog format)

MUSÍ obsahovat:
- **[Unreleased]** sekcí (pro buggy/in-progress)
- **[version]** sekcí pro released (s datem ISO 8601)
- Kategorie: **Added**, **Changed**, **Fixed**, **Removed**, **Deprecated**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- New `/recall` endpoint for budgeted memory retrieval ([ITEM-42](link))
- Configuration option for secret sensitivity gating

### Changed
- Refactored `triage_event()` signature for better testability

### Fixed
- Bug in cosine similarity scoring for edge case embeddings

### Removed
- Deprecated `quick_recall()` method (use `recall()` instead)

## [0.2.0] — 2026-03-01

### Added
- Initial Qdrant backend support
```

#### 4.3) CHANGELOG enforcement

Pro KAŽDÝ merged item se MUST_DOCUMENT klasifikací:

```bash
#!/bin/bash
CHANGELOG_FILE=$(find {DOCS_ROOT} {CODE_ROOT} -name "CHANGELOG.md" 2>/dev/null | head -1)

# For each MUST_DOCUMENT item, check if it has CHANGELOG entry
echo "=== CHANGELOG VALIDATION ==="
while IFS='|' read -r ID TITLE CLASS REASON; do
  if [ "$CLASS" = "MUST_DOCUMENT" ]; then
    # Search for ID in CHANGELOG
    if grep -q "ITEM-$ID\|$ID" "$CHANGELOG_FILE"; then
      echo "✓ $ID: found in CHANGELOG"
    else
      echo "✗ $ID: MISSING from CHANGELOG"
    fi
  fi
done
```

**Pokud CHANGELOG neexistuje:**
- Pokud merged items obsahují MUST_DOCUMENT změny → vytvoř `CHANGELOG.md` s [Unreleased] sek
- Pokud jen SHOULD_DOCUMENT → můžeš vytvořit intake item `intake/docs-create-changelog.md` (optional)

### 5) ADR decisions (pokud došlo k arch/design změně)

**ADR (Architecture Decision Record) vytvoř POVINNĚ pokud:**
- Nové architecture komponenty (storage, cache, queue)
- Změna public API kontraktu (breaking changes)
- Nový subsystém s budoucím dopadem (auth, logging, monitoring)
- Deprecace či sunset feature
- Cross-cutting concern (bezpečnost, performance, compliance)

**Nevytvářej ADR pokud:**
- Čistě interní refactor bez dopadem na API
- Bugfix bez budoucího dopadem
- Testovací změny

#### 5.1) ADR decision tree

```bash
#!/bin/bash
# Decide if ADR is needed
declare -a MUST_DECIDE=(
  "nový storage backend"
  "breaking API change"
  "nový subsystém"
  "deprecace"
  "cross-cutting concern"
)

adr_decision_needed() {
  local TITLE="$1"

  for KEYWORD in "${MUST_DECIDE[@]}"; do
    if echo "$TITLE" | grep -qiE "$KEYWORD"; then
      echo "YES"
      return 0
    fi
  done

  # Check against merged changes
  if grep -qiE "architecture|design|refactor|auth|encrypt|storage" <<< "$TITLE"; then
    # Might need ADR—check code for scope
    if echo "$TITLE" | grep -qE "^(Add|Implement) "; then
      echo "PROBABLY"
      return 0
    fi
  fi

  echo "NO"
}

# Usage
RESULT=$(adr_decision_needed "$MERGED_ITEM_TITLE")
echo "ADR needed: $RESULT"
```

#### 5.2) ADR template

Umístit v `{DOCS_ROOT}/adr/NNNN-{slug}.md`:

```markdown
# ADR-NNNN: {Title}

**Date:** {YYYY-MM-DD}
**Status:** {Proposed|Accepted|Deprecated|Superseded}
**Author:** {name}

## Context

{Jaký problem řešíme? Jaké jsou business/technical drivers?}

## Decision

{Co jsme se rozhodli dělat?}

## Rationale

{Proč jsme si vybrali toto řešení místo alternativ?}
{Jaké jsou trade-offs?}

## Consequences

### Positive
- {benefit 1}
- {benefit 2}

### Negative
- {cost 1}
- {cost 2}

## Alternatives Considered

1. **{Alternative A}**
   - Pros: ...
   - Cons: ...

2. **{Alternative B}**
   - Pros: ...
   - Cons: ...

## Related ADRs
- [ADR-001: ...](./0001-example.md)
```

#### 5.3) ADR validation

```bash
#!/bin/bash
echo "=== ADR VALIDATION ==="
find {DOCS_ROOT}/adr/ -name "*.md" 2>/dev/null | while read ADR; do
  # Check for required fields
  for FIELD in "Status:" "Context" "Decision" "Consequences"; do
    if ! grep -q "$FIELD" "$ADR"; then
      echo "⚠️ WARNING: Missing '$FIELD' in $ADR"
    fi
  done
done
```

### 6) Vytvoř docs report (POVINNĚ)

`{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`

Report MUSÍ obsahovat všechny sekce a být strojově parsovatelný.

**ENHANCED report obsah:**

#### 6.1) API Surface Delta

Detekuj všechny změny v public API (nové/změněné/odstraněné endpoints a functions):

```bash
#!/bin/bash
echo "=== API SURFACE DELTA ANALYSIS ==="

# Extract current public endpoints
grep -rn "@app\|@router" {CODE_ROOT}/api/ --include="*.py" \
  | grep -oP "(?<=['\"])/[^'\"]*" \
  | sort > /tmp/current-endpoints.txt

# Extract current public functions from models/services
grep -rn "^def \|^async def " {CODE_ROOT}/ --include="*.py" \
  | grep -v "^_" | grep -v test | grep -v __pycache__ \
  | sort > /tmp/current-functions.txt

# Load previous baseline if exists
LAST_BASELINE=$(ls -t {WORK_ROOT}/reports/baseline-endpoints-*.txt 2>/dev/null | head -1)
if [ -n "$LAST_BASELINE" ]; then
  echo "API CHANGES (since last report):"
  echo "New endpoints:"
  comm -23 /tmp/current-endpoints.txt "$LAST_BASELINE" | head -10
  echo "Removed endpoints:"
  comm -13 /tmp/current-endpoints.txt "$LAST_BASELINE" | head -10
else
  echo "No previous baseline found (first run)"
fi

# Save current as new baseline
cp /tmp/current-endpoints.txt {WORK_ROOT}/reports/baseline-endpoints-$(date +%Y-%m-%d).txt
```

#### 6.2) Docstring quality distribution

Výstup z sekce 3.3 (quality scoring):

```
| Quality | Count | % | Target |
|---------|-------|---|--------|
| GOOD (2pts) | {count} | {pct}% | ≥60% |
| ACCEPTABLE (1pt) | {count} | {pct}% | ≥30% |
| BAD (0pts) | {count} | {pct}% | ≤10% |
| AVERAGE SCORE | — | {avg}% | ≥150% |
```

#### 6.3) Documentation coverage per module

```
| Module | Public Items | Documented | Coverage | Status |
|--------|--------------|-------------|----------|--------|
| llmem.api.routes | 12 | 11 | 92% | ✓ |
| llmem.services | 8 | 7 | 88% | ✓ |
| llmem.triage | 5 | 3 | 60% | ⚠️ |
```

#### 6.4) Validation results (broken links, examples, etc.)

```
- Broken markdown links: 0
- Orphaned doc files: 0
- Code examples with syntax errors: 0
- API docs vs code mismatches: 0
```

#### 6.5) Enhanced report template

```markdown
---
schema: fabric.report.v1
kind: docs
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
version: "1.0"                                    # WQ9 fix: track report schema version
status: {PASS|WARN|FAIL}                         # WQ10 fix: coverage <80% or MUST_DOCUMENT undocumented → FAIL
---

# docs — Report {YYYY-MM-DD}

## Souhrn
Zpracován{o} {N} merged items: {M} MUST_DOCUMENT + {K} SHOULD_DOCUMENT.
Aktualizován{o} {L} dokumentačních souborů.
ADR: {vytvořen|nepotřebný}.

## Merged items
| ID | Title | Classification | Files Changed | Updated Docs |
|----|-------|-----------------|----------------|--------------|
| ITEM-123 | Add recall API | MUST_DOCUMENT | api/routes/recall.py (42 lines) | api/recall.md |
| ITEM-124 | Refactor triage | SHOULD_DOCUMENT | services/triage.py (120 lines) | — |

## API Surface Delta
### New Endpoints
- POST /recall (with query params: scope, budget)

### Changed Endpoints
- GET /memories (added: filter_type parameter)

### Removed Endpoints
- DELETE /old-memory (deprecated in ITEM-119)

## Updated Files

<!--
EXAMPLE (LLMem project specifics — adapt to your codebase):
-->

| File | Change | Code Reference | Status |
|------|--------|-----------------|--------|
| {DOCS_ROOT}/api/recall.md | Added endpoint spec | {CODE_ROOT}/src/llmem/api/routes/recall.py:L42-L78 | ✓ |
| {DOCS_ROOT}/README.md | Added recall command | — | ✓ |
| CHANGELOG.md | Added [Unreleased] entries | — | ✓ |

## Docstring Quality Distribution
| Quality | Count | % | Status |
|---------|-------|---|--------|
| GOOD (2pts) | 24 | 65% | ✓ |
| ACCEPTABLE (1pt) | 10 | 27% | ✓ |
| BAD (0pts) | 3 | 8% | ✓ |
| **Average Score** | — | **158%** | **✓ PASS** |

## Documentation Coverage (by module)
| Module | Public Items | Documented | Coverage | Status |
|--------|--------------|-------------|----------|--------|
| llmem.api.routes | 5 | 5 | 100% | ✓ |
| llmem.services | 12 | 11 | 92% | ✓ |
| llmem.triage | 8 | 6 | 75% | ⚠️ WARN |
| **TOTAL** | **37** | **34** | **92%** | **✓ PASS** |

## Validation Results
- ✓ Broken markdown links: 0
- ✓ Orphaned doc files: 0
- ✓ Code examples with syntax errors: 0
- ✓ API docs vs code mismatches: 0

## Coverage Check
- Docstring coverage: 92% (target: ≥80%) — **PASS**
- README.md: Updated for new API — **OK**
- CHANGELOG.md: [Unreleased] entries added — **OK**

## ADR
- **ADR-005:** Created — New recall scoring mechanism ({DOCS_ROOT}/adr/0005-recall-scoring.md)

## TODO
{Pokud nic: "Žádné pending items"
 Pokud něco: "- ITEM-125: pondělí (čekám na AC clarity)"}

## Checklist (self-validation before submit)
- [x] All MUST_DOCUMENT items have updated docs (WQ10 fix: if any missing → **FAIL**)
- [x] Code examples validated for syntax (if any syntax errors → **FAIL**)
- [x] Broken links checked (if >0 broken links → **FAIL**)
- [x] Docstring quality scored (if coverage <80% → **FAIL**)
- [x] API coverage ≥80% (if <80% → **FAIL**)
- [x] CHANGELOG updated (if MUST_DOCUMENT items but no CHANGELOG entries → **FAIL**)
- [x] ADR created/not needed (with justification)
```

---

## Self-check (POVINNĚ před END)

### Existence checks (MUST ALL PASS)
- [ ] Report existuje: `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md`
- [ ] Report má všechny sekce: Souhrn, Merged items, API Surface Delta, Updated files, Docstring Quality, Coverage (module breakdown), Validation Results, ADR, TODO, Checklist
- [ ] Report je machine-parseable (YAML frontmatter + markdown structure)

### Quality checks (MUST ALL PASS)
- [ ] Všechny MUST_DOCUMENT items mají ≥1 aktualizovaný soubor v `{DOCS_ROOT}/`
- [ ] Všechny SHOULD_DOCUMENT items buď mají doc update NEBO zdůvodnění v TODO proč ne
- [ ] Žádná doc změna bez grep-verifikace v kódu (no invented APIs)
  - Ověření: `grep -n "def funkce_z_docu" {CODE_ROOT}/**/*.py`
- [ ] Všechny code examples v docs jsou syntakticky validní (python3 -m ast.parse)
- [ ] Interní linky (cross-references) vedou na existující soubory
  - Test: `for link in $(grep -roh '\(.*\.md\)' {DOCS_ROOT}/); do test -f "$link" || echo "BROKEN: $link"; done`
- [ ] Docstring coverage report runnable a přesný
  - Minimálně: `grep -rn '^def \|^class ' {CODE_ROOT}/ | wc -l` vs `. | grep -A1 '"""'`
- [ ] API Surface Delta porovnává s last baseline (ne s hardcoded expected)
- [ ] Žádné broken links v docs (ověřeno skriptem ze sekce 3.1)
- [ ] CHANGELOG updated pokud existuje a jsou MUST_DOCUMENT items
  - Pokud neexistuje a jsou MUST_DOCUMENT → vysvětleni v reportu

### Docstring quality (MUST MEET)
- [ ] Average docstring quality score ≥150% (target 1.5 points per item)
  - Bad items ≤10%, Acceptable ≥30%, Good ≥60%
- [ ] Všechny veřejné API mají ≥ ACCEPTABLE docstring (ne BAD)

### ADR validation (IF APPLICABLE)
- [ ] ADR created pokud měl být → je v `{DOCS_ROOT}/adr/` s číslem (NNNN-slug.md)
- [ ] ADR má povinné sekce: Context, Decision, Rationale, Consequences
- [ ] ADR status field je vyplněn (Proposed|Accepted|Deprecated|Superseded)
- [ ] Pokud ADR NOT NEEDED → report vysvětluje proč (ne jen "N/A")

### Invarianty (MUST ALL HOLD)
- [ ] Žádný soubor mimo `{DOCS_ROOT}/` nebyl modifikován (except close report reference)
- [ ] Pokud byl vytvořen CHANGELOG → je v `{CODE_ROOT}/` nebo `{DOCS_ROOT}/` (consistent location)
- [ ] CHANGELOG formát: `## [Unreleased]` nebo `## [X.Y.Z]` + kategorie (Added/Changed/Fixed/Removed)
- [ ] Všechny updated doc files mají explicitní code reference (Source: module.py:LineNN)
- [ ] Report má run_id a created_at (ISO 8601) v frontmatter
- [ ] Report status: PASS (vše OK), WARN (něco chybí ale ne kritické), FAIL (kritické chyby)

### Integration tests (RUN BEFORE SUBMIT)
```bash
#!/bin/bash
# Quick validation that report is complete
REPORT="{WORK_ROOT}/reports/docs-$(date +%Y-%m-%d).md"

if [ ! -f "$REPORT" ]; then
  echo "❌ REPORT NOT FOUND: $REPORT"
  exit 1
fi

# Check required sections
for SECTION in "Souhrn" "Merged items" "API Surface Delta" "Updated files" "Docstring Quality" "Coverage" "Validation Results" "ADR" "TODO" "Checklist"; do
  if ! grep -q "^## $SECTION\|^### $SECTION" "$REPORT"; then
    echo "❌ MISSING SECTION: $SECTION"
    exit 1
  fi
done

# Check frontmatter
if ! grep -q "^schema: fabric.report.v1" "$REPORT"; then
  echo "❌ INVALID FRONTMATTER"
  exit 1
fi

echo "✓ Report structure validated"

# Check that all MUST_DOCUMENT items have docs
UNDOCUMENTED=$(grep "MUST_DOCUMENT.*— *$\|MUST_DOCUMENT.*| —" "$REPORT" | wc -l)
if [ "$UNDOCUMENTED" -gt 0 ]; then
  echo "⚠️ WARNING: $UNDOCUMENTED MUST_DOCUMENT items without updated docs"
fi

echo "✓ All checks passed"
```

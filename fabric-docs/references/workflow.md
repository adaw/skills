# fabric-docs — Detailný workflow

Toto je komprehenzivní guide pro každý krok dokumentačního synchronizačního procesu.

---

## Krok 1: Načti context

### Co dělat
Sesbírej informace o tom, co se merglo: seznam merged items s ID, tituly, dotčené soubory, popisy AC.

### Jak to udělat kvalitně

**1a) Pokud existuje close report:**
1. Otevři poslední `{WORK_ROOT}/reports/close-*.md`
2. Vylistuj tabulku merged items (ID, title, files)
3. Pro každý item vypiš dotčené soubory (pokud v reportu jsou)

**Bash:**
```bash
CLOSE_REPORT=$(ls -t {WORK_ROOT}/reports/close-*.md 2>/dev/null | head -1)
if [ -n "$CLOSE_REPORT" ]; then
  echo "=== CLOSE REPORT: $CLOSE_REPORT ==="
  grep -A 100 "^| ITEM-\|^| TASK-" "$CLOSE_REPORT" | head -50
fi
```

**1b) Pokud close report neexistuje — spusť proaktivní code scanning:**
```bash
#!/bin/bash
# Extract all public API signatures from current codebase
echo "=== SCANNING PUBLIC API SURFACE ==="
grep -rn "^class " {CODE_ROOT}/ --include='*.py' \
  | grep -v test | grep -v __pycache__ | grep -v "^_" \
  | sort > /tmp/current-classes.txt

grep -rn "^def \|^async def " {CODE_ROOT}/ --include='*.py' \
  | grep -v test | grep -v __pycache__ | grep -v "_" \
  | sort > /tmp/current-funcs.txt

# Detect signature changes: compare with last baseline
LAST_CLASSES=$(ls -t {WORK_ROOT}/reports/baseline-classes-*.txt 2>/dev/null | head -2 | tail -1)
if [ -n "$LAST_CLASSES" ]; then
  echo "Comparing with: $LAST_CLASSES"
  diff -u "$LAST_CLASSES" /tmp/current-classes.txt | grep '^[+-]' | grep -v '^[+-][+-]' > /tmp/class-changes.txt || true
  if [ -s /tmp/class-changes.txt ]; then
    echo "Class signature changes detected:"
    cat /tmp/class-changes.txt
  fi
fi
```

### Minimum
- seznam ≥1 merged item(u) s ID, title, dotčenými soubory, popisem změny

---

## Krok 2: Klasifikuj merged items

### Co dělat
Každý merged item rozhodovacím stromem klasifikuj na MUST_DOCUMENT / SHOULD_DOCUMENT / SKIP. Bez klasifikace nelze skončit.

### Jak to udělat kvalitně

**Rozhodovací strom (aplikuj SEKVENCIÁLNĚ):**

```bash
#!/bin/bash
classify_merged_item() {
  local ITEM_ID="$1"
  local TITLE="$2"
  local AFFECTED_FILES="$3"  # newline-separated

  # Check 1: API/public interface change?
  if echo "$AFFECTED_FILES" | grep -qE "api/|routes/|models\.py|config\.py"; then
    if echo "$AFFECTED_FILES" | grep -qvE "test_|__pycache__"; then
      echo "MUST_DOCUMENT"
      echo "  Reason: Public API surface change (endpoint/model/config)"
      return 0
    fi
  fi

  # Check 2: Breaking change?
  if echo "$TITLE" | grep -qiE "remov|deprecat|break|break.*chang"; then
    echo "MUST_DOCUMENT"
    echo "  Reason: Breaking change detected"
    return 0
  fi

  # Check 3: Security-relevant?
  if echo "$TITLE" | grep -qiE "secret|auth|encrypt|password|token|api.?key|credential"; then
    echo "MUST_DOCUMENT"
    echo "  Reason: Security-relevant change"
    return 0
  fi

  # Check 4: Configuration change?
  if echo "$AFFECTED_FILES" | grep -qE "config\.py|\.env|settings"; then
    echo "MUST_DOCUMENT"
    echo "  Reason: Configuration change"
    return 0
  fi

  # Check 5: README or infrastructure?
  if echo "$AFFECTED_FILES" | grep -qE "README|setup\.py|requirements|Dockerfile|docker-compose"; then
    echo "MUST_DOCUMENT"
    echo "  Reason: User-facing infrastructure/setup change"
    return 0
  fi

  # Check 6: Performance change?
  if echo "$TITLE" | grep -qiE "optim|perform|speed|latency|throughput|memory|cach"; then
    echo "SHOULD_DOCUMENT"
    echo "  Reason: Performance characteristic"
    return 0
  fi

  # Check 7: Behavior change (not just refactor)?
  if echo "$TITLE" | grep -qiE "fix|chang.*behav|adjust|tuning|threshold"; then
    if echo "$AFFECTED_FILES" | grep -qvE "test_|comments|docstrings"; then
      echo "SHOULD_DOCUMENT"
      echo "  Reason: Internal behavior change"
      return 0
    fi
  fi

  # Check 8: Pure formatting/test-only?
  if echo "$AFFECTED_FILES" | grep -qE "^test_|^_test\.py|\.pyc|__pycache__" \
     || echo "$TITLE" | grep -qiE "format|lint|typo|comment"; then
    if ! echo "$AFFECTED_FILES" | grep -qE "api/|routes/|models|config"; then
      echo "SKIP"
      echo "  Reason: Test-only or formatting change"
      return 0
    fi
  fi

  # Default: when in doubt, SHOULD_DOCUMENT
  echo "SHOULD_DOCUMENT"
  echo "  Reason: Unknown impact — erring on side of documentation"
}
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

### Minimum
Pro KAŽDÝ merged item tabulka:
```
| ITEM-123 | Add new endpoint | MUST_DOCUMENT | api/routes/recall.py | api/recall.md |
```

### Anti-patterns (zakázáno)
- Klasifikovat bez bash ověření (vždycky spusť grep tree)
- Klasifikovat jako SKIP bez ověření absence API dopadem
- Klasifikovat bez odůvodnění (reason field je POVINNÝ)

---

## Krok 1.1: Proaktivní code scanning

### Co dělat
Aktivně skenuj kód a najdi co v docs chybí. Spustit POVINNĚ (doplněk ke close reportu).

### Jak to udělat kvalitně

Bash script ze sekce "FAST PATH" v SKILL.md + dodatečné analýzy:

```bash
#!/bin/bash
echo "=== DOCSTRING COVERAGE ANALYSIS ==="
TOTAL_PUB_ITEMS=0
DOCUMENTED_ITEMS=0
declare -A COVERAGE_BY_MODULE

for FILE in $(grep -h '^' /tmp/current-classes.txt /tmp/current-funcs.txt | cut -d: -f1 | sort -u); do
  ITEM_COUNT=$(grep "^$FILE:" /tmp/current-classes.txt /tmp/current-funcs.txt | wc -l)
  DOC_COUNT=0

  while IFS= read -r LINE; do
    LINENUM=$(echo "$LINE" | cut -d: -f2)
    NEXTLINE=$((LINENUM + 1))
    if sed -n "${NEXTLINE}p" "$FILE" 2>/dev/null | grep -qE '^\s+"""'; then
      DOC_COUNT=$((DOC_COUNT + 1))
    fi
  done < <(grep "^$FILE:" /tmp/current-classes.txt /tmp/current-funcs.txt)

  MODULE=$(echo "$FILE" | sed 's|{CODE_ROOT}/||' | sed 's|\.py||')
  COVERAGE_BY_MODULE["$MODULE"]="$DOC_COUNT/$ITEM_COUNT"
  TOTAL_PUB_ITEMS=$((TOTAL_PUB_ITEMS + ITEM_COUNT))
  DOCUMENTED_ITEMS=$((DOCUMENTED_ITEMS + DOC_COUNT))
done

OVERALL_COVERAGE=$((DOCUMENTED_ITEMS * 100 / (TOTAL_PUB_ITEMS + 1)))
echo "Overall docstring coverage: ${OVERALL_COVERAGE}% ($DOCUMENTED_ITEMS / $TOTAL_PUB_ITEMS)"
echo "By module:"
for MOD in "${!COVERAGE_BY_MODULE[@]}"; do
  echo "  $MOD: ${COVERAGE_BY_MODULE[$MOD]}"
done

# List undocumented items
echo "=== UNDOCUMENTED PUBLIC ITEMS ==="
while IFS= read -r LINE; do
  FILE=$(echo "$LINE" | cut -d: -f1)
  LINENUM=$(echo "$LINE" | cut -d: -f2)
  ITEM=$(echo "$LINE" | cut -d: -f3-)
  NEXTLINE=$((LINENUM + 1))
  if ! sed -n "${NEXTLINE}p" "$FILE" 2>/dev/null | grep -qE '^\s+"""'; then
    echo "UNDOCUMENTED: $FILE:$LINENUM — $ITEM"
  fi
done < <(cat /tmp/current-classes.txt /tmp/current-funcs.txt)

# Missing doc files
echo "=== MISSING DOC FILES ==="
for PYMOD in $(grep '^' /tmp/current-classes.txt /tmp/current-funcs.txt | cut -d: -f1 | sed 's|{CODE_ROOT}/||' | sed 's|\.py||' | sort -u); do
  DOCFILE=$(echo "$PYMOD" | sed 's|/|-|g')
  if [ ! -f "{DOCS_ROOT}/$DOCFILE.md" ] && [ ! -f "{DOCS_ROOT}/api/$DOCFILE.md" ]; then
    echo "MISSING DOC: $PYMOD (expected: {DOCS_ROOT}/$DOCFILE.md or {DOCS_ROOT}/api/$DOCFILE.md)"
  fi
done
```

### Minimum
- seznam class/function signature CHANGES
- DOCSTRING COVERAGE % (target ≥80%)
- seznam UNDOCUMENTED public items (file:line format)
- seznam MISSING doc files

### Anti-patterns
- Nepoužívat grep baseline (vždycky porovnávej s last baseline)
- Ignorovat malé undocumented items (každý veřejný item se počítá)

---

## Krok 3: Aktualizuj docs (konzistentně s kódem)

### Co dělat
Pro každý MUST_DOCUMENT item: najdi/vytvoř doc file v `{DOCS_ROOT}/`, aktualizuj s konkrétními parametry, příklady, kódem.

### Jak to udělat kvalitně

**3a) Pro každý MUST_DOCUMENT item:**

1. Identifikuj odpovídající doc file (nebo vytvoř nový)
2. Přidej/uprav tyto sekce:
   - **Co:** Nová feature/API, změna konfigurace
   - **Kde:** Cesta v kódu s explicitním linkováním: `{CODE_ROOT}/{relative_path}`
   - **Příklad:** Minimálně 1 runnable code example
   - **Parametry:** Pokud endpoint/func → popis ALL parametrů (povinné, typ, default)
   - **Zpět na kód:** Odkaz "Source:" na konkrétní řádek

**Příklad šablony:**
```markdown
## New Memory Endpoint

Create a memory directly.

**Source:** [RecallService.recall()](../../src/llmem/services/recall.py#L42)

### Request
```python
POST /memories/{instance_id}
Content-Type: application/json

{
  "content": "Important fact",
  "memory_type": "fact",
  "sensitivity": "public"
}
```

### Parameters
- `instance_id` (string, required): Instance identifier
- `content` (string, required): Memory content
- `memory_type` (MemoryType, required): Type of memory (fact|decision|observation)
- `sensitivity` (Sensitivity, optional): Default: public

### Response
```json
{
  "memory_id": "mem_xyz",
  "created_at": "2026-03-06T15:45:00Z"
}
```
```

**3b) Validation & Link checking:**

```bash
#!/bin/bash
echo "=== CHECKING FOR BROKEN LINKS ==="
grep -roh '\[.*\](.*\.md)' {DOCS_ROOT}/ 2>/dev/null | grep -oP '\(.*?\)' | tr -d '()' | while read LINK; do
  if [ ! -f "{DOCS_ROOT}/$LINK" ] && [ ! -f "$LINK" ]; then
    echo "BROKEN LINK: $LINK"
  fi
done

echo "=== CHECKING FOR ORPHANED DOCS ==="
find {DOCS_ROOT}/ -name "*.md" -type f | while read DOC; do
  BASENAME=$(basename "$DOC" .md)
  if ! grep -r --include="*.md" "$BASENAME" {DOCS_ROOT}/ | grep -q "\.md)" && \
     [ "$DOC" != "{DOCS_ROOT}/README.md" ] && \
     [ "$DOC" != "{DOCS_ROOT}/index.md" ]; then
    echo "ORPHANED: $DOC"
  fi
done

echo "=== CHECKING API DOCS vs CODE ==="
grep -roh "^###.*\`/.*\`" {DOCS_ROOT}/api/ 2>/dev/null | sort > /tmp/doc-endpoints.txt
grep -rn "@app\.\|@router\." {CODE_ROOT}/api/routes/ --include="*.py" 2>/dev/null \
  | grep -oP "(?<=['\"])/[^'\"]*" | sort > /tmp/code-endpoints.txt
echo "Endpoints in docs but not in code:"
comm -23 /tmp/doc-endpoints.txt /tmp/code-endpoints.txt || true
echo "Endpoints in code but not in docs:"
comm -13 /tmp/doc-endpoints.txt /tmp/code-endpoints.txt || true
```

### Minimum
- Pro každý MUST_DOCUMENT item ≥1 aktualizovaný doc soubor v `{DOCS_ROOT}/`
- Každý doc file má explicitní code reference (Source: module.py:L42)
- Všechny parametry jsou dokumentovány

### Anti-patterns (zakázáno)
- Dokumentovat vymyšlenou API (vždycky ověř v kódu: `grep -n "def funkce_z_docu" {CODE_ROOT}/**/*.py`)
- Zastat s broken linky (spusť link validation)
- Nechat undocumented parametry (all-or-nothing: všechny nebo žádné v příkladu)

---

## Krok 3.2: Docstring quality scoring

### Co dělat
Sesbírej a skóruj kvalitu docstringů ve veřejných API.

### Jak to udělat kvalitně

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
      DOCLINES=$(echo "$DOCSTRING" | wc -l)

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

**Quality definition:**
| Quality | Definition | Points | Example |
|---------|-----------|--------|---------|
| BAD | `"""Capture."""` (1 slovo, bez Args/Returns) | 0 | Jedno slovo |
| ACCEPTABLE | `"""Capture an event and store memories."""` (1 věta) | 1 | Popis cíle |
| GOOD | Full docstring: popis + Args + Returns + Raises/Example | 2 | Komplexní |

### Minimum
- Average score ≥150% (target 1.5 points per item)
- BAD ≤10%, ACCEPTABLE ≥30%, GOOD ≥60%

---

## Krok 3.2: Code example validation

### Co dělat
Všechny code examples v docs musí být syntakticky správné.

### Jak to udělat kvalitně

```bash
#!/bin/bash
echo "=== VALIDATING CODE EXAMPLES ==="
find {DOCS_ROOT}/ -name "*.md" | while read DOC; do
  TMPFILE=$(mktemp)
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

### Minimum
- 0 syntax errors v code examples

### Anti-patterns
- Ignorovat syntax errors (každý example se testuje)
- Nechat outdated function signatures (spusť validation)

---

## Krok 4: CHANGELOG update (POVINNÉ pro VŠECHNY MUST_DOCUMENT)

### Co dělat
CHANGELOG je záznam o user-facing změnách. Pokud existuje a jsou MUST_DOCUMENT items → MUSÍ být aktualizován.

### Jak to udělat kvalitně

**4a) Existence & format check:**

```bash
#!/bin/bash
if [ ! -f "{DOCS_ROOT}/CHANGELOG.md" ] && [ ! -f "{CODE_ROOT}/CHANGELOG.md" ]; then
  echo "CHANGELOG NOT FOUND"
  if grep -q "MUST_DOCUMENT" /tmp/classification-results.txt; then
    echo "⚠️ WARNING: No CHANGELOG but MUST_DOCUMENT items exist"
    echo "Create CHANGELOG.md or explain in report why N/A"
  fi
else
  CHANGELOG_FILE=$(find {DOCS_ROOT} {CODE_ROOT} -name "CHANGELOG.md" 2>/dev/null | head -1)

  # Validate format: Keep a Changelog
  if ! grep -q "^## \[\(Unreleased\|[0-9]\)" "$CHANGELOG_FILE"; then
    echo "⚠️ WARNING: CHANGELOG format invalid. Expected '## [Unreleased]' or '## [version]'"
  fi

  # Check for [Unreleased] section
  if ! grep -q "^## \[Unreleased\]" "$CHANGELOG_FILE"; then
    echo "⚠️ WARNING: No '[Unreleased]' section in CHANGELOG"
  fi
fi
```

**4b) Entry template (Keep a Changelog format):**

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

**4c) CHANGELOG enforcement (per item):**

```bash
#!/bin/bash
CHANGELOG_FILE=$(find {DOCS_ROOT} {CODE_ROOT} -name "CHANGELOG.md" 2>/dev/null | head -1)

echo "=== CHANGELOG VALIDATION ==="
while IFS='|' read -r ID TITLE CLASS REASON; do
  if [ "$CLASS" = "MUST_DOCUMENT" ]; then
    if grep -q "ITEM-$ID\|$ID" "$CHANGELOG_FILE"; then
      echo "✓ $ID: found in CHANGELOG"
    else
      echo "✗ $ID: MISSING from CHANGELOG"
    fi
  fi
done
```

### Minimum
- CHANGELOG existuje (pokud MUST_DOCUMENT items)
- Všechny MUST_DOCUMENT items jsou v [Unreleased] sekci
- Formát: Keep a Changelog (Added/Changed/Fixed/Removed kategorie)

### Anti-patterns
- Nechat CHANGELOG bez [Unreleased] sekce (intake item pro vytvoření)
- Ignorovat chybějící CHANGELOG (pokud MUST_DOCUMENT items → MUST create)

---

## Krok 5: ADR decisions (arch/design změny)

### Co dělat
Vytvoř ADR POVINNĚ pokud: nové storage komponenty, breaking API changes, nový subsystém, deprecace, cross-cutting concern.

### Jak to udělat kvalitně

**5a) Decision tree:**

```bash
adr_decision_needed() {
  local TITLE="$1"

  declare -a MUST_DECIDE=(
    "nový storage backend"
    "breaking API change"
    "nový subsystém"
    "deprecace"
    "cross-cutting concern"
  )

  for KEYWORD in "${MUST_DECIDE[@]}"; do
    if echo "$TITLE" | grep -qiE "$KEYWORD"; then
      echo "YES"
      return 0
    fi
  done

  if grep -qiE "architecture|design|refactor|auth|encrypt|storage" <<< "$TITLE"; then
    if echo "$TITLE" | grep -qE "^(Add|Implement) "; then
      echo "PROBABLY"
      return 0
    fi
  fi

  echo "NO"
}
```

**Nevytvářej ADR pokud:**
- Čistě interní refactor bez dopadem na API
- Bugfix bez budoucího dopadem
- Testovací změny

**5b) ADR template:**

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

**5c) ADR validation:**

```bash
#!/bin/bash
echo "=== ADR VALIDATION ==="
find {DOCS_ROOT}/adr/ -name "*.md" 2>/dev/null | while read ADR; do
  for FIELD in "Status:" "Context" "Decision" "Consequences"; do
    if ! grep -q "$FIELD" "$ADR"; then
      echo "⚠️ WARNING: Missing '$FIELD' in $ADR"
    fi
  done
done
```

### Minimum
- ADR vytvořen pokud arch decision (a v {DOCS_ROOT}/adr/ s číslem)
- Nebo: vysvětlení v reportu proč ADR NOT NEEDED

### Anti-patterns
- Vytvářet ADR bez povinných sekcí (Context, Decision, Rationale, Consequences)
- Ignorovat referenced ADRs v existing docs

---

## Krok 6: Report (template ze SKILL.md §9)

Vytvoř `{WORK_ROOT}/reports/docs-{YYYY-MM-DD}.md` se všemi sekcemi:
- Souhrn
- Merged items (tabulka)
- API Surface Delta
- Updated Files
- Docstring Quality
- Coverage by Module
- Validation Results
- ADR
- TODO
- Checklist

Viz SKILL.md §9 pro přesný format.

---

## Krok 7: Self-check (SKILL.md §10)

Povinné ověření před END:
- [ ] Report existuje
- [ ] Všech 10 sekcí je vyplněno
- [ ] Všechny MUST_DOCUMENT items mají docs
- [ ] Code examples validní
- [ ] Broken links = 0
- [ ] Docstring coverage ≥80%
- [ ] CHANGELOG updated (pokud relevantní)
- [ ] ADR vytvořen nebo zdůvodněn proč ne
- [ ] Protocol log START + END

---

## Anti-patterns s detekcí a fix procedurami

### Anti-pattern A: Undocumented public endpoint

**Detection:**
```bash
grep -rn '@app\.\|@router\.' {CODE_ROOT}/api/routes/ --include="*.py" | \
  grep -oP "(?<=['\"])/[^'\"]*" | while read route; do
  if ! grep -q "$route" {DOCS_ROOT}/api/ 2>/dev/null; then
    echo "UNDOCUMENTED: $route"
  fi
done
```

**Fix:**
1. For each undocumented route, create/update docs in {DOCS_ROOT}/api/
2. Include: endpoint path, HTTP method, request/response schema, example
3. Verify: `grep -r "/recall" {DOCS_ROOT}/api/`

### Anti-pattern B: Outdated function signature in examples

**Detection:**
```bash
find {DOCS_ROOT}/ -name "*.md" -exec grep -l '```python' {} \; | while read f; do
  awk '/^```python$/,/^```$/ { if (!/^```/) print }' "$f" > /tmp/code.py
  python3 -m py_compile /tmp/code.py 2>/dev/null || echo "SYNTAX_ERROR: $f"
done
```

**Fix:**
1. Run examples through Python syntax checker
2. Update function calls to match current API
3. Re-run syntax check

### Anti-pattern C: BAD docstring quality

**Detection:**
```bash
find {CODE_ROOT} -name "*.py" | xargs grep -A2 '^def \|^class ' | \
  grep -A1 '"""' | grep '"""' | grep -E '^\s+"""[^\"]{1,20}"""'
```

**Fix:**
1. For each BAD docstring, expand to ACCEPTABLE minimum:
   - One sentence describing purpose
   - For functions with params: add Args: section
   - For functions with return: add Returns: section

### Anti-pattern D: Docs reference non-existent code

**Detection:**
```bash
grep -roh 'src/llmem/[^)]*\.py' {DOCS_ROOT}/ | sort -u | while read path; do
  if [ ! -f "{CODE_ROOT}/$path" ]; then
    echo "MISSING_FILE: $path"
  fi
done
```

**Fix:**
1. Collect all referenced file paths from docs
2. Verify each exists in CODE_ROOT
3. Update stale paths or remove broken references

### Anti-pattern E: Missing MUST_DOCUMENT for breaking change

**Detection:**
```bash
grep -i 'remov\|deprecat\|break.*chang\|signature.*chang' {WORK_ROOT}/reports/close-sprint*.md | \
  grep -v 'MUST_DOCUMENT'
```

**Fix:**
1. Find each breaking change in close report
2. Ensure classified MUST_DOCUMENT
3. Create/update doc with migration guidance

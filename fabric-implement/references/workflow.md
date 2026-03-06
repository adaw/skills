# fabric-implement — Detailed Workflow & Coding Patterns

This document contains detailed implementation steps, coding patterns, anti-patterns, and complex validation logic referenced from main SKILL.md.

---

## Detailed Implementation Steps

### 1) State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="implementation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-implement. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### 2) Path Traversal Guard (K7: Input Validation)

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
validate_path "$TASK_FILE"
validate_path "$BRANCH_NAME"
```

### 3) Select Task (WIP=1)

1. Načti `state.md`.
2. Pokud `wip_item` je `null`:
   - otevři sprint plán a přečti tabulku `## Task Queue`
   - vyber první item v pořadí `Order`, který:
     - není `DONE`
     - má status `READY` (nebo `IN_PROGRESS` pokud jde o navázání)
   - nastav:
     - `state.wip_item = <id>`
     - `state.wip_branch = <branch>` (viz níže)
3. Pokud `wip_item` není `null`:
   - pokračuješ na tomtéž tasku (typicky rework po review)

> Implementace nikdy nesmí paralelně zpracovávat 2 tasks.

### 4) Prepare Branch (create nebo reuse)

1. Načti backlog item `{WORK_ROOT}/backlog/{id}.md` a zjisti `branch:`.
2. Pokud `branch` existuje → reuse.
3. Pokud `branch` neexistuje:
   - vymysli branch name:
     - default: `{id}-impl`
     - nebo podle `GIT.feature_branch_pattern` (pokud je definováno)
   - zapiš `branch:` do backlog itemu

#### Unicode Normalization (P2 fix)

Sanitize branch name before git checkout:

```bash
# Unicode normalization (P2 fix): sanitize branch name
# Remove all non-alphanumeric, dash, underscore, dot characters
branch_name=$(echo "${branch_name}" | LC_ALL=C sed 's/[^a-zA-Z0-9._-]/-/g' | sed 's/-*-/-/g' | sed 's/^-\|-$//')
```

#### Git Steps

```bash
# Branch causality: verify branch exists before checkout
if ! git rev-parse --verify "${WIP_BRANCH}" >/dev/null 2>&1; then
  echo "STOP: branch '${WIP_BRANCH}' does not exist — implement may have crashed before creating it"
  echo "  → Reset state.wip_branch and re-run implement"
  exit 1
fi

git status --porcelain
timeout 60 git fetch --all --prune || echo "WARN: git fetch failed/timeout (network?), continuing with local state"
git checkout "${main_branch}"
git pull --ff-only || echo "WARN: pull failed, using local main"
git checkout -b "${branch_name}" || git checkout "${branch_name}"
# Pokud oba failnou (branch smazán po předchozím close, ale backlog item má stale branch:):
CHECKOUT_EXIT=$?
if [ $CHECKOUT_EXIT -ne 0 ]; then
  echo "WARN: branch ${branch_name} not found, creating fresh from ${main_branch}"
  git checkout "${main_branch}"
  git checkout -b "${branch_name}"
fi
```

#### Post-checkout Validation (povinné)

```bash
# Ověř, že nejsme v detached HEAD
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "HEAD" ] || [ "$CURRENT_BRANCH" != "{branch_name}" ]; then
  echo "WARN: detached HEAD or wrong branch ($CURRENT_BRANCH), attempting recovery"
  # Recovery: checkout main, pak znovu vytvoř/checkout branch
  git checkout "${main_branch}" 2>/dev/null
  git checkout -b "${branch_name}" 2>/dev/null || git checkout "${branch_name}" 2>/dev/null
  # Ověř znovu
  if [ "$(git rev-parse --abbrev-ref HEAD)" != "${branch_name}" ]; then
    echo "ERROR: detached HEAD recovery failed"
    # Vytvoř intake item intake/implement-detached-head-{date}.md
    exit 1
  fi
fi

# Pokud branch existuje na remote, synchronizuj
if git ls-remote --heads origin "${branch_name}" | grep -q "${branch_name}"; then
  git pull --ff-only origin "${branch_name}" || echo "WARN: remote diverged, using local"
fi

# Post-checkout validation enhancement (P2 fix): verify working tree is on correct branch and clean
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "${branch_name}" ]; then
  echo "ERROR: expected branch ${branch_name} but on $CURRENT_BRANCH"
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "WARN: working tree not clean after checkout"
  git stash --message "auto-stash before implement ${TASK_ID}" || true
fi
```

Pokud working tree není čistý → FAIL (nejdřív vyřeš).

### 5) VERIFY-FIRST (pochop problém)

- Přečti `{WORK_ROOT}/backlog/{id}.md` (AC + dotčené soubory)
- Pokud existuje `{ANALYSES_ROOT}/{id}-analysis.md`, použij ho jako plán.

#### Analysis Validation

Ověř, že analysis obsahuje povinné sekce:
- `## Constraints` (musí existovat, i kdyby byla `None`)
- `## Plan` (musí mít alespoň 2 kroky)
- `## Tests` (musí mít alespoň 1 test)

Pokud některá sekce chybí:
- zaloguj WARNING: "analysis {id} missing section: {section}"
- pokračuj, ale v implement reportu poznamenej "incomplete analysis"
- vytvoř intake item `intake/implement-incomplete-analysis-{id}.md` (jednorázově)

Udělej baseline (s timeoutem):

```bash
timeout 300 {COMMANDS.test}
BASELINE_EXIT=$?
if [ $BASELINE_EXIT -eq 124 ]; then echo "TIMEOUT: baseline test exceeded 300s"; fi
```

Pokud baseline selže (exit ≠ 0, včetně timeout):
- nezaváděj nový kód
- vytvoř intake item `intake/baseline-tests-failing.md` (je to blocker)
- FAIL

#### Governance Compliance (VERIFY-FIRST)

- Pokud `{ANALYSES_ROOT}/{id}-analysis.md` **neexistuje**: zaloguj WARNING do implement reportu ("analysis missing, governance check skipped") a pokračuj bez governance ověření. Vytvoř intake item `intake/implement-missing-analysis-{id}.md` (jednorázově, pokud ještě neexistuje).
- Pokud analýza **existuje**: otevři `{ANALYSES_ROOT}/{id}-analysis.md` a najdi sekci **Constraints**.
- Pro každé uvedené `ADR-*` a `SPEC-*`:
  - otevři odpovídající soubor v `{WORK_ROOT}/decisions/` nebo `{WORK_ROOT}/specs/`
  - explicitně ověř, že plánovaná implementace tyto kontrakty **neporuší**.
- Pokud task implicitně vyžaduje porušení **accepted ADR** nebo **active spec**:
  - **STOP** (neimplementuj)
  - vytvoř intake item `intake/governance-conflict-{id}.md` s důkazy:
    - proč je konflikt nevyhnutelný
    - které soubory by musely porušit kontrakt
    - návrh řešení (např. nová ADR/spec, nebo změna acceptance criteria)
  - FAIL

---

## 6) Implementation

### Co: Napsat produkční kód + testy

**Minimální akceptovatelný výstup:**

1. **Uprav jen nezbytné soubory** v `{CODE_ROOT}/` — malý diff, fokusovaná změna.
2. **Testy jsou POVINNÉ** — žádný kód bez testů. Minimální test set:
   - `test_{id}_happy` — základní funkčnost (happy path)
   - `test_{id}_edge` — hraniční případ (empty input, max values, unicode, None)
   - `test_{id}_error` — chybový stav (invalid input → correct exception/error response)
3. Pokud se mění veřejné chování, připrav změnu docs (docs step to může dokončit).

### Coverage Check (POVINNÉ)

```bash
# Coverage check (POVINNÉ po všech testech)
CHANGED_MODULES=$(git diff --name-only "${main_branch}...HEAD" -- '*.py' | grep -v test | head -20)
CORE_MODULES_FAILED=0
for MODULE in $CHANGED_MODULES; do
  MODULE_NAME=$(echo "$MODULE" | sed 's|/|.|g' | sed 's|\.py$||' | sed 's|^src\.||')
  # Zjisti, jestli je core modul (services/, api/, recall/, triage/)
  if echo "$MODULE" | grep -qE '(services/|api/|recall/|triage/)'; then
    IS_CORE=1
  else
    IS_CORE=0
  fi

  timeout 120 pytest --cov="$MODULE_NAME" --cov-report=term-missing --cov-fail-under=60 -q 2>/dev/null
  COV_EXIT=$?
  if [ $COV_EXIT -ne 0 ] && [ $COV_EXIT -ne 124 ]; then
    if [ "$IS_CORE" -eq 1 ]; then
      echo "FAIL: coverage <60% for CORE module $MODULE_NAME — MUST FIX BEFORE COMMIT"
      CORE_MODULES_FAILED=$((CORE_MODULES_FAILED + 1))
    else
      echo "WARN: coverage <60% for helper module $MODULE_NAME (non-blocking)"
    fi
  fi
done

# FAIL if any core module has insufficient coverage
if [ "$CORE_MODULES_FAILED" -gt 0 ]; then
  echo "ERROR: $CORE_MODULES_FAILED core modules failed coverage threshold"
  exit 1
fi
```

Pokud coverage <60% pro core modul (services/, api/, recall/, triage/): MUSÍŠ opravit testy PŘED commitem.
Pokud coverage <60% pro helper/util: zapiš WARNING do reportu, pokračuj.

### Per-function Quality Check

```bash
# Check LOC per function
git diff "${main_branch}...HEAD" -- '*.py' | grep -E '^\+def |^\+class ' | while read line; do
  # Spočítej LOC pro každou novou funkci
  # (simplified: just warn on syntax level)
  echo "INFO: new function/class: $(echo "$line" | cut -c2-80)"
done
```

- ≤50 LOC per funkce (nebo split na menší)
- ≤3 parametry (nebo use dataclass)
- MUSÍ mít docstring
- MUSÍ mít type hints
- Žádný `pass`, `# TODO`, `...` nebo stub v DONE kódu
- Všechny nové funkce/metody mají type hints a docstring (min 1 věta)

### Test Template

```python
class Test{ComponentName}:
    """Testy pro {component} — {task_id}."""

    def test_{id}_happy(self):
        """Happy path: {co testuje}."""
        result = component.method(valid_input)
        assert result == expected

    def test_{id}_edge(self):
        """Edge case: {jaký hraniční případ}."""
        result = component.method(edge_input)
        assert result == expected_edge

    def test_{id}_error(self):
        """Error: {jaký chybový stav}."""
        with pytest.raises(ExpectedException):
            component.method(invalid_input)
```

### Integration Test Mapping (POVINNÉ)

Pokud task mění veřejné rozhraní, MUSÍ mít odpovídající integrační test.

| Typ změny | Testovací soubor | Vzor testu |
|-----------|-----------------|------------|
| Nový/změněný API endpoint | `{TEST_ROOT}/test_api_{module}.py` | `async def test_{endpoint}_{method}(): response = client.{method}("/path"); assert response.status_code == {expected}` |
| Nový/změněný CLI command | `{TEST_ROOT}/test_cli.py` | `def test_cli_{command}(): result = runner.invoke(app, ["{command}", ...]); assert result.exit_code == 0` |
| Nový/změněný service | `{TEST_ROOT}/test_{service}_integration.py` | `def test_{service}_{operation}(): svc = {Service}(real_backend); result = svc.{method}(input); assert result == expected` |
| Nový storage backend | `{TEST_ROOT}/test_{backend}_integration.py` | `def test_{backend}_roundtrip(): backend.store(item); retrieved = backend.get(item.id); assert retrieved == item` |
| Změna modelu (Pydantic) | `{TEST_ROOT}/test_models.py` | `def test_{model}_validation(): valid = {Model}(**valid_data); assert valid.field == expected` |
| Změna triage/heuristics | `{TEST_ROOT}/test_triage_{pattern}.py` | `def test_{pattern}_detection(): result = triage(input_with_pattern); assert result.tier == expected` |

#### Enforcement Check

```bash
# Po zapsání kódu ověř, že test soubor existuje
TEST_ROOT="${TEST_ROOT:-.}"  # From config.md, default to current dir
AFFECTED_FILES=$(git diff --name-only "${main_branch}...HEAD" -- '*.py' | grep -v test)
for FILE in $AFFECTED_FILES; do
  # Detekuj typ souboru a požadovaný test soubor
  if echo "$FILE" | grep -qE 'api/.*\.py'; then
    TEST_FILE="${TEST_ROOT}/test_api_$(basename "$FILE" .py).py"
  elif echo "$FILE" | grep -qE 'services/.*\.py'; then
    TEST_FILE="${TEST_ROOT}/test_$(basename "$FILE" .py)_integration.py"
  elif echo "$FILE" | grep -qE 'triage/.*\.py'; then
    TEST_FILE="${TEST_ROOT}/test_triage_$(basename "$FILE" .py).py"
  else
    # Ostatní moduly — alespoň test_{module}.py
    TEST_FILE="${TEST_ROOT}/test_$(basename "$FILE" .py).py"
  fi

  # Ověř, že test soubor existuje
  if ! git show HEAD:"$TEST_FILE" >/dev/null 2>&1 && [ ! -f "$TEST_FILE" ]; then
    echo "ERROR: missing integration test for $FILE (expected $TEST_FILE)"
    echo "CREATE: $TEST_FILE with mapping from table above"
    exit 1
  fi
done
```

### Anti-patterns (zakázáno)

- ❌ Commit bez testů ("testy dodám později" = nikdy)
- ❌ `pass` nebo `raise NotImplementedError` v produkčním kódu
- ❌ Stub testy: `def test_something(): assert True` (musí testovat reálné chování)
- ❌ God function >50 řádků (rozděl na menší funkce)
- ❌ Hardcoded magic numbers (použij konstanty nebo config)
- ❌ `# type: ignore` bez komentáře proč
- ❌ Kopírování kódu místo abstrakce (DRY)
- ❌ Pouze unit testy pro API endpoint změnu (MUSÍ mít integrační test s HTTP klientem)
- ❌ Mock VŠECHNO — integrační test má testovat reálnou interakci (mock jen external deps)

---

## 7) Quality Gates & Auto-fix

### Auto-fix Decision Tree

```
Lint errors count:
  ≤5:        auto-fix all, then re-run. If new errors → revert, manual fix.
  6-20:      auto-fix, re-run. If ≥30% regression (nové errors) → revert, manual fix.
  >20:       DON'T auto-fix. Create intake item, manual fix required.
```

#### Implementation (konkrétní)

```bash
# Count lint errors PŘED auto-fixem
LINT_ERROR_COUNT=$(timeout 120 {COMMANDS.lint} 2>&1 | grep -cE '^[^:]+:[0-9]+:[0-9]+:' || echo 0)

if [ "$LINT_ERROR_COUNT" -le 5 ]; then
  # AUTO-FIX ALL
  echo "Lint errors ≤5 ($LINT_ERROR_COUNT) — attempting auto-fix all"
  timeout 120 {COMMANDS.lint_fix}
  AUTOFIX_EXIT=$?
  if [ $AUTOFIX_EXIT -eq 0 ]; then
    # Re-run lint
    timeout 120 {COMMANDS.lint}
    LINT_RERUN_EXIT=$?
    if [ $LINT_RERUN_EXIT -ne 0 ]; then
      echo "WARN: lint still fails after auto-fix, reverting auto-fix changes"
      git checkout -- .
    fi
  fi
elif [ "$LINT_ERROR_COUNT" -le 20 ]; then
  # AUTO-FIX WITH REGRESSION CHECK
  echo "Lint errors 6-20 ($LINT_ERROR_COUNT) — auto-fix with regression check"
  timeout 120 {COMMANDS.lint_fix}
  AUTOFIX_EXIT=$?
  if [ $AUTOFIX_EXIT -eq 0 ]; then
    # Count errors AFTER auto-fix
    LINT_ERROR_AFTER=$(timeout 120 {COMMANDS.lint} 2>&1 | grep -cE '^[^:]+:[0-9]+:[0-9]+:' || echo 0)
    # Calculate regression percentage
    if [ "$LINT_ERROR_COUNT" -gt 0 ]; then
      REGRESSION_PCT=$((($LINT_ERROR_AFTER - $LINT_ERROR_COUNT) * 100 / $LINT_ERROR_COUNT))
      if [ "$REGRESSION_PCT" -gt 30 ]; then
        echo "WARN: regression detected (+${REGRESSION_PCT}% errors), reverting auto-fix"
        git checkout -- .
      fi
    fi
  fi
else
  # DON'T AUTO-FIX — >20 errors
  echo "Lint errors >20 ($LINT_ERROR_COUNT) — DO NOT auto-fix, requires manual fix"
  python skills/fabric-init/tools/fabric.py intake-new --source "implement" --slug "implement-lint-too-many-${date}" \
    --title "Too many lint errors ($LINT_ERROR_COUNT) — requires manual fix (auto-fix disabled for >20 errors)"
fi
```

### Regression Detection Post Auto-fix

```bash
# 1. Zapamatuj si pre-autofix test výsledek
PRE_FIX_TEST_RESULT="$TEST_RESULT"  # PASS nebo FAIL

# 2. Spusť auto-fix (lint_fix nebo format)
timeout 120 {COMMANDS.lint_fix}
AUTOFIX_EXIT=$?
if [ $AUTOFIX_EXIT -eq 124 ]; then echo "TIMEOUT: auto-fix"; fi

# 3. Spusť testy PŘED opakovaným gate checkem
timeout 300 {COMMANDS.test}
POST_FIX_TEST_EXIT=$?
if [ $POST_FIX_TEST_EXIT -eq 124 ]; then POST_FIX_TEST="TIMEOUT";
elif [ $POST_FIX_TEST_EXIT -ne 0 ]; then POST_FIX_TEST="FAIL"; else POST_FIX_TEST="PASS"; fi

# 4. Regression check: pokud testy předtím PASS a teď FAIL → revert auto-fix
if [ "$PRE_FIX_TEST_RESULT" = "PASS" ] && [ "$POST_FIX_TEST" != "PASS" ]; then
  echo "REGRESSION: auto-fix broke tests, reverting"
  git checkout -- .
fi
```

### Auto-fix Counter (Idempotence Guard)

```bash
# Přečti auto-fix counter z backlog itemu (přežije re-run)
AUTOFIX_COUNT=$(grep 'autofix_count:' {WORK_ROOT}/backlog/{id}.md | awk '{print $2}')
AUTOFIX_COUNT=${AUTOFIX_COUNT:-0}
if [ "$AUTOFIX_COUNT" -ge 1 ]; then
  echo "SKIP: auto-fix already ran for this task (autofix_count=$AUTOFIX_COUNT)"
else
  # Spusť auto-fix
  # Po úspěšném auto-fixu inkrementuj counter:
  NEW_COUNT=$((AUTOFIX_COUNT + 1))
  sed -i "s/^autofix_count:.*/autofix_count: $NEW_COUNT/" {WORK_ROOT}/backlog/{id}.md
fi
```

Counter se resetuje na 0 při výběru nového tasku.

### Blocked Dependencies Detection

```bash
DEPENDS=$(grep 'depends_on:' {WORK_ROOT}/backlog/{id}.md | sed 's/depends_on://' | tr -d '[],' | xargs)
if [ -n "$DEPENDS" ]; then
  for DEP in $DEPENDS; do
    DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" 2>/dev/null | awk '{print $2}')
    if [ "$DEP_STATUS" != "DONE" ]; then
      echo "BLOCKED: dependency $DEP not DONE (status=$DEP_STATUS)"
      python skills/fabric-init/tools/fabric.py intake-new --source "implement" --slug "blocked-dep-${DEP}" \
        --title "Task $id blocked: dependency $DEP status=$DEP_STATUS (not DONE)"
      exit 1
    fi
  done
fi
```

### Spec/ADR Drift Detection

```bash
if [ -f "{ANALYSES_ROOT}/{id}-analysis.md" ]; then
  if grep -q "InMemoryBackend" "{ANALYSES_ROOT}/{id}-analysis.md" && \
     grep -q "QdrantBackend" {CODE_ROOT}/storage/backends/*.py; then
    echo "WARN: analysis vs implementation drift detected"
    python skills/fabric-init/tools/fabric.py intake-new --source "implement" --slug "impl-spec-drift-${id}" \
      --title "ADR/SPEC drift detected during $id implementation"
  fi
fi
```

### Code Complexity Validation (WQ8)

```bash
# Cyclomatic complexity check (radon — optional)
if command -v radon &> /dev/null; then
  echo "Running complexity analysis..."
  radon cc -a -nc src/llmem/ | grep -E "src/llmem/(services|api|recall|triage)/" | while read line; do
    FUNC=$(echo "$line" | awk '{print $1}')
    CC=$(echo "$line" | grep -oE "[0-9]+" | head -1)
    if [ "$CC" -gt 10 ]; then
      echo "WARN: high cyclomatic complexity in $FUNC: CC=$CC"
    fi
  done
fi

# Function length distribution
git diff "${main_branch}...HEAD" -- '*.py' | \
  grep -E '^\+def |^\+class ' | \
  while read line; do
    FUNC=$(echo "$line" | sed 's/^\+//' | cut -c2-60)
    echo "New function: $FUNC (verify ≤50 LOC)"
  done
```

**Enforcement criteria:**
- ✅ PASS: Cyclomatic complexity ≤10 (≤15 for complex logic)
- ✅ PASS: Function length ≤50 lines
- ✅ PASS: Max nesting depth ≤3
- ❌ FAIL: CC >15 without justification

---

## 8) Commit & Self-review

### Pre-existing Fixes Separation

```bash
# zjisti, které soubory opravil auto-fix, ale NEJSOU v diff tasku
git diff --name-only "${main_branch}...HEAD" > /tmp/task-files.txt
git diff --name-only > /tmp/autofix-files.txt
# soubory v autofix ale ne v task-files = pre-existing
```

Pokud existují pre-existing fixy:
```bash
# Commitni je separátně PŘED task commitem
git add <pre-existing-files>
git commit -m "chore: auto-fix pre-existing lint/format"
```

### Quick Security & Reliability Scan

```bash
# Quick security scan na diff
git diff "${main_branch}...HEAD" -- '*.py' | grep -n \
  -e 'eval(' -e 'exec(' -e 'subprocess.*shell=True' \
  -e '__import__' -e 'pickle.loads' -e 'yaml.load(' \
  -e 'os.system(' -e 'input(' \
  > /tmp/security-scan.txt 2>/dev/null

# Quick reliability scan
git diff "${main_branch}...HEAD" -- '*.py' | grep -n \
  -e 'except:$' -e 'except Exception:$' \
  -e 'pass$' -e '# TODO' -e '# FIXME' -e '# HACK' \
  > /tmp/reliability-scan.txt 2>/dev/null
```

**Security/Reliability Checklist:**
- [ ] Žádný `eval()`, `exec()`, `subprocess(shell=True)` bez sanitizace
- [ ] Žádný bare `except:` nebo `except Exception:` bez re-raise/logging
- [ ] Žádný `pass` v exception handleru
- [ ] Všechny nové I/O operace mají timeout
- [ ] Všechny nové user vstupy jsou validované

### Commit Message

```bash
git add -A
git commit -m "feat({id}): {short description}"
# nebo
git commit -m "fix({id}): {short description}"
```

Message MUSÍ mít format `feat/fix({task_id}): ...`

---

## 9) Timeout Handling

```bash
timeout 120 {COMMANDS.lint}
LINT_EXIT=$?
if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint exceeded 120s"; GATE_RESULT="TIMEOUT"; fi

timeout 120 {COMMANDS.format_check}
FMT_EXIT=$?
if [ $FMT_EXIT -eq 124 ]; then echo "TIMEOUT: format exceeded 120s"; GATE_RESULT="TIMEOUT"; fi

timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then echo "TIMEOUT: test exceeded 300s"; GATE_RESULT="TIMEOUT"; fi
```

- Pokud GATE_RESULT=TIMEOUT: zapiš do implement reportu `TIMEOUT`
- Auto-fix se nepokouší po timeoutu → rovnou FAIL
- Timeout exit code 124 NESMÍ být zaměněn za normální test failure

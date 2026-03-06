---
name: fabric-implement
description: "Implement exactly one task (WIP=1) from the sprint Task Queue. VERIFY-FIRST workflow: read config+analysis, inspect code, create/reuse feature branch, implement minimal change + tests, run COMMANDS (test/lint/format_check), commit, and update backlog item metadata (status/branch). Only updates state.md fields wip_item/wip_branch."
---

# IMPLEMENT — Kód + testy (WIP=1, VERIFY-FIRST)

## Účel

Implementovat **jednu** backlog položku (Task/Bug/Chore/Spike) podle `Task Queue` ve sprint plánu.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-implement" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-implement" --event end --status OK --report "{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Princip:
- **VERIFY-FIRST**: nejdřív čti, ověř, reprodukuj; až pak piš kód.
- **Small batch**: malý diff, rychlé iterace.
- **Evidence-driven**: testy + lint + format check musí projít.

---

## Vstupy

Povinné:
- `{WORK_ROOT}/config.md` (COMMANDS + cesty + git)
- `{WORK_ROOT}/state.md` (wip_item/wip_branch + sprint N)
- `{WORK_ROOT}/sprints/sprint-{N}.md` (sekce `## Task Queue`)
- `{WORK_ROOT}/backlog/{id}.md`
- `{ANALYSES_ROOT}/{id}-analysis.md` (pokud existuje; preferované)
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`

Volitelné:
- předchozí `reports/review-*.md` (pokud jde o rework)

---

## Výstupy

**Output schema (WQ9: version field):**

All reports use schema `fabric.report.v1` with `version: "1.0"` field.

- git branch s commit(y)
- aktualizovaný backlog item `{WORK_ROOT}/backlog/{id}.md`:
  - `status: IN_PROGRESS` během práce
  - `status: IN_REVIEW` po úspěšném commit + passing checks
  - `branch: <branch-name>`
  - `updated: <YYYY-MM-DD>`
- update `{WORK_ROOT}/state.md` (pouze):
  - `wip_item`
  - `wip_branch`

- `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md`
  ```yaml
  ---
  schema: fabric.report.v1
  kind: implement
  version: "1.0"
  task_id: "{wip_item}"
  branch: "{branch_name}"
  created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
  commit_hash: "{sha}"
  test_result: "PASS"
  coverage_pct: {percentage}
  ---
  ```
  (vytvoř jako kopii `{WORK_ROOT}/templates/report.md`; shrň změny, test evidence, commit hash, otevřený PR/Review)

**FILLED-IN EXAMPLE (Task T-TRI-02, LLMem triage heuristics):**

```yaml
---
schema: fabric.report.v1
kind: implement
version: "1.0"
task_id: "T-TRI-02"
branch: "feature/tri-02-heuristics"
created_at: "2026-03-06T14:30:00Z"
---

# T-TRI-02 Implementation Report

## Summary

Implemented deterministic triage heuristics for secret/PII/preference/decision detection. Added 8 unit tests covering regex patterns, 1 integration test (end-to-end capture→triage), edge cases (unicode, empty content), and error handling (invalid regex). Coverage increased from 62% to 78% in triage module (target ≥60% — PASS).

## Changes

### Modified Files
- `src/llmem/triage/heuristics.py` — added `triage_event()` function with 4 regex patterns (secret, PII, preference, decision)
- `src/llmem/triage/patterns.py` — added regex patterns for OpenAI, GitHub, AWS, Bearer token, password detection
- `tests/test_triage_heuristics.py` — 8 new unit tests

**Diff stats:**
```
 src/llmem/triage/heuristics.py   | 120 ++++++++++++++++++
 src/llmem/triage/patterns.py     |  85 ++++++++++++
 tests/test_triage_heuristics.py  | 180 +++++++++++++++++++++++++
 3 files changed, 385 insertions(+)
```

### Evidence

**Tests (PASS):**
```bash
pytest tests/test_triage_heuristics.py -v
test_triage_happy_path PASSED
test_triage_secret_detection PASSED
test_triage_pii_masking PASSED
test_triage_preference_extraction PASSED
test_triage_decision_extraction PASSED
test_triage_edge_empty_content PASSED
test_triage_edge_unicode_normalization PASSED
test_triage_error_invalid_regex PASSED
test_triage_integration_capture_to_triage PASSED

====== 9 passed in 1.42s ======
```

**Coverage (PASS, ≥60%):**
```
src/llmem/triage/heuristics.py: 78% (target ≥60%)
src/llmem/triage/patterns.py: 81%
```

**Lint (PASS):**
```
ruff check src/llmem/triage/ — 0 errors
```

**Commit:**
```
feat(T-TRI-02): implement deterministic triage heuristics with secret/PII/preference detection
```

## Risks & Follow-ups

- **Regex performance**: Large event text (>10MB) may slow triage. Mitigated: added timeout in CaptureService (5s).
- **Regex false positives**: Pattern for AWS key may match other strings. Mitigated: regex tested against 50+ real AWS keys + false positives (97% precision in tests).
- **TODO**: Add performance benchmark test `test_triage_performance_large_event()` in next sprint.

## Status

Task status: **IN_REVIEW** (ready for review + testing by fabric-review skill).
```

---

## Downstream Contract (WQ7)

**fabric-implement** contracts with **downstream skills:**

| Skill | Contract | Enforcement |
|-------|----------|------------|
| **fabric-test** (if separate) | Commit hash recorded in backlog. Branch exists and is clean. Coverage ≥60% (or documented exception). | Test skill queries backlog for commit_hash; missing = warning |
| **fabric-review** | Status = IN_REVIEW. All tests PASS. Lint PASS (or skipped in bootstrap). | Review reads status + test results from backlog + reports |
| **fabric-close** | Branch exists. Commit message follows conventional format. No stubs/TODO in code. | Close detects invalid branches or stubs via pre-merge scan |
| **backlog index** | Backlog item updated with branch + status. Updated timestamp current. | Loop regenerates index after implement; verifies consistency |

**Errors that break contract (CRITICAL):**
- ❌ Branch not created or wrong name → close cannot find commits to merge
- ❌ Status not set to IN_REVIEW → review skill skips task, implementation wasted
- ❌ Tests not PASS → coverage metrics inaccurate, quality gates fail downstream
- ❌ Stubs/pass left in code → review will reject, implements wasted time

---

## Preconditions (fail fast)

1. `{CODE_ROOT}/` musí existovat.
2. Backlog item soubor musí existovat na disku:
   ```bash
   TASK_ID="..."  # z state.wip_item nebo vybraný z Task Queue
   if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
     echo "STOP: backlog file not found: backlog/${TASK_ID}.md"
     python skills/fabric-init/tools/fabric.py intake-new --source "implement" --slug "missing-backlog-file" \
       --title "Backlog file not found: backlog/${TASK_ID}.md"
     exit 1
   fi
   ```
3. V configu musí být vyplněno:

- `COMMANDS.test` (**povinné**; nesmí být `TBD` ani prázdné)
- `COMMANDS.lint` (volitelné; `""` = vypnuto, `TBD` = konfigurační chyba)
- `COMMANDS.format_check` (volitelné; `""` = vypnuto, `TBD` = konfigurační chyba)

Pravidla:
- Pokud `COMMANDS.test` je `TBD` nebo `""` → vytvoř `intake/config-missing-test-command.md` a **FAIL**.
- Pokud `COMMANDS.lint` je `TBD` → vytvoř `intake/config-missing-lint-command.md` a **FAIL**.
  - Pokud je `""` → pokračuj, ale vytvoř `intake/recommend-enable-lint.md` (WARN).
- Pokud `COMMANDS.format_check` je `TBD` → vytvoř `intake/config-missing-format-check-command.md` a **FAIL**.
  - Pokud je `""` → pokračuj, ale vytvoř `intake/recommend-enable-format-check.md` (WARN).

- Pokud `QUALITY.mode` je `strict`:
  - `COMMANDS.lint` a `COMMANDS.format_check` NESMÍ být `""` (vypnuto).
  - Pokud jsou `""` → vytvoř `intake/strict-mode-missing-lint-or-format.md` a **FAIL**.


---


## FAST PATH (doporučeno) — state/backlog patch + gates deterministicky

### Práce se state.md (bez ruční editace YAML)
- přečti state:
  ```bash
  python skills/fabric-init/tools/fabric.py state-read
  ```
- nastav WIP (jakmile vybereš task + branch):
  ```bash
  python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"wip_item":"<id>","wip_branch":"<branch>"}'
  ```

### Objektivní gates (log capture)
```bash
python skills/fabric-init/tools/fabric.py run test --tail 200
python skills/fabric-init/tools/fabric.py run lint --tail 200
python skills/fabric-init/tools/fabric.py run format_check --tail 200
```

### Backlog metadata (branch/status) patchuj přes plan/apply
Po prvním commitu vytvoř plan:

```yaml
schema: fabric.plan.v1
ops:
  - op: backlog.set
    id: "{wip_item}"
    fields:
      status: "IN_PROGRESS"
      branch: "{branch}"
      updated: "{YYYY-MM-DD}"
  - op: backlog.index
```

A aplikuj:

```bash
python skills/fabric-init/tools/fabric.py apply "{WORK_ROOT}/reports/implement-plan-{wip_item}-{YYYY-MM-DD}.yaml"
```

---

## Postup

### 1) Vyber task (WIP=1)

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

### 2) Připrav branch (create nebo reuse)

1. Načti backlog item `{WORK_ROOT}/backlog/{id}.md` a zjisti `branch:`.
2. Pokud `branch` existuje → reuse.
3. Pokud `branch` neexistuje:
   - vymysli branch name:
     - default: `{id}-impl`
     - nebo podle `GIT.feature_branch_pattern` (pokud je definováno)
   - zapiš `branch:` do backlog itemu

**Unicode normalization (P2 fix): Sanitize branch name before git checkout:**
```bash
# Unicode normalization (P2 fix): sanitize branch name
branch_name=$(echo "${branch_name}" | LC_ALL=C sed 's/[^a-zA-Z0-9._/-]/-/g' | sed 's/--*/-/g')
```

Git kroky:

```bash
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

**Post-checkout validace (povinné):**
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

### 3) VERIFY-FIRST (pochop problém)

- Přečti `{WORK_ROOT}/backlog/{id}.md` (AC + dotčené soubory)
- Pokud existuje `{ANALYSES_ROOT}/{id}-analysis.md`, použij ho jako plán.

**Validace analýzy (pokud existuje):**
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

#### 3.1) Governance compliance (VERIFY-FIRST)

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

### 4) Implementuj minimální změnu

**Co:** Napsat produkční kód + testy tak, aby AC byly splněny a quality gates prošly.

**Jak (detailní instrukce):**

1. **Uprav jen nezbytné soubory** v `{CODE_ROOT}/` — malý diff, fokusovaná změna.
2. **Testy jsou POVINNÉ** — žádný kód bez testů. Minimální test set:
   - `test_{id}_happy` — základní funkčnost (happy path)
   - `test_{id}_edge` — hraniční případ (empty input, max values, unicode, None)
   - `test_{id}_error` — chybový stav (invalid input → correct exception/error response)
3. Pokud se mění veřejné chování, připrav změnu docs (docs step to může dokončit).

**Minimum akceptovatelného výstupu:**
- ≥3 testy (happy/edge/error) pro každou novou/změněnou komponentu
- Coverage nových řádků ≥60% pro core modules (services/, api/, recall/, triage/) — **VYNUCENO a MUSÍ FAILNOUT:**
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
- Per-function quality check (POVINNÉ):
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

**Anti-patterns (zakázáno):**
- ❌ Commit bez testů ("testy dodám později" = nikdy)
- ❌ `pass` nebo `raise NotImplementedError` v produkčním kódu
- ❌ Stub testy: `def test_something(): assert True` (musí testovat reálné chování)
- ❌ God function >50 řádků (rozděl na menší funkce)
- ❌ Hardcoded magic numbers (použij konstanty nebo config)
- ❌ `# type: ignore` bez komentáře proč
- ❌ Kopírování kódu místo abstrakce (DRY)

**Šablona testu:**
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

**Integration test mapping (POVINNÉ pro API/service/CLI změny) — ENFORCEMENT:**

Pokud task mění veřejné rozhraní, MUSÍ mít odpovídající integrační test. Po zapsání produkčního kódu MUSÍŠ ověřit, že test soubor existuje. Mapping:

| Typ změny | Testovací soubor | Vzor testu |
|-----------|-----------------|------------|
| Nový/změněný API endpoint | `tests/test_api_{module}.py` | `async def test_{endpoint}_{method}(): response = client.{method}("/path"); assert response.status_code == {expected}` |
| Nový/změněný CLI command | `tests/test_cli.py` | `def test_cli_{command}(): result = runner.invoke(app, ["{command}", ...]); assert result.exit_code == 0` |
| Nový/změněný service | `tests/test_{service}_integration.py` | `def test_{service}_{operation}(): svc = {Service}(real_backend); result = svc.{method}(input); assert result == expected` |
| Nový storage backend | `tests/test_{backend}_integration.py` | `def test_{backend}_roundtrip(): backend.store(item); retrieved = backend.get(item.id); assert retrieved == item` |
| Změna modelu (Pydantic) | `tests/test_models.py` | `def test_{model}_validation(): valid = {Model}(**valid_data); assert valid.field == expected` |
| Změna triage/heuristics | `tests/test_triage_{pattern}.py` | `def test_{pattern}_detection(): result = triage(input_with_pattern); assert result.tier == expected` |

**Enforcement check (POVINNÉ)**:
```bash
# Po zapsání kódu ověř, že test soubor existuje
AFFECTED_FILES=$(git diff --name-only "${main_branch}...HEAD" -- '*.py' | grep -v test)
for FILE in $AFFECTED_FILES; do
  # Detekuj typ souboru a požadovaný test soubor
  if echo "$FILE" | grep -qE 'api/.*\.py'; then
    TEST_FILE="tests/test_api_$(basename "$FILE" .py).py"
  elif echo "$FILE" | grep -qE 'services/.*\.py'; then
    TEST_FILE="tests/test_$(basename "$FILE" .py)_integration.py"
  elif echo "$FILE" | grep -qE 'triage/.*\.py'; then
    TEST_FILE="tests/test_triage_$(basename "$FILE" .py).py"
  else
    # Ostatní moduly — alespoň test_{module}.py
    TEST_FILE="tests/test_$(basename "$FILE" .py).py"
  fi

  # Ověř, že test soubor existuje
  if ! git show HEAD:"$TEST_FILE" >/dev/null 2>&1 && [ ! -f "$TEST_FILE" ]; then
    echo "ERROR: missing integration test for $FILE (expected $TEST_FILE)"
    echo "CREATE: $TEST_FILE with mapping from table above"
    exit 1
  fi
done
```

**Anti-patterns:**
- ❌ Pouze unit testy pro API endpoint změnu (MUSÍ mít integrační test s HTTP klientem)
- ❌ Mock VŠECHNO — integrační test má testovat reálnou interakci (mock jen external deps)
- ❌ Přeskočit mapping enforcement check (je POVINNÝ)
- ✅ Pro KAŽDOU API změnu: ≥1 integrační test který volá endpoint přes HTTP client
- ✅ Test soubor MUSÍ existovat před commitem (enforce via check výše)

Během práce nastav backlog status:
- `status: IN_PROGRESS`
- `updated: {YYYY-MM-DD}`

### 5) Run quality gates (must pass)

Spusť quality commands v tomto pořadí:

- Lint (pokud `COMMANDS.lint` není prázdné)
- Format check (pokud `COMMANDS.format_check` není prázdné)
- Tests (vždy)

```bash
# lint (optional) — s timeoutem
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint}
  LINT_EXIT=$?
  if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint exceeded 120s"; LINT_RESULT="TIMEOUT";
  elif [ $LINT_EXIT -ne 0 ]; then LINT_RESULT="FAIL"; else LINT_RESULT="PASS"; fi
else echo "lint: SKIPPED"; LINT_RESULT="SKIPPED"; fi

# format check (optional) — s timeoutem
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check}
  FMT_EXIT=$?
  if [ $FMT_EXIT -eq 124 ]; then echo "TIMEOUT: format_check exceeded 120s"; FMT_RESULT="TIMEOUT";
  elif [ $FMT_EXIT -ne 0 ]; then FMT_RESULT="FAIL"; else FMT_RESULT="PASS"; fi
else echo "format_check: SKIPPED"; FMT_RESULT="SKIPPED"; fi

# tests (required) — s timeoutem
timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then echo "TIMEOUT: test exceeded 300s"; TEST_RESULT="TIMEOUT";
elif [ $TEST_EXIT -ne 0 ]; then TEST_RESULT="FAIL"; else TEST_RESULT="PASS"; fi
```

#### Auto-fix (pokud gates failnou) — DECISION TREE

Pokud lint nebo format check failne a config má příslušný fix příkaz, **spusť auto-fix a opakuj gate** PODLE tohoto stromu rozhodnutí:

**Auto-fix decision tree (konkrétní):**
```
Lint errors count:
  ≤5:        auto-fix all, then re-run. If new errors → revert, manual fix.
  6-20:      auto-fix, re-run. If ≥30% regression (nové errors) → revert, manual fix.
  >20:       DON'T auto-fix. Create intake item, manual fix required.
```

**Implementace (konkrétní):**
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

1. **Lint fail** + `COMMANDS.lint_fix` není prázdné → spusť auto-fix podle stromu výše.
2. **Format fail** + `COMMANDS.format` není prázdné → spusť `timeout 120 {COMMANDS.format}` (exit 124 = timeout → FAIL), pak znovu `{COMMANDS.format_check}`.

Pokud lint/format fail a příslušný fix příkaz **je prázdný** (`""`) → auto-fix není možný. Vytvoř intake item `intake/implement-recommend-lint-fix-command.md` (jednorázově, jen pokud ještě neexistuje) a oprav chyby manuálně.

Auto-fix smí proběhnout **max 1×** per gate per implement run. Pokud po auto-fixu gate stále failne → oprav manuálně (v rámci stejného tasku).

**Persisted auto-fix counter (idempotence guard pro re-run):**
```bash
# Přečti auto-fix counter z backlog itemu (přežije re-run)
AUTOFIX_COUNT=$(grep 'autofix_count:' {WORK_ROOT}/backlog/{id}.md | awk '{print $2}')
AUTOFIX_COUNT=${AUTOFIX_COUNT:-0}
if [ "$AUTOFIX_COUNT" -ge 1 ]; then
  echo "SKIP: auto-fix already ran for this task (autofix_count=$AUTOFIX_COUNT)"
  # Nepokouš se znovu — auto-fix je idempotentní jen 1×
else
  # Spusť auto-fix (viz kód níže)
  # Po úspěšném auto-fixu inkrementuj counter:
  NEW_COUNT=$((AUTOFIX_COUNT + 1))
  sed -i "s/^autofix_count:.*/autofix_count: $NEW_COUNT/" {WORK_ROOT}/backlog/{id}.md \
    || echo "WARN: autofix_count increment failed"

  # Verify persist succeeded
  VERIFY_COUNT=$(grep 'autofix_count:' {WORK_ROOT}/backlog/{id}.md | awk '{print $2}')
  if [ "$VERIFY_COUNT" != "$NEW_COUNT" ]; then
    echo "WARN: autofix_count persist failed (expected $NEW_COUNT, got $VERIFY_COUNT)"
    # Fallback: append if field missing
    if ! grep -q 'autofix_count:' {WORK_ROOT}/backlog/{id}.md; then
      echo "autofix_count: $NEW_COUNT" >> {WORK_ROOT}/backlog/{id}.md
    fi
  fi
fi
```
Counter se resetuje na 0 při výběru nového tasku (fabric-loop, spolu s test_fail_count a rework_count).

**Bounds check across rework cykly:** `autofix_count >= 1` → SKIP auto-fix v KAŽDÉM dalším implement runu pro stejný task. Toto znamená, že auto-fix proběhne maximálně 1× per task (ne per gate per run, ale per CELÝ task lifecycle). Pokud auto-fix nepomohl v prvním runu, v rework cyklech se nepokouší znovu — opravuj manuálně. Hard cap: `autofix_count` je bounded `max_rework_iters` (default 3) protože nový task resetuje counter.

#### Regression detection po auto-fixu (povinné)

Po spuštění auto-fix příkazu a PŘED opakovaným gate checkem ověř, že auto-fix NEZHORŠIL stav:

```bash
# 1. Zapamatuj si pre-autofix test výsledek
PRE_FIX_TEST_RESULT="$TEST_RESULT"  # PASS nebo FAIL z předchozího gate runu

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
  # Vytvoř intake item pro manuální řešení
  # intake/implement-autofix-regression-{date}.md
fi
```

> **Proč:** Auto-fix (lint_fix, format) může zavést nekompatibilní změny (např. import re-ordering, trailing comma v multiline). Regression detection zabraňuje tichému zhoršení.

#### Blocked dependencies detection (POVINNÉ)

Pokud task závisí na jiném tasku (field `depends_on` v backlog):
```bash
DEPENDS=$(grep 'depends_on:' {WORK_ROOT}/backlog/{id}.md | sed 's/depends_on://' | tr -d '[],' | xargs)
if [ -n "$DEPENDS" ]; then
  for DEP in $DEPENDS; do
    DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" 2>/dev/null | awk '{print $2}')
    if [ "$DEP_STATUS" != "DONE" ]; then
      echo "BLOCKED: dependency $DEP not DONE (status=$DEP_STATUS)"
      python skills/fabric-init/tools/fabric.py intake-new --source "implement" --slug "blocked-dep-${DEP}" \
        --title "Task $id blocked: dependency $DEP status=$DEP_STATUS (not DONE)"
      exit 1  # FAIL this task, move to next
    fi
  done
fi
```

#### Spec/ADR drift detection (POVINNÉ)

Během implementace pokud zjistíš, že se plán LIŠÍ od aktuálního ADR/SPEC:
```bash
# Kontrola: pokud implementation discovery reveals ADR/SPEC drift
if [ -f "{ANALYSES_ROOT}/{id}-analysis.md" ]; then
  # Hledej nesrovnalosti mezi analysis a skutečným kódem
  # Např. analysis říká "use InMemoryBackend" ale codebase potřebuje Qdrant
  if grep -q "InMemoryBackend" "{ANALYSES_ROOT}/{id}-analysis.md" && \
     grep -q "QdrantBackend" {CODE_ROOT}/storage/backends/*.py; then
    echo "WARN: analysis vs implementation drift detected"
    python skills/fabric-init/tools/fabric.py intake-new --source "implement" --slug "impl-spec-drift-${id}" \
      --title "ADR/SPEC drift detected during $id implementation — requires ADR update or analysis correction"
  fi
fi
```

#### Separace pre-existing fixů (povinné)

Pokud auto-fix opravil soubory, rozliš, které změny patří k tasku a které jsou pre-existing:

```bash
# zjisti, které soubory opravil auto-fix, ale NEJSOU v diff tasku
git diff --name-only "${main_branch}...HEAD" > /tmp/task-files.txt
git diff --name-only > /tmp/autofix-files.txt
# soubory v autofix ale ne v task-files = pre-existing
```

**Error handling:** Pokud `git diff` vrátí chybu (detached HEAD, corrupted index, merge conflict):
- zaloguj chybu do implement reportu
- fallback: commitni VŠECHNY auto-fix změny jako pre-existing (bezpečnější než riskovat smíchání)
- vytvoř intake item `intake/implement-git-diff-error-{date}.md`

Pokud working tree je dirty z neočekávaného důvodu (uncommitted changes před auto-fixem):
- stashni existující změny: `git stash`
- spusť auto-fix
- proveď separaci
- pop stash: `git stash pop`
- **Pokud stash pop selže** (merge conflict):
  1. `git stash drop` NEPROVÁDĚJ (stash obsahuje necommitnutou práci)
  2. `git checkout -- .` reset conflicted files
  3. `git stash pop` znovu (nebo `git stash show -p | git apply --3way`)
  4. Pokud stále selže → `git stash list` a zaloguj stash ref do reportu
  5. Vytvoř intake item `intake/implement-stash-conflict-{date}.md` s instrukcí pro manuální recovery
  6. FAIL task (nesmíš riskovat ztrátu kódu)

Pokud existují pre-existing fixy (soubory mimo diff tasku):
- commitni je **separátně** před task commitem:
  ```bash
  git add <pre-existing-files>
  git commit -m "chore: auto-fix pre-existing lint/format"
  ```

Pokud něco selže:
- neopouštěj branch
- oprav (v rámci stejného tasku)
- opakuj gates

**Code complexity metrics validation (WQ8 ENFORCEMENT):**

Po zapsání všeho kódu proveď complexity check (POVINNÉ):

```bash
# Cyclomatic complexity check (radon — optional install)
if command -v radon &> /dev/null; then
  echo "Running complexity analysis..."
  radon cc -a -nc src/llmem/ | grep -E "src/llmem/(services|api|recall|triage)/" | while read line; do
    # Extract function name and CC score
    FUNC=$(echo "$line" | awk '{print $1}')
    CC=$(echo "$line" | grep -oE "[0-9]+" | head -1)

    # Warn if CC > 10 (complex function)
    if [ "$CC" -gt 10 ]; then
      echo "WARN: high cyclomatic complexity in $FUNC: CC=$CC (consider refactoring if >15)"
    fi
  done
else
  echo "SKIP: radon not installed (optional complexity check)"
fi

# Function length distribution
echo "Function length analysis:"
git diff "${main_branch}...HEAD" -- '*.py' | \
  grep -E '^\+def |^\+class ' | \
  while read line; do
    FUNC=$(echo "$line" | sed 's/^\+//' | cut -c2-60)
    echo "New function: $FUNC (verify ≤50 LOC)"
  done
```

**Enforcement criteria:**
- ✅ PASS: Cyclomatic complexity ≤10 for most functions (≤15 acceptable for complex business logic)
- ✅ PASS: Function length ≤50 lines (or documented exception)
- ✅ PASS: Max nesting depth ≤3 (else split to helper function)
- ❌ FAIL: CC >15 without justification + comment
- ❌ FAIL: Function >50 LOC without docstring explaining why

**Anti-patterns (WQ8):**
- ❌ Long functions with nested loops/conditions (split to helpers)
- ❌ Same complexity pattern repeated (extract shared logic)
- ❌ No comments on complex sections (add "# Why this complexity: ...")

### 6) Commit

Commit message musí obsahovat ID:
- `feat({id}): ...` nebo `fix({id}): ...`

Commituj jen soubory patřící k tasku (pre-existing fixy už byly commitnuty zvlášť):

```bash
git add -A
git commit -m "feat({id}): {short description}"
```

Po commit:
- nastav backlog item `status: IN_REVIEW`
- doplň `updated: {YYYY-MM-DD}`

### 6.1) Per-task micro-review (security + reliability quick check)

PO COMMITU a PŘED přechodem na další krok proveď RYCHLÝ self-review zaměřený na R2 (Security) a R4 (Reliability):

```bash
# Quick security scan na diff
git diff "${main_branch}...HEAD" -- '*.py' | grep -n \
  -e 'eval(' -e 'exec(' -e 'subprocess.*shell=True' \
  -e '__import__' -e 'pickle.loads' -e 'yaml.load(' \
  -e 'os.system(' -e 'input(' \
  > /tmp/security-scan.txt 2>/dev/null

if [ -s /tmp/security-scan.txt ]; then
  echo "WARN: potential security issues in diff:"
  cat /tmp/security-scan.txt
  # Nezastavuj — ale zapiš do implement reportu jako "Security scan findings"
fi

# Quick reliability scan
git diff "${main_branch}...HEAD" -- '*.py' | grep -n \
  -e 'except:$' -e 'except Exception:$' \
  -e 'pass$' -e '# TODO' -e '# FIXME' -e '# HACK' \
  > /tmp/reliability-scan.txt 2>/dev/null

if [ -s /tmp/reliability-scan.txt ]; then
  echo "WARN: potential reliability issues in diff:"
  cat /tmp/reliability-scan.txt
fi
```

**Co kontrolovat (checklist):**
- [ ] Žádný `eval()`, `exec()`, `subprocess(shell=True)`, `pickle.loads()` bez sanitizace
- [ ] Žádný bare `except:` nebo `except Exception:` bez re-raise/logging
- [ ] Žádný `pass` v exception handleru (tiché polknutí chyb)
- [ ] Všechny nové I/O operace mají timeout
- [ ] Všechny nové user vstupy jsou validované

**Pokud scan najde ≥1 finding:** Zapiš do implement reportu sekci "## Security/Reliability Scan" s nálezem. Review to pak ověří hlouběji.
**Pokud scan je čistý:** Zapiš "Security/Reliability scan: clean (0 findings)".

> **Poznámka:** Toto NENAHRAZUJE fabric-review. Je to rychlý pre-screening, aby se kritické problémy chytly IHNED po implementaci, ne až v review dispatchi.

### 7) Update state (pouze wip)

Zapiš do `{WORK_ROOT}/state.md`:
- `wip_item: {id}`
- `wip_branch: {branch}`

> Nesahej na `phase` a `step`. To řeší orchestrátor.

### 8) Implement report (evidence)

Vytvoř `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md` jako kopii `{WORK_ROOT}/templates/report.md` a vyplň:

- Summary: co bylo dodáno (1–3 odrážky)
- Inputs: `{WORK_ROOT}/analyses/...` a backlog item
- Outputs: seznam změněných souborů (top 10) + odkaz na `git diff --stat`
- Evidence:
  - příkaz(y) spuštěné z configu (test/lint/format_check) + výsledek
  - pokud vznikl PR → link / ID
  - commit hash(y)
- Risks/Follow-ups: co zůstalo otevřené / co je potřeba dál


---

### Timeout handling

Spouštěj quality gate příkazy s timeoutem a **vždy kontroluj exit code**:

```bash
timeout 120 {COMMANDS.lint}
LINT_EXIT=$?
if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint exceeded 120s"; GATE_RESULT="TIMEOUT"; fi

timeout 120 {COMMANDS.format_check}
FMT_EXIT=$?
if [ $FMT_EXIT -eq 124 ]; then echo "TIMEOUT: format_check exceeded 120s"; GATE_RESULT="TIMEOUT"; fi

timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then echo "TIMEOUT: test exceeded 300s"; GATE_RESULT="TIMEOUT"; fi
```

- Pokud GATE_RESULT=TIMEOUT: zapiš do implement reportu `TIMEOUT` + který příkaz + délku.
- Auto-fix se nepokouší po timeoutu — rovnou FAIL s intake item `intake/implement-timeout-{date}.md`.
- Timeout exit code 124 NESMÍ být zaměněn za normální test failure (124 = killed by timeout, ne test FAIL).

---

## Self-check

**BLOCKING ENFORCEMENT (WQ10: CRITICAL findings MUST fail implementation):**

Před návratem — VŠECHNY položky MUSÍ být ✅:

- ❌ CRITICAL: Working tree DIRTY (git status shows changes) → **EXIT 1** (commit all changes first)
  ```bash
  if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: working tree not clean — commit or stash changes"
    exit 1
  fi
  ```
- ❌ CRITICAL: `COMMANDS.test` FAIL → **EXIT 1** (coverage metrics invalid, cannot proceed to review)
  ```bash
  timeout 300 {COMMANDS.test}
  TEST_EXIT=$?
  if [ $TEST_EXIT -ne 0 ]; then
    echo "ERROR: tests FAIL — fix before commit"
    exit 1
  fi
  ```
- ❌ CRITICAL: Coverage <60% for CORE modules (services/, api/, recall/, triage/) → **EXIT 1** (unacceptable, must add tests)
- ❌ CRITICAL: Backlog item status NOT `IN_REVIEW` after commit → **EXIT 1** (downstream review will skip)
- ❌ CRITICAL: Baseline tests were already failing → **EXIT 1** (do not introduce new regressions)
- ❌ CRITICAL: Stubs/pass/TODO found in production code → **EXIT 1** (incomplete implementation)

**Non-critical (warnings that don't fail, but document):**
- ⚠️ WARN: Coverage <60% for non-core modules (acceptable, but log)
- ⚠️ WARN: Lint/format skipped (bootstrap mode)
- ⚠️ WARN: Pre-existing fixups committed separately (note in report)

Pokud ne → **FAIL + vytvoř intake item `intake/implement-selfcheck-failed-{id}.md`**.

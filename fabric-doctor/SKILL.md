---
name: fabric-doctor
description: "Diagnose and fix code/test infrastructure issues that block the pipeline: flaky tests, import contamination, dependency errors, env pollution. Triggered when tests repeatedly fail for non-obvious reasons."
---
<!-- built from: builder-template -->

# DOCTOR — Diagnostika a oprava infrastrukturních problémů

---

## §1 — Účel

Diagnostikovat a opravit **kódové/testové infrastrukturní problémy**, které blokují pipeline a které nejsou řešitelné standardním fabric-implement cyklem. Bez DOCTORu loop opakovaně failuje na test (implement → test FAIL → implement → test FAIL...) protože implement nemá diagnostické heuristiky pro infrastrukturní root causes.

**Typické problémy:**
- Flaky testy (order-dependent, sys.modules contamination, fixture scope)
- Import/dependency errors (missing packages, proxy env vars, version incompatibilities)
- Test isolation failures (shared state, global mutations, module-level side effects)
- Configuration drift (env vars, config defaults, backend compatibility)

---

## §2 — Protokol (povinné — NEKRÁTIT)

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "doctor" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "doctor" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/doctor-{YYYY-MM-DD}-{run_id}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "doctor" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

```bash
# --- Path traversal guard (K7) ---
for VAR in "{WORK_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# Precondition 1: config.md existuje
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found"
  exit 1
fi

# Precondition 2: COMMANDS.test nakonfigurován
COMMANDS_TEST=$(grep 'COMMANDS.test:' "{WORK_ROOT}/config.md" | grep -v test_e2e | head -1 | sed 's/.*: //')
if [ -z "$COMMANDS_TEST" ] || [ "$COMMANDS_TEST" = "TBD" ]; then
  echo "STOP: COMMANDS.test not configured"
  exit 1
fi

# Precondition 3: evidence of test failure (doctor se volá když něco nefunguje)
# Buď existuje FAIL test report, nebo uživatel/loop explicitně volá doctor
LATEST_FAIL=$(ls -t {WORK_ROOT}/reports/test-*.md 2>/dev/null | head -1)
if [ -n "$LATEST_FAIL" ] && grep -q "status: FAIL" "$LATEST_FAIL"; then
  echo "Doctor triggered by: $LATEST_FAIL"
fi
```

**Dependency chain:** `fabric-test (FAIL) → [tento skill] → fabric-test (revalidace)`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (COMMANDS, cesty)
- `{CODE_ROOT}/` (zdrojový kód)
- `{TEST_ROOT}/` (testy)

### Volitelné (obohacují diagnostiku)
- `{WORK_ROOT}/reports/test-*.md` (poslední test reporty — evidence of failures)
- pytest výstup (stderr/stdout z posledního běhu)
- `{WORK_ROOT}/state.md` (wip_item context)

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/doctor-{YYYY-MM-DD}-{run_id}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Opravené soubory v `{CODE_ROOT}/` a `{TEST_ROOT}/` (s git commitem)
- Intake items: `{WORK_ROOT}/intake/doctor-{slug}.md` (pro problémy vyžadující větší zásah)

---

## §6 — Deterministic FAST PATH

Před LLM diagnostikou spusť automatické detektory:

```bash
# 1. Spusť testy a zachyť výstup
TIMEOUT_TEST=$(awk '/timeout_bounds:/,/^[^ ]/{if(/  test:/)print $2}' "{WORK_ROOT}/config.md")
TIMEOUT_TEST=${TIMEOUT_TEST:-300}
timeout "$TIMEOUT_TEST" {COMMANDS.test} > /tmp/doctor-test-full.log 2>&1
FULL_EXIT=$?
FULL_PASSED=$(grep -oP '\d+(?= passed)' /tmp/doctor-test-full.log | tail -1)
FULL_FAILED=$(grep -oP '\d+(?= failed)' /tmp/doctor-test-full.log | tail -1)
echo "Full suite: ${FULL_PASSED:-0} passed, ${FULL_FAILED:-0} failed (exit $FULL_EXIT)"

# 2. Pokud FAIL, identifikuj failing test soubory
if [ "${FULL_FAILED:-0}" -gt 0 ]; then
  FAILING_FILES=$(grep -E '^FAILED ' /tmp/doctor-test-full.log \
    | grep -oP '[\w/]+\.py' | sort -u)
  echo "Failing files: $FAILING_FILES"

  # 3. Spusť failing soubory IZOLOVANĚ
  for FILE in $FAILING_FILES; do
    timeout "$TIMEOUT_TEST" python -m pytest "$FILE" -v > "/tmp/doctor-isolated-$(basename $FILE).log" 2>&1
    ISO_EXIT=$?
    if [ $ISO_EXIT -eq 0 ]; then
      echo "ORDER-DEPENDENT: $FILE passes in isolation but fails in suite"
    else
      echo "GENUINE-FAIL: $FILE fails even in isolation"
    fi
  done
fi
```

---

## §7 — Postup (JÁDRO SKILLU)

### 7.1) Triage — Klasifikuj typ problému

**Co:** Rozděl failing testy do kategorií podle FAST PATH výsledků.

**Kategorie:**
1. **ORDER-DEPENDENT** — projde v izolaci, failne v suite → test isolation issue
2. **GENUINE-FAIL** — failne i v izolaci → kódový bug nebo missing dependency
3. **FLAKY** — občas projde, občas ne → nedeterminismus
4. **TIMEOUT** — exit code 124 → performance issue

**Jak:** Viz `references/triage-heuristics.md`

**Minimum:** Každý failing test musí mít přiřazenou kategorii.

---

### 7.2) Diagnostika — Root Cause Analysis per kategorie

**Co:** Pro každou kategorii aplikuj specifické diagnostické heuristiky.

**ORDER-DEPENDENT diagnostika:**
```bash
# Najdi test soubor, který kontaminuje
# Strategie: bisect — spouštěj failing file po každém jiném souboru
FAILING="$1"  # failing test file
ALL_FILES=$(python -m pytest --collect-only -q 2>/dev/null | grep '::' | cut -d: -f1 | sort -u)

for PREV_FILE in $ALL_FILES; do
  [ "$PREV_FILE" = "$FAILING" ] && continue
  python -m pytest "$PREV_FILE" "$FAILING" -v > /tmp/doctor-pair.log 2>&1
  if [ $? -ne 0 ]; then
    echo "CONTAMINATOR: $PREV_FILE contaminates $FAILING"
    break
  fi
done
```

**Poté inspekce kontaminátoru:**
- `sys.modules` manipulace (setdefault vs přímé přiřazení)
- Module-level side effects (import-time code execution)
- Fixture scope issues (session/module scope bez cleanup)
- Global state mutations (class variables, module globals)

**GENUINE-FAIL diagnostika:**
```bash
# Zachyť ImportError/ModuleNotFoundError
grep -E 'ImportError|ModuleNotFoundError|AttributeError' /tmp/doctor-isolated-*.log

# Zkontroluj env var interference
env | grep -iE 'proxy|socks|http_proxy|https_proxy|no_proxy'

# Zkontroluj package verze vs expected
pip list --format=json 2>/dev/null | python -c "
import json, sys
pkgs = json.load(sys.stdin)
for p in pkgs:
    if p['name'] in ['qdrant-client', 'httpx', 'pydantic', 'fastapi']:
        print(f\"{p['name']}=={p['version']}\")
"
```

**Detaily:** Viz `references/diagnostics.md`

**Minimum:** Root cause identifikován pro každý failing test.

---

### 7.3) Fix — Aplikuj opravu per root cause

**Co:** Oprav identifikovaný root cause. Každý fix typ má konkrétní pattern.

**Fix patterns (kanonické):**

| Root Cause | Fix Pattern |
|-----------|------------|
| sys.modules setdefault | Nahraď přímým přiřazením `sys.modules[key] = fake` |
| sys.modules no cleanup | Přidej fixture s `yield` + restore originals |
| httpx proxy env leak | `httpx.Client(trust_env=False)` |
| Missing package attribute | `getattr(module, attr, fallback)` |
| Fixture scope contamination | Zúži scope na `function` nebo přidej cleanup |
| Module-level import side effect | Přesuň import do fixture/function |
| Global state mutation | Přidej `autouse` fixture pro reset |

**Jak:** Pro každý fix:
1. Vytvoř fix na feature/doctor branch (nebo přímo na WIP branch pokud existuje)
2. Spusť testy — ověř, že fix opravuje failing test
3. Spusť CELÝ suite — ověř, že fix nezavádí regresi
4. Commitni s `fix(doctor): {popis root cause}`

**Anti-patterns:**
- Neignoruj failing test přes `@pytest.mark.skip` — to problém schová
- Neměň test assertion aby prošla s chybným výsledkem
- Nepřidávej `# noqa` na importy bez pochopení proč failují

**Minimum:** Všechny failing testy prochází po fixu, žádné regrese.

---

### 7.4) Prevence — Aktualizuj skills pro budoucí ochranu

**Co:** Pro každý opravený root cause ověř, který skill ho měl zachytit, a pokud chybí detekce, vytvoř intake item.

**Jak:**
```bash
# Pro každý fix, ověř zda fabric-test isolation check pokrývá tento pattern
# Pro každý fix, ověř zda fabric-implement quality gates pokrývají tento pattern
# Pokud ne → intake item pro rozšíření skillu
```

**Root cause → Responsible skill mapping:**

| Root Cause | Měl zachytit | Chybějící check |
|-----------|-------------|----------------|
| sys.modules contamination | fabric-test (isolation check) | Pattern pro sys.modules |
| httpx trust_env | fabric-implement (dependency check) | Proxy env var awareness |
| Package version mismatch | fabric-implement (baseline) | Version pinning check |
| Fixture scope leak | fabric-test (isolation check) | Fixture scope analysis |

**Minimum:** Každý fix má mapovaný responsible skill + intake item pokud chybí prevence.

---

### K10: Concrete Example — LLMem sys.modules Contamination Fix

```
Doctor triggered by: test_fail_count=2 (threshold), 2 tests failing in suite

FAST PATH:
  Full suite: 1054 passed, 2 failed (exit 1)
  Failing: test_qdrant_sensitivity_filter.py::test_search_includes_pii_by_default
           test_qdrant_sensitivity_filter.py::test_search_all_sensitivities_when_allowed
  Isolated: pytest tests/test_qdrant_sensitivity_filter.py → 6/6 PASS
  Category: ORDER-DEPENDENT

TRIAGE:
  Bisect: pytest test_qdrant_knowledge_collection.py test_qdrant_sensitivity_filter.py → 2 FAIL
  Contaminator: test_qdrant_knowledge_collection.py

DIAGNOSTIKA:
  grep -n sys.modules test_qdrant_sensitivity_filter.py → line 101-103: setdefault()
  grep -n sys.modules test_qdrant_knowledge_collection.py → line 129-131: direct assignment
  Root cause: knowledge_collection uses sys.modules[key]=fake (overwrites),
              sensitivity_filter uses sys.modules.setdefault(key,fake) (keeps stale).
              When KC runs first, its MagicMock fakes persist. SF's setdefault is no-op.

FIX:
  Replace setdefault → direct assignment in test_qdrant_sensitivity_filter.py
  + same fix in test_qdrant_backend.py and test_qdrant_tier_type_scope_filter.py (same pattern)
  Post-fix: 1056 passed, 0 failed, 0 regressions

PREVENCE:
  fabric-test: Added sys.modules pattern to Test Isolation Check (Pattern 4-5)
  fabric-implement: Added sys.modules anti-pattern to coding guidelines
  → intake: chore-test-isolation-audit (audit ALL test files for setdefault)
```

### K10: Anti-patterns (s detekcí)
```bash
# A1: Marking test as @skip instead of fixing root cause
# DETECTION:
git diff --name-only | xargs grep -l '@pytest.mark.skip' 2>/dev/null
# FIX: Never skip as "fix" — diagnose and repair the actual issue

# A2: Changing assertion to match wrong result
# DETECTION:
git diff --stat | grep "assert" | head -5
# FIX: Fix the code/test infrastructure, not the assertion

# A3: Fix without regression check (post-fix suite run)
# DETECTION: doctor report missing "Post-fix: X passed, 0 failed" line
grep -c "Post-fix.*passed.*0 failed" {WORK_ROOT}/reports/doctor-*.md
# FIX: ALWAYS run full suite after fix, compare with pre-fix counts

# A4: Fix attempt without persisted counter (unbounded retries)
# DETECTION: no fix_attempt_count in backlog item
grep 'fix_attempt_count:' "{WORK_ROOT}/backlog/${WIP_ITEM}.md" || echo "MISSING"
# FIX: Persist counter, enforce max=3 from config
```

### Counter Persistence (K2 compliance)
```bash
# Read fix_attempt_count from backlog item (persisted across ticks)
FIX_ATTEMPTS=$(grep 'fix_attempt_count:' "{WORK_ROOT}/backlog/${WIP_ITEM}.md" 2>/dev/null | awk '{print $2}')
FIX_ATTEMPTS=${FIX_ATTEMPTS:-0}
if ! echo "$FIX_ATTEMPTS" | grep -qE '^[0-9]+$'; then FIX_ATTEMPTS=0; fi
MAX_FIX=3

if [ "$FIX_ATTEMPTS" -ge "$MAX_FIX" ]; then
  echo "STOP: fix_attempt_count ($FIX_ATTEMPTS) >= max ($MAX_FIX)"
  # → intake item, manuální intervence
  exit 1
fi

# Increment after each fix attempt
NEW_COUNT=$((FIX_ATTEMPTS + 1))
sed -i "s/^fix_attempt_count:.*/fix_attempt_count: $NEW_COUNT/" "{WORK_ROOT}/backlog/${WIP_ITEM}.md"
```

---

## §8 — Quality Gates

### Gate 1: All previously failing tests PASS
```bash
timeout "$TIMEOUT_TEST" {COMMANDS.test} > /tmp/doctor-post-fix.log 2>&1
POST_EXIT=$?
POST_FAILED=$(grep -oP '\d+(?= failed)' /tmp/doctor-post-fix.log | tail -1)
if [ "${POST_FAILED:-0}" -gt 0 ]; then
  echo "FAIL: ${POST_FAILED} tests still failing after doctor fix"
  exit 1
fi
```

### Gate 2: No regressions introduced
```bash
POST_PASSED=$(grep -oP '\d+(?= passed)' /tmp/doctor-post-fix.log | tail -1)
if [ "${POST_PASSED:-0}" -lt "${FULL_PASSED:-0}" ]; then
  echo "FAIL: regression — was ${FULL_PASSED} passed, now ${POST_PASSED}"
  exit 1
fi
```

---

## §9 — Report

`{WORK_ROOT}/reports/doctor-{YYYY-MM-DD}-{run_id}.md`:

```md
---
schema: fabric.report.v1
kind: doctor
step: "doctor"
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# Doctor Report {YYYY-MM-DD}

## Souhrn
{1–3 věty: kolik testů opraveno, jaké root causes}

## Diagnostika

| Test | Kategorie | Root Cause | Fix |
|------|-----------|-----------|-----|
| {test_name} | ORDER-DEPENDENT | sys.modules setdefault | Direct assignment |

## Prevence
{Intake items vytvořené pro skill prevention gaps}

## Evidence
- Pre-fix: {X} passed, {Y} failed
- Post-fix: {Z} passed, 0 failed
- Regressions: none
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

- [ ] Report exists with schema: `{WORK_ROOT}/reports/doctor-{YYYY-MM-DD}-{run_id}.md`
- [ ] All failing tests PASS: post-fix count = 0 failures
- [ ] Zero regressions: post-fix passed ≥ pre-fix passed
- [ ] Each fix has root cause identified in report
- [ ] Fixes are code, not assertion tweaks
- [ ] Git commit with `fix(doctor):` prefix exists
- [ ] NO @pytest.mark.skip added
- [ ] Working tree clean (only reports/ modified)

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| FAST PATH | Testy PASS (žádný problém) | Report PASS + skip |
| Triage | Nelze klasifikovat | WARN + intake item |
| Diagnostika | Root cause neidentifikován | WARN + intake item pro manuální debug |
| Fix | Fix neopravuje test | Zkus další heuristiku (max 3 iterace) → FAIL + intake |
| Fix | Fix zavádí regresi | Revert fix → FAIL + intake item |
| Prevence | Skill nelze aktualizovat (no-fix list) | Intake item pro manuální úpravu |

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
phase: utility
step: doctor
may_modify_state: false
may_modify_backlog: false
may_modify_code: true
may_create_intake: true

depends_on: [fabric-init]
feeds_into: [fabric-test]
```

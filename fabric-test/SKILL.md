---
name: fabric-test
description: "Run configured test suites for current WIP task and write evidence report. Uses COMMANDS.test and optional COMMANDS.test_e2e without modifying code. Fails fast on missing config, ensuring measurable test results."
---

<!-- built from: builder-template -->

# TEST — Spuštění testů (evidence)

## §1 — Účel

Spustit testy definované v `{WORK_ROOT}/config.md` a vytvořit report s evidencí pro další kroky (review/close). Bez TESTu se change nevhodnotí objektivně — výsledek je vágní guess místo měřené evidence.

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci zapiš události do protokolu:

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "test" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "test" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/test-{wip_item}-{YYYY-MM-DD}-{run_id}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "test" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

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

# Precondition 2: state.md existuje
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found"
  exit 1
fi

# Precondition 3: wip_item + wip_branch + backlog file
WIP_ITEM=$(python skills/fabric-init/tools/fabric.py state-get --field wip_item 2>/dev/null)
WIP_BRANCH=$(python skills/fabric-init/tools/fabric.py state-get --field wip_branch 2>/dev/null)

if [ -z "$WIP_ITEM" ] || [ "$WIP_ITEM" = "null" ]; then
  echo "STOP: state.wip_item not set — run fabric-implement first"
  exit 1
fi

if [ ! -f "{WORK_ROOT}/backlog/${WIP_ITEM}.md" ]; then
  echo "STOP: backlog file missing for wip_item=$WIP_ITEM"
  python skills/fabric-init/tools/fabric.py intake-new --source "test" --slug "missing-backlog-file" \
    --title "Backlog file not found: backlog/${WIP_ITEM}.md"
  exit 1
fi

if ! git rev-parse --verify "$WIP_BRANCH" >/dev/null 2>&1; then
  echo "STOP: branch $WIP_BRANCH does not exist in git"
  python skills/fabric-init/tools/fabric.py intake-new --source "test" --slug "missing-branch" \
    --title "Git branch not found: $WIP_BRANCH"
  exit 1
fi

# Precondition 4: COMMANDS.test je vyplněno
COMMANDS_TEST=$(grep 'COMMANDS.test:' "{WORK_ROOT}/config.md" | grep -v test_e2e | head -1 | sed 's/.*: //')
if [ -z "$COMMANDS_TEST" ] || [ "$COMMANDS_TEST" = "TBD" ]; then
  echo "STOP: COMMANDS.test not configured in config.md"
  exit 1
fi

# Precondition 5: git working tree musí být čistý
if [ -n "$(git status --porcelain)" ]; then
  echo "STOP: git working tree is not clean — commit or stash changes"
  exit 1
fi
```

**Dependency chain:** `fabric-implement → fabric-test`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (COMMANDS.test, volitelně COMMANDS.test_e2e)
- `{WORK_ROOT}/state.md` (wip_item, wip_branch)
- `{WORK_ROOT}/backlog/{wip_item}.md`
- Git branch `{state.wip_branch}` (musí existovat)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/templates/test-report.md` (pokud existuje)

---

## §5 — Výstupy

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/test-{wip_item}-{YYYY-MM-DD}-{run_id}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/test-*.md` (pro chybějící prereq, timeout, flaky testy)

---

## §6 — Deterministic FAST PATH

Deterministické kroky PŘED LLM prací — neplytvej tokeny parsováním a strukturováním:

```bash
# 1. State validation — check phase compatibility
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
if [ "$CURRENT_PHASE" != "implementation" ]; then
  echo "WARN: phase is '$CURRENT_PHASE', expected 'implementation' — proceeding anyway"
fi

# 2. Spusť testy deterministicky (gate-test vytvoří parsovatelný report)
python skills/fabric-init/tools/fabric.py gate-test --tail 200
GATE_EXIT=$?

if [ $GATE_EXIT -eq 0 ]; then
  RESULT="PASS"
else
  RESULT="FAIL"
fi

echo "FAST PATH complete: RESULT=$RESULT"
```

---

## §7 — Postup (JÁDRO SKILLU)

### 7.1) Checkout branch a ověř čistý stav

**Co:** Checkout na WIP branch, ověř, že pracovní strom je čistý (testy musí běžet na čistém stavu).

**Jak:**
```bash
git checkout "${WIP_BRANCH}"
git status --porcelain
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree not clean after checkout"
  exit 1
fi
```

**Minimum:** Branch checkout bez chyby, žádné uncommitted changes.

**Anti-patterns:**
- Nespouštět testy na dirty tree (vede na falešné failure)
- Commit kódu během tестu (fabric-test je read-only)

---

### 7.2) Spusť deterministic gate-test

**Co:** Spusť testy přes `fabric.py gate-test`, který vezme COMMANDS.test, uloží log, vytvoří parsovatelný report.

**Jak:**
```bash
python skills/fabric-init/tools/fabric.py gate-test --tail 200
TEST_EXIT=$?

if [ $TEST_EXIT -eq 0 ]; then
  TEST_RESULT="PASS"
else
  TEST_RESULT="FAIL"
fi
```

**Minimum:** Report v `{WORK_ROOT}/reports/test-*.md` s řádkem `Result: PASS` nebo `Result: FAIL`.

**Anti-patterns:**
- Ignorovat exit code
- Parsovat výstup ručně místo použití gate-test

---

### 7.3) Volitelně: Spusť E2E testy

**Co:** Pokud config má COMMANDS.test_e2e (a není TBD), spusť E2E po unit/integration testech.

**Jak:**
```bash
COMMANDS_E2E=$(grep 'COMMANDS.test_e2e:' "{WORK_ROOT}/config.md" | sed 's/.*: //')

if [ -n "$COMMANDS_E2E" ] && [ "$COMMANDS_E2E" != "TBD" ]; then
  timeout 600 $COMMANDS_E2E
  E2E_EXIT=$?

  if [ $E2E_EXIT -eq 124 ]; then
    E2E_RESULT="TIMEOUT"
    # → intake item pro slow E2E
  elif [ $E2E_EXIT -ne 0 ]; then
    E2E_RESULT="FAIL"
  else
    E2E_RESULT="PASS"
  fi
else
  E2E_RESULT="SKIPPED"
fi
```

**Minimum:** E2E report nebo SKIPPED status v report.

---

### 7.4) Analyzuj report a doplň interpretaci

**Co:** Načti `gate-test` report, extrahuj metriky (passed/failed/errors/skipped), analyzuj root cause, doplň strukturovanou interpretaci.

**Jak (viz references/workflow.md § Analýza výstupu):**
- Parsuj test summary (passed/failed/error counts)
- Pokud FAIL: aplikuj heuristics (single module? spanning modules? timeout?)
- Pokud PASS: shrň što pokrývaly, coverage story
- Doplň Coverage Metrics (target ≥60% core modules)
- Doplň Test Isolation check (detekuj shared state)
- Doplň Test/Code LOC ratio

**Minimum:**
- Test summary (X passed, Y failed, Z errors)
- Root cause (pokud FAIL)
- Coverage percentage
- Minimálně 1–2 věty interpreace v Notes sekcí

**Anti-patterns:**
- Prázdný Notes (skill violation)
- Ignorovat low LOC ratio (<30%)
- Nedetekovat timeout (exit code 124 ≠ assertion failure)

---

### 7.5) Vytvoř finální report

**Co:** Doplň gate-test skeleton s interpretací, vytvoř report v schématu `fabric.report.v1`.

**Jak:** Viz references/examples.md (příklad vyplněného test reportu).

**Minimum:**
```md
---
schema: fabric.report.v1
kind: test
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

## Souhrn
{1–3 věty: test suite + PASS/FAIL verdict + coverage/isolation notes}

## Test Results
{Structured: passed/failed/error/skipped counts}

## Coverage Analysis
{coverage_pct, test/code LOC ratio, possibly warnings}

## Flakiness
{Detected flaky tests or "none"}

## Notes
{Interpretation: what was tested, any regressions, next action if FAIL}
```

---

## §8 — Quality Gates (pokud skill má gates)

Skill sám neimplementuje code — jen testuje. Neexistují quality gates na skill výstup.

Ale **testy MUSÍ PASS** — pokud gate-test vrátí FAIL, report status je FAIL a skill nesmí pokračovat.

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/test-{wip_item}-{YYYY-MM-DD}-{run_id}.md`:

Viz§5 Výstupy (schéma) a references/examples.md (konkrétní příklad).

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/test-{wip_item}-{YYYY-MM-DD}-{run_id}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Protocol log má START záznam s `skill: test`
- [ ] Protocol log má END záznam s `skill: test` a status OK/WARN/FAIL/ERROR

### Quality checks
- [ ] Report obsahuje povinné sekce: Souhrn, Test Results, Coverage Analysis, Notes
- [ ] **Notes sekce je neprázdná** — alespoň 1–2 věty interpretace
- [ ] Pokud FAIL, report obsahuje root cause heuristic + next action
- [ ] Pokud PASS, report popisuje, co bylo testováno + coverage trend
- [ ] **version/schema field present** v YAML frontmatter

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován
- [ ] Git branch `{state.wip_branch}` zůstává `HEAD` (né checkout jinde)
- [ ] Backlog item `{WORK_ROOT}/backlog/{wip_item}.md` není smazán

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí backlog/branch | STOP + jasná zpráva |
| FAST PATH | gate-test FAIL | Pokračuj do analýzy, report FAIL |
| gate-test timeout | Timeout 300s | Report WARN + intake pro slow tests |
| Self-check FAIL | Prázdný Notes | Report WARN + intake pro fix |

**Obecné pravidlo:** Skill fail-open na VOLITELNÉ vstupy (E2E timeout → WARN), fail-fast na POVINNÉ (backlog chybí → STOP).

---

## §12 — Metadata

```yaml
phase: implementation
step: test_evidence
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true

depends_on: [fabric-implement]
feeds_into: [fabric-review, fabric-close]
```

---

# Přílohy

- references/workflow.md — Detailní postup (§7 rozšířeno)
- references/examples.md — Příklad reportu + katalog anti-patterns

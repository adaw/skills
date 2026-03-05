---
name: fabric-test
description: "Run the configured test suites for the current WIP task (state.wip_item) and write an evidence report. Uses COMMANDS.test (and optionally COMMANDS.test_e2e). Does not modify code. Fails fast on missing config commands."
---

# TEST — Spuštění testů (evidence)

## Účel

Spustit testy definované v `{WORK_ROOT}/config.md` a vytvořit report s evidencí pro další kroky (review/close).

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-test" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-test" --event end --status OK --report "{WORK_ROOT}/reports/test-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy

- `{WORK_ROOT}/config.md` (COMMANDS.test, volitelně test_e2e)
- `{WORK_ROOT}/state.md` (wip_item)
- `{WORK_ROOT}/backlog/{wip_item}.md`
- repo working tree (aktuální branch je `{state.wip_branch}`)

---

## Výstupy

- `{WORK_ROOT}/reports/test-*.md` *(vytváří deterministicky `fabric.py gate-test`; ty jen doplňuješ interpretaci)*

---

## Preconditions

- `state.wip_item` musí být vyplněné
- `COMMANDS.test` musí být vyplněné a nesmí být `TBD`
- `state.wip_branch` musí existovat jako git branch

Pokud není splněno:
- vytvoř intake item `intake/test-missing-wip-or-commands.md`
- FAIL

### File & branch existence checks (povinné)

```bash
WIP_ITEM=$(python skills/fabric-init/tools/fabric.py state-get --field wip_item 2>/dev/null)
WIP_BRANCH=$(python skills/fabric-init/tools/fabric.py state-get --field wip_branch 2>/dev/null)

# 1. wip_item musí mít backlog soubor
if [ ! -f "{WORK_ROOT}/backlog/${WIP_ITEM}.md" ]; then
  echo "STOP: backlog file missing for wip_item=$WIP_ITEM"
  python skills/fabric-init/tools/fabric.py intake-new --source "test" --slug "missing-backlog-file" \
    --title "Backlog file not found: backlog/${WIP_ITEM}.md"
  exit 1
fi

# 2. wip_branch musí existovat v git
if ! git rev-parse --verify "$WIP_BRANCH" >/dev/null 2>&1; then
  echo "STOP: branch $WIP_BRANCH does not exist in git"
  python skills/fabric-init/tools/fabric.py intake-new --source "test" --slug "missing-branch" \
    --title "Git branch not found: $WIP_BRANCH"
  exit 1
fi
```

> `COMMANDS.test_e2e` je volitelné:
> - `""` nebo `TBD` = nespouštěj
> - cokoliv jiného = spusť po unit/integration testech

---


## FAST PATH (doporučeno) — testy deterministicky + log capture

Místo ručního spouštění příkazů používej deterministický gate `gate-test`, který:

- vezme `COMMANDS.test` z configu,
- uloží plný log do `{WORK_ROOT}/logs/commands/`,
- vytvoří **parsovatelný** test report (povinné pro `tick` gating),
- a vrátí JSON shrnutí (Result + cesty).

```bash
python skills/fabric-init/tools/fabric.py gate-test --tail 200
```

Volitelně E2E (pokud má projekt `COMMANDS.test_e2e`):
```bash
python skills/fabric-init/tools/fabric.py run test_e2e --tail 200
```

---

## Postup

1. Načti `state.md` → `id = wip_item`, `branch = wip_branch`
2. Checkoutni branch (bez změn):
   ```bash
   git status --porcelain
   git checkout "${branch}"
   ```
   Pokud working tree není čistý → FAIL (testy musí běžet na čistém stavu)
3. Spusť testy deterministicky:

   ```bash
   python skills/fabric-init/tools/fabric.py gate-test --tail 200
   ```

   Tím vznikne report v `{WORK_ROOT}/reports/` s řádkem `Result: PASS` nebo `Result: FAIL` (BEZ leading dash — kanonický formát pro fabric-loop verdict parsing).
4. Pokud `COMMANDS.test_e2e` není prázdné **a zároveň není `TBD`**, spusť i E2E (volitelně):
   ```bash
   {COMMANDS.test_e2e}
   ```
5. Analyzuj výstup (structured failure analysis):
   - Parsuj stderr/stdout pro klíčové signály:
     - test runner summary (např. `X passed, Y failed, Z errors`)
     - konkrétní failing test names + assertion message
     - stack trace → identifikuj soubor a řádek
   - Pokud test runner generuje structured output (JUnit XML, pytest JSON), parsuj ho přednostně
   - Pro každý failing test zapiš:
     - `test_name`, `file:line`, `error_type`, zkrácený `message` (max 3 řádky)
   - Pokud FAIL count > 20, zapiš jen top 10 + „… and {N} more"
6. Doplň report (**povinné** — NESMÍ zůstat prázdné):
   - přidej structured failures (viz krok 5)
   - pokud FAIL: napiš *nejpravděpodobnější root cause* + *next action*
   - pokud PASS: napiš **minimálně 1–2 věty** shrnutí: kolik testů, co pokrývají, jaké moduly/soubory byly testovány
   - **Notes sekce NESMÍ být prázdná** — `gate-test` vytvoří skeleton, ale ty MUSÍŠ doplnit interpretaci

> **Poznámka:** `gate-test` report vytvoří automaticky. Ty **musíš** doplnit interpretaci — prázdný Notes/Failures je skill violation.

---

## Report template

Použij `{WORK_ROOT}/templates/test-report.md` (vytvořeno přes `report-new`).

---

### Timeout a hanging testy

Spouštěj s timeoutem a **vždy kontroluj exit code**:

```bash
timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then
  RESULT="TIMEOUT"
  ROOT_CAUSE="Test runner timeout after 300s"
elif [ $TEST_EXIT -ne 0 ]; then
  RESULT="FAIL"
else
  RESULT="PASS"
fi
```

Pro `test_e2e` (explicitně):
```bash
if [ -n "{COMMANDS.test_e2e}" ] && [ "{COMMANDS.test_e2e}" != "TBD" ]; then
  timeout 600 {COMMANDS.test_e2e}
  E2E_EXIT=$?
  if [ $E2E_EXIT -eq 124 ]; then
    E2E_RESULT="TIMEOUT"
    E2E_ROOT_CAUSE="E2E test runner timeout after 600s"
  elif [ $E2E_EXIT -ne 0 ]; then
    E2E_RESULT="FAIL"
  else
    E2E_RESULT="PASS"
  fi
fi
```

- TIMEOUT se hodnotí jako FAIL s `root_cause: "Test runner timeout after {N}s"`.
- TIMEOUT NESMÍ být zaměněn za normální FAIL (jiný root cause, jiná remediace).
- Vytvoř intake item `intake/test-timeout-{date}.md` s doporučením: identifikovat pomalé testy, zvážit paralelizaci nebo test split.

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/`
- **Notes sekce je neprázdná** (alespoň 1 věta)
- pokud FAIL, report obsahuje aspoň 1 jasný root cause nebo next action
- pokud PASS, report říká kolik testů prošlo a co pokrývaly

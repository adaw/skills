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

Pokud není splněno:
- vytvoř intake item `intake/test-missing-wip-or-commands.md`
- FAIL

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
   git checkout {branch}
   ```
   Pokud working tree není čistý → FAIL (testy musí běžet na čistém stavu)
3. Spusť testy deterministicky:

   ```bash
   python skills/fabric-init/tools/fabric.py gate-test --tail 200
   ```

   Tím vznikne report v `{WORK_ROOT}/reports/` s řádkem `- Result: PASS` nebo `- Result: FAIL`.
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
6. Doplň report (volitelné, ale doporučené):
   - přidej structured failures (viz krok 5)
   - pokud FAIL: napiš *nejpravděpodobnější root cause* + *next action*
   - pokud PASS: napiš 1 větu „co testy pokrývaly“

> **Poznámka:** `gate-test` report vytvoří automaticky. Ty jen doplňuješ interpretaci.

---

## Report template

Použij `{WORK_ROOT}/templates/test-report.md` (vytvořeno přes `report-new`).

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/`
- pokud FAIL, report obsahuje aspoň 1 jasný root cause nebo next action

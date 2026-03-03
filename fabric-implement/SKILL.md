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
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-implement" --event end --status OK --report "{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}.md"`

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
- `{WORK_ROOT}/decisions/*.md` (architektonická omezení — implementace NESMÍ porušovat accepted decisions)
- `{WORK_ROOT}/specs/*.md` (technické kontrakty — kód MUSÍ odpovídat specifikacím)

Volitelné:
- předchozí `reports/review-*.md` (pokud jde o rework)

---

## Výstupy

- git branch s commit(y)
- aktualizovaný backlog item `{WORK_ROOT}/backlog/{id}.md`:
  - `status: IN_PROGRESS` během práce
  - `status: IN_REVIEW` po úspěšném commit + passing checks
  - `branch: <branch-name>`
  - `updated: <YYYY-MM-DD>`
- update `{WORK_ROOT}/state.md` (pouze):
  - `wip_item`
  - `wip_branch`

- `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}.md` (vytvoř jako kopii `{WORK_ROOT}/templates/report.md`; shrň změny, test evidence, commit hash, otevřený PR/Review)

---

## Preconditions (fail fast)

1. `{CODE_ROOT}/` musí existovat.
2. V configu musí být vyplněno:

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

Git kroky:

```bash
git status --porcelain
git fetch --all --prune
git checkout {main_branch}
git pull --ff-only
git checkout -b {branch_name} || git checkout {branch_name}
```

Pokud working tree není čistý → FAIL (nejdřív vyřeš).

### 3) VERIFY-FIRST (pochop problém + constraints)

- Přečti `{WORK_ROOT}/backlog/{id}.md` (AC + dotčené soubory)
- Pokud existuje `{ANALYSES_ROOT}/{id}-analysis.md`, použij ho jako plán.
- Přečti `{WORK_ROOT}/decisions/*.md` — identifikuj which accepted decisions ovlivňují tento task.
- Přečti `{WORK_ROOT}/specs/*.md` — identifikuj relevantní specs (API kontrakt, schéma, formáty).
- Pokud implementace by porušila decision nebo spec → STOP, vytvoř intake item `intake/constraint-violation-{id}.md` a reportuj.

Udělej baseline:
```bash
{COMMANDS.test}
```

Pokud baseline selže:
- nezaváděj nový kód
- vytvoř intake item `intake/baseline-tests-failing.md` (je to blocker)
- FAIL

### 4) Implementuj minimální změnu

- uprav jen nezbytné soubory v `{CODE_ROOT}/`
- přidej/aktualizuj testy v `{TEST_ROOT}/` tak, aby AC byly verifikovatelné
- pokud se mění veřejné chování, připrav změnu docs (docs step to může dokončit)

Během práce nastav backlog status:
- `status: IN_PROGRESS`
- `updated: {YYYY-MM-DD}`

### 5) Run quality gates (must pass)

Spusť quality commands v tomto pořadí:

- Lint (pokud `COMMANDS.lint` není prázdné)
- Format check (pokud `COMMANDS.format_check` není prázdné)
- Tests (vždy)

```bash
# lint (optional)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi

# format check (optional)
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi

# tests (required)
{COMMANDS.test}
```

Pokud format check failne a config má `COMMANDS.format`, můžeš spustit auto-format a znovu `format_check`.

Pokud něco selže:
- neopouštěj branch
- oprav (v rámci stejného tasku)
- opakuj gates

### 6) Commit

Commit message musí obsahovat ID:
- `feat({id}): ...` nebo `fix({id}): ...`

```bash
git add -A
git commit -m "feat({id}): {short description}"
```

Po commit:
- nastav backlog item `status: IN_REVIEW`
- doplň `updated: {YYYY-MM-DD}`

### 7) Update state (pouze wip)

Zapiš do `{WORK_ROOT}/state.md`:
- `wip_item: {id}`
- `wip_branch: {branch}`

> Nesahej na `phase` a `step`. To řeší orchestrátor.

### 8) Implement report (evidence)

Vytvoř `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}.md` jako kopii `{WORK_ROOT}/templates/report.md` a vyplň:

- Summary: co bylo dodáno (1–3 odrážky)
- Inputs: `{WORK_ROOT}/analyses/...` a backlog item
- Outputs: seznam změněných souborů (top 10) + odkaz na `git diff --stat`
- Evidence:
  - příkaz(y) spuštěné z configu (test/lint/format_check) + výsledek
  - pokud vznikl PR → link / ID
  - commit hash(y)
- Risks/Follow-ups: co zůstalo otevřené / co je potřeba dál


---

## Self-check

Před návratem:
- working tree čistý (`git status` nic)
- `COMMANDS.test` PASS
- backlog item aktualizovaný (branch/status/updated)
- implement report existuje v `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}.md`
- žádná accepted decision nebyla porušena
- implementace odpovídá relevantním specs (API formát, schéma, kontrakty)

Pokud ne → FAIL + vytvoř intake item `intake/implement-selfcheck-failed-{id}.md`.

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

- git branch s commit(y)
- aktualizovaný backlog item `{WORK_ROOT}/backlog/{id}.md`:
  - `status: IN_PROGRESS` během práce
  - `status: IN_REVIEW` po úspěšném commit + passing checks
  - `branch: <branch-name>`
  - `updated: <YYYY-MM-DD>`
- update `{WORK_ROOT}/state.md` (pouze):
  - `wip_item`
  - `wip_branch`

- `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md` (vytvoř jako kopii `{WORK_ROOT}/templates/report.md`; shrň změny, test evidence, commit hash, otevřený PR/Review)

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
timeout 60 git fetch --all --prune || echo "WARN: git fetch failed/timeout (network?), continuing with local state"
git checkout {main_branch}
git pull --ff-only || echo "WARN: pull failed, using local main"
git checkout -b {branch_name} || git checkout {branch_name}
```

**Post-checkout validace (povinné):**
```bash
# Ověř, že nejsme v detached HEAD
if [ "$(git rev-parse --abbrev-ref HEAD)" != "{branch_name}" ]; then
  echo "ERROR: detached HEAD or checkout failed"; exit 1
fi
# Pokud branch existuje na remote, synchronizuj
if git ls-remote --heads origin {branch_name} | grep -q {branch_name}; then
  git pull --ff-only origin {branch_name} || echo "WARN: remote diverged, using local"
fi
```

Pokud working tree není čistý → FAIL (nejdřív vyřeš).

### 3) VERIFY-FIRST (pochop problém)

- Přečti `{WORK_ROOT}/backlog/{id}.md` (AC + dotčené soubory)
- Pokud existuje `{ANALYSES_ROOT}/{id}-analysis.md`, použij ho jako plán.

Udělej baseline:
```bash
{COMMANDS.test}
```

Pokud baseline selže:
- nezaváděj nový kód
- vytvoř intake item `intake/baseline-tests-failing.md` (je to blocker)
- FAIL

#### 3.1) Governance compliance (VERIFY-FIRST)

- Otevři `{ANALYSES_ROOT}/{id}-analysis.md` a najdi sekci **Constraints**.
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

#### Auto-fix (pokud gates failnou)

Pokud lint nebo format check failne a config má příslušný fix příkaz, **spusť auto-fix a opakuj gate**:

1. **Lint fail** + `COMMANDS.lint_fix` není prázdné → spusť `timeout 120 {COMMANDS.lint_fix}` (exit 124 = timeout → FAIL, nepokouš se znovu), pak znovu `{COMMANDS.lint}`.
2. **Format fail** + `COMMANDS.format` není prázdné → spusť `timeout 120 {COMMANDS.format}` (exit 124 = timeout → FAIL), pak znovu `{COMMANDS.format_check}`.

Pokud lint/format fail a příslušný fix příkaz **je prázdný** (`""`) → auto-fix není možný. Vytvoř intake item `intake/implement-recommend-lint-fix-command.md` (jednorázově, jen pokud ještě neexistuje) a oprav chyby manuálně.

Auto-fix smí proběhnout **max 1×** per gate per implement run. Pokud po auto-fixu gate stále failne → oprav manuálně (v rámci stejného tasku).

#### Separace pre-existing fixů (povinné)

Pokud auto-fix opravil soubory, rozliš, které změny patří k tasku a které jsou pre-existing:

```bash
# zjisti, které soubory opravil auto-fix, ale NEJSOU v diff tasku
git diff --name-only {main_branch}...HEAD > /tmp/task-files.txt
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

Před návratem:
- working tree čistý (`git status` nic)
- `COMMANDS.test` PASS
- backlog item aktualizovaný (branch/status/updated)
- implement report existuje v `{WORK_ROOT}/reports/implement-{wip_item}-{YYYY-MM-DD}-{run_id}.md`

Pokud ne → FAIL + vytvoř intake item `intake/implement-selfcheck-failed-{id}.md`.

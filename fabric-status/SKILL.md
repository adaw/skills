---
name: fabric-status
description: "Produce a holistic project health snapshot (codebase, tests, backlog, docs, CI/tooling). Language-agnostic by default: detects dominant file types, uses configured COMMANDS for tests, lint, format_check, and summarizes risks/trends. Outputs a dashboard-style status report."
---

# STATUS — Health snapshot (holisticky)

## Účel

Vytvořit rychlý, ale použitelný „dashboard“:
- codebase signály (velikost, churn proxy),
- test zdraví (PASS/FAIL + evidence),
- backlog stav (flow, WIP),
- docs drift,
- rizika pro další sprint.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-status" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-status" --event end --status OK --report "{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy

- `{WORK_ROOT}/config.md` (COMMANDS, cesty)
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/backlog.md` + backlog items
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/`
- `{WORK_ROOT}/reports/status-*.md` (pro trend)

---

## Výstupy

- `{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md`

---


## FAST PATH (doporučeno) — deterministický snapshot

Než začneš psát report, vyrob strojový snapshot (git + code stats + backlog stats + COMMANDS test/lint/format_check s log capture):

```bash
python skills/fabric-init/tools/fabric.py snapshot-status --out "{WORK_ROOT}/reports/status-snapshot-{YYYY-MM-DD}.json" --tail 120
```

Pak report stav podle dat ze snapshotu (ne odhadem).

---

## Postup

### 1) Zjisti dominantní typy souborů (language-agnostic)

Použij `git ls-files` (pokud repo je git) nebo `find` fallback:

- vytvoř histogram přípon v `{CODE_ROOT}/` (ignoruj `{TEST_ROOT}/`, `{DOCS_ROOT}/`, vendory)
- top 3 extensions použij jako proxy pro jazyk (např. `.py`, `.ts`, `.go`)

Reportuj:
- top extensions
- počet souborů (code)
- hrubé LOC (sum `wc -l` pro top extension soubory)

> Nejde o perfektní LOC, jde o trend.

**MINIMUM:** tabulka s: Extension, Count (files), Approx LOC

### 2) Test health (objektivní)

Z configu načti:
- `COMMANDS.test`
- volitelně `COMMANDS.test_e2e`

Pokud `COMMANDS.test` je `TBD` nebo prázdné (`""`):
- označ test status jako `UNKNOWN` a vytvoř WARNING v reportu

Jinak spusť:
```bash
{COMMANDS.test}
```

Reportuj:
- PASS/FAIL
- (pokud fail) 1–3 nejpravděpodobnější root causes + next action

**MINIMUM:** Status: {PASS|FAIL|UNKNOWN|SKIPPED}, Evidence (pass/fail count), Exit code

### 3) Lint/format health

Z configu načti:
- `COMMANDS.lint`
- `COMMANDS.format_check`

Pokud `COMMANDS.lint` nebo `COMMANDS.format_check` je `TBD` → report `UNKNOWN` + vytvoř intake item `intake/status-missing-lint-or-format-command.md`.

Pokud je některý z nich prázdný (`""`) → report `SKIPPED` (doporuč v reportu doplnit linter/formatter).

Jinak spusť:
```bash
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi
```

### 4) Git health

```bash
# Working tree clean?
git status --porcelain

# Stale feature branches (older than GIT.max_branch_age_days)
git for-each-ref --sort=committerdate --format='%(refname:short) %(committerdate:relative)' refs/heads/

# Ahead/behind main
git rev-list --left-right --count {main_branch}...HEAD
```

Reportuj:
- dirty working tree (YES/NO)
- počet stale branches (> `GIT.max_branch_age_days`)
- unmerged branches count

### 5) Backlog health

Z `{WORK_ROOT}/backlog/*.md` spočítej:
- counts per status (IDEA/DESIGN/READY/IN_PROGRESS/IN_REVIEW/BLOCKED/DONE)
- READY ratio (kolik práce je připravené)
- WIP compliance: pokud existuje víc než 1 IN_PROGRESS/IN_REVIEW → riziko (WIP breach)

### 6) Sprint health (pokud existuje)

Najdi aktuální sprint file z `state.sprint`.
- kolik tasks je v Task Queue
- kolik DONE (pokud trackuje) vs carry-over signál (z backlog item statusů)

### 7) Docs health

- existuje `{DOCS_ROOT}/`?
- počet markdown souborů
- nejnovější modifikovaný doc file (pokud git)

### 8) Trend (last 3 status reports)

Pokud existují poslední 3 status reporty:
- trend: zlepšuje se test/lint? roste backlog READY? klesá BLOCKED?

### 9) Status report (dashboard)

`{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md` (vytvoř jako kopii `{WORK_ROOT}/templates/status-report.md`):

**MINIMUM obsah:**
- **Health score:** 0–100 (heuristicky)
- **Key signals:** tabulka se sloupci Status, Value, Assessment
  - Tests: PASS/FAIL/UNKNOWN
  - Lint/Format: PASS/FAIL/UNKNOWN
  - Backlog: READY count, BLOCKED count, WIP breach?
  - Docs: OK/STALE/UNKNOWN
  - Git: working-tree-clean (YES/NO), stale-branches (count)
- **Risks radar:** top 3–5 rizik (specifika, ne generické)
- **Suggested next actions:** max 5 (konkrétně, s prioritou)

**Šablona:**
```markdown
---
schema: fabric.report.v1
kind: status
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: OK
health_score: {0-100}
---

# status — Report {YYYY-MM-DD}

## Health snapshot
Health score: **{N}/100** ({healthy|at-risk|critical})

## Key signals
| Signal | Status | Value | Assessment |
|--------|--------|-------|------------|
| Tests | {PASS/FAIL/UNKNOWN} | {count or —} | {brief} |
| Lint | {PASS/FAIL/UNKNOWN} | {count or —} | {brief} |
| Format | {PASS/FAIL/UNKNOWN} | {count or —} | {brief} |
| Backlog flow | {OK/RISK} | READY={N}, BLOCKED={N} | {brief} |
| Docs | {OK/STALE/UNKNOWN} | {modified: N days ago or —} | {brief} |
| Git | {CLEAN/DIRTY} | dirty={N}, stale-branches={N} | {brief} |

## Codebase snapshot
| Metric | Value |
|--------|-------|
| Top language | {ext: count files, LOC} |
| Total code files | {N} |
| Total LOC | ~{N} |

## Risks (top 3)
1. {Risk}: {Specifika + impact} → {next action}
2. {Risk}: {Specifika + impact} → {next action}
3. {Risk}: {Specifika + impact} → {next action}

## Suggested next actions (priority)
1. {Konkrétní akce + reason}
2. {Konkrétní akce + reason}
3. {Konkrétní akce + reason}

## Trend (last 3 reports)
[Tabulka: Date, Health score, Key delta]
```

**Anti-patterns (zakázáno):**
- Nepiš „build health" bez ověření COMMANDS.test
- Netvrdíš „dobrý stav" pokud tests FAIL
- Netvrdíš „žádná rizika" pokud BLOCKED > READY
- Nevynechávej konkrétní čísla (vždy: {N} files, {N} tests passed, atd.)

---

## Scoring (doporučené)

Start 100:
- -40 pokud tests FAIL
- -20 pokud lint FAIL
- -10 pokud format_check FAIL
- -10 pokud WIP breach
- -10 pokud BLOCKED > READY

---

## Self-check

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/status-{YYYY-MM-DD}.md`
- [ ] Protocol log obsahuje START i END záznam

### Quality checks
- [ ] Report obsahuje povinné sekce: Health snapshot, Key signals, Codebase snapshot, Risks, Suggested next actions
- [ ] Health score je číselný (0–100)
- [ ] Všechny key signals mají explicitní hodnotu: PASS / FAIL / UNKNOWN / SKIPPED
- [ ] Risks jsou specifické (ne generické): jméno rizika + impact + next action
- [ ] Suggested actions jsou konkrétní (ne vágní): není „improve tests", je „run test coverage; target ≥80%"
- [ ] Tabulky mají hodnoty (ne „—" když je data dostupná)

### Invarianty
- [ ] Pokud `COMMANDS.test` je `TBD` → intake item „fabric-status-missing-test-command" existuje
- [ ] Pokud `COMMANDS.lint` je `TBD` → intake item „fabric-status-missing-lint-command" existuje
- [ ] Health score logika odpovídá Scoring sekcí (start 100, -40 pokud tests FAIL, atd.)

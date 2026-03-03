---
name: fabric-review
description: "Perform automated code review for the current WIP task across 8 dimensions (R1–R8). Uses config COMMANDS.lint + COMMANDS.format_check as objective gates, then performs a structured diff review. Writes a review report, updates backlog item review_report, and creates intake items for systemic improvements."
---

# REVIEW — Code review (R1–R8) + verdikt

## Účel

Zajistit „enterprise-grade“ kvalitu před merge:
- objektivní gates (lint/format),
- strukturovaný review diffu,
- jednoznačný verdikt: `CLEAN` nebo `REWORK`,
- evidence report + případné intake items pro systémové zlepšení.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-review" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-review" --event end --status OK --report "{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Vstupy

- `{WORK_ROOT}/config.md` (COMMANDS.lint, COMMANDS.format_check)
- `{WORK_ROOT}/state.md` (wip_item, wip_branch)
- `{WORK_ROOT}/backlog/{wip_item}.md`
- `{WORK_ROOT}/reports/test-{wip_item}-*.md` (evidence, pokud existuje)
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md` (compliance source of truth)
- `{WORK_ROOT}/specs/` + `specs/INDEX.md` (compliance source of truth)
- git diff na `{state.wip_branch}` proti `main`

---

## Výstupy

- `{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md` *(frontmatter `schema: fabric.report.v1` + `verdict`)*
- (volitelně) publikace pro čtení v `{WORK_ROOT}/reviews/`:
  - `python skills/fabric-init/tools/fabric.py review-publish --src "{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`
  - aktualizuje `reviews/INDEX.md`
- update backlog item:
  - `review_report: "reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`
  - `updated: {YYYY-MM-DD}`
  - `status`: nastav podle verdictu (CLEAN → DONE, REWORK → IN_PROGRESS, REDESIGN → BLOCKED)
- volitelně intake items: `{WORK_ROOT}/intake/review-*.md` (systemic)

---

## Preconditions

- `state.wip_item` a `state.wip_branch` musí existovat
- `COMMANDS.lint` a `COMMANDS.format_check` nesmí být `TBD` *(prázdné = vypnuto)*

Pokud chybí → vytvoř intake item `intake/review-missing-wip-or-commands.md` a FAIL.

### Rework counter check

Před review spočítej existující review reporty pro daný task:
```bash
ls {WORK_ROOT}/reports/review-{wip_item}-*.md 2>/dev/null | wc -l
```

Pokud count >= `SPRINT.max_rework_iters` (default 3):
- Verdikt = `ESCALATE` (ne REWORK)
- Vytvoř intake item `intake/review-max-rework-exceeded-{wip_item}.md`:
  - shrnutí opakujících se findings
  - doporučení: rozdělit task, změnit přístup, nebo eskalovat na člověka
- Nastav backlog item `status: BLOCKED`
- STOP (nepokračuj dalším rework cyklem)

Pokud je `COMMANDS.lint` nebo `COMMANDS.format_check` prázdné:
- pokračuj, ale v reportu označ gate jako `SKIPPED`
- vytvoř intake item `intake/review-recommend-enable-lint-or-format.md`

Pokud `QUALITY.mode` je `strict` a lint/format jsou prázdné (`""`):
- vytvoř intake item `intake/review-strict-mode-missing-lint-or-format.md`
- FAIL

---


## FAST PATH (doporučeno) — gates + zápis metadat deterministicky

### Objektivní gates (log capture)
```bash
python skills/fabric-init/tools/fabric.py run lint --tail 200
python skills/fabric-init/tools/fabric.py run format_check --tail 200
```

### Zápis výsledku do backlog item (bez ruční editace)
Nejprve vytvoř review report skeleton (frontmatter + verdict) a vyplň ho:

```bash
python skills/fabric-init/tools/fabric.py report-new \
  --template review-summary.md \
  --step review --kind review \
  --out "{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md" \
  --ensure-run-id
```

Pak vytvoř plan (ulož jako `{WORK_ROOT}/plans/review-plan-{wip_item}-{YYYY-MM-DD}-{run_id}.yaml`) a aplikuj ho:

```yaml
schema: fabric.plan.v1
ops:
  - op: backlog.set
    id: "{wip_item}"
    fields:
      status: "DONE"          # pokud CLEAN
      review_report: "reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"
      updated: "{YYYY-MM-DD}"
  - op: backlog.index
```

```bash
python skills/fabric-init/tools/fabric.py apply "{WORK_ROOT}/plans/review-plan-{wip_item}-{YYYY-MM-DD}-{run_id}.yaml"
```

---

## Postup

### 1) Objective gates (must run)

Na branchi:

```bash
git checkout {wip_branch}

# lint (optional)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi

# format check (optional)
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi
```

Pokud gate failne:
- Verdikt = `REWORK`
- do reportu napiš „Gate failed“ + první příčina
- STOP (neprováděj hluboký review, dokud gates nejsou čisté)

### 2) Zjisti změny (diff)

```bash
git fetch --all --prune
git diff --stat {main_branch}...{wip_branch}
git diff {main_branch}...{wip_branch}
```

Vypiš seznam změněných souborů (code/test/docs).

### 3) Review rámec (R1–R8)

Pro každou dimenzi napiš:
- skóre 0–5
- konkrétní nálezy (1–N)
- doporučení nebo požadavek na rework

Dimenze:
- **R1 Correctness:** správnost a edge cases
- **R2 Security:** input validation, secrets, authz, injections
- **R3 Performance:** složitost, I/O, hot paths
- **R4 Reliability:** error handling, retries, timeouts
- **R5 Testability:** testy pokrývají AC? izolace? flaky?
- **R6 Maintainability:** čitelnost, naming, modularita
- **R7 Documentation:** docs + komentáře + ADR když je potřeba
- **R8 Compliance:** dodržení config konvencí + **accepted ADR** + **active specs** (porušení = CRITICAL)


#### R8 Compliance — konkrétně (povinné)

1) Otevři `decisions/INDEX.md` a identifikuj `accepted` ADR (nebo ty, které jsou zmíněné v analýze tasku).
2) Otevři `specs/INDEX.md` a identifikuj `active` specs (nebo ty, které jsou zmíněné v analýze tasku).
3) Pokud diff zavádí změnu, která **odporuje accepted ADR** nebo **porušuje active spec**:
   - zapiš finding severity **CRITICAL**
   - v reportu cituj konkrétní ADR/SPEC + konkrétní změnu v diffu
   - doporuč: buď upravit implementaci, nebo vytvořit nový ADR/SPEC (nepřepisuj accepted bez procesu)


### 4) Verdikt (jednoznačně)

**Důležité:** Verdikt musí být parsovatelný. Do reportu napiš řádek přesně ve tvaru:
- `Verdict: CLEAN`
- nebo `Verdict: REWORK`


- `CLEAN` pokud:
  - gates PASS
  - žádné CRITICAL findings
  - test evidence existuje a je PASS (nebo je v reportu vysvětleno proč ne)

- `REWORK` pokud:
  - gates fail
  - nebo existuje alespoň 1 CRITICAL finding

### Finding severity taxonomy

Každý individual finding musí mít severity:

- **CRITICAL** — blokuje merge: security issue, data corruption risk, testy nevalidují AC, breaking change bez docs, ambiguous behavior
- **HIGH** — měl by se opravit před merge: chybějící error handling pro hlavní flow, netestovaný edge case pro core logic, performance regrese
- **MEDIUM** — doporučeno opravit, neblokuje: naming, minor refactor, chybějící doc komentář, neoptimální ale funkční řešení
- **LOW** — nice-to-have: stylistické, preference, minor improvements

Verdikt pravidla:
- ≥1 CRITICAL → `REWORK`
- ≥3 HIGH bez CRITICAL → `REWORK` (akumulace)
- Jen MEDIUM/LOW → `CLEAN` (findings zapiš do reportu jako doporučení)

### 5) Systemic findings → intake

Pokud najdeš věc, která není jen pro tento task (např. chybí lint rule, CI gate, opakující se pattern):
- vytvoř intake item podle `{WORK_ROOT}/templates/intake.md`
- `source: review`
- `initial_type: Chore` (typicky)
- `raw_priority` podle dopadu

### 6) Zapiš review report a aktualizuj backlog item

1) Vytvoř report skeleton deterministicky (frontmatter + verdict):

```bash
python skills/fabric-init/tools/fabric.py report-new \
  --template review-summary.md \
  --step review --kind review \
  --out "{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md" \
  --ensure-run-id
```

2) Vyplň report (hlavně `verdict: CLEAN|REWORK|REDESIGN`).

3) Do backlog itemu doplň (preferovaně přes apply plan výše):
   - `review_report: "reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`
   - `updated: {YYYY-MM-DD}`
   - `status:`
     - `CLEAN` → `DONE`
     - `REWORK` → `IN_PROGRESS`
     - `REDESIGN` → typicky `BLOCKED` + vytvoř follow‑up v intake

---

> Skeleton reportu nepiš ručně — používej template `review-summary.md`.

## Checklist (co musí být v reportu)
- R1–R8 (skóre + konkrétní nálezy)
- CRITICAL findings (pokud existují)
- Suggested next step

---

## Self-check

- review report exists
- backlog item has `review_report`
- verdict is explicit (CLEAN/REWORK/REDESIGN)

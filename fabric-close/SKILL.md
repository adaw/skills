---
name: fabric-close
description: "Close the current sprint: merge approved task branches into main (squash), run quality gates on main, update backlog items to DONE with evidence (merge_commit), regenerate backlog index, and write a close report. Leaves carry-over items untouched and documents why."
---

# CLOSE — Uzavření sprintu (merge + evidence)

## Účel

- squash-merge hotové tasks do `main`
- ověřit kvalitu na `main` (lint/format/tests)
- aktualizovat backlog items (`status: DONE`, `merge_commit`)
- vytvořit sprint close report

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-close" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-close" --event end --status OK --report "{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


> CLOSE nesmí dělat magie. Když něco není připravené (chybí CLEAN review, branch, nebo tests), musí to být explicitně označeno jako carry-over.

---

## Vstupy

- `{WORK_ROOT}/config.md` (GIT + COMMANDS)
- `{WORK_ROOT}/state.md` (sprint N)
- `{WORK_ROOT}/sprints/sprint-{N}.md` (Task Queue)
- `{WORK_ROOT}/backlog/{id}.md` (branch + review_report)
- `{WORK_ROOT}/reports/review-*.md` (Verdict)
- `{WORK_ROOT}/reports/test-*.md` (evidence; volitelné)

---

## Výstupy

- **Per-task:** `{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md` *(pro každý mergovaný task — NESMÍ se přepisovat)*
- **Sprint summary:** `{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md` *(aktualizuj po každém close — append-only tabulky, přepiš jen Summary/Next)*
- aktualizované backlog items:
  - `merge_commit`
  - `status: DONE`
  - `updated`
- regenerovaný `{WORK_ROOT}/backlog.md` *(po každém merge, ne jen na konci)*
- aktualizovaný `{WORK_ROOT}/sprints/sprint-{N}.md` (Task Queue statusy → DONE)
- (doporučeno) reset `state.wip_item` + `state.wip_branch` na null

---

## Preconditions

- `COMMANDS.test` nesmí být `TBD` ani prázdné
- `COMMANDS.lint` nesmí být `TBD` *(prázdné = vypnuto v bootstrap režimu)*
- `COMMANDS.format_check` nesmí být `TBD` *(prázdné = vypnuto v bootstrap režimu)*
- sprint plán musí existovat a mít `## Task Queue`

Pokud `QUALITY.mode` je `strict`:
- `COMMANDS.lint` a `COMMANDS.format_check` NESMÍ být prázdné (`""`).
- Pokud jsou → vytvoř `intake/close-strict-mode-missing-lint-or-format.md` a FAIL.

Pokud preconditions nejsou splněny:
- vytvoř intake item `intake/close-missing-config-or-sprint.md`
- FAIL

---


## FAST PATH (doporučeno) — quality gates deterministicky

Po merge do `main` spusť gates deterministicky přes `fabric.py` (logy do `{WORK_ROOT}/logs/commands/`):

```bash
python skills/fabric-init/tools/fabric.py run test --tail 200
python skills/fabric-init/tools/fabric.py run lint --tail 200
python skills/fabric-init/tools/fabric.py run format_check --tail 200
```

A metadata (`merge_commit`, `status`) patchuj přes plan/apply, ne ručně.

---

## Postup

### 1) Načti sprint tasks (Task Queue)

Z `sprints/sprint-{N}.md` načti tabulku `Task Queue` a získej ordered list:
- `id`, `title`, `type`, `status`, `depends_on`

Ignoruj řádky, které nejsou Task-like typy.

### 2) Klasifikuj tasks: MERGEABLE vs CARRY-OVER

Task je **MERGEABLE**, pokud:
- backlog item `{WORK_ROOT}/backlog/{id}.md` existuje
- `branch:` je vyplněný a branch existuje lokálně nebo na remote
- `review_report:` existuje a obsahuje `Verdict: CLEAN`

Jinak je **CARRY-OVER** s důvodem:
- missing branch
- review missing
- review verdict REWORK
- blocked dependencies
- status není IN_REVIEW (typicky není hotovo)

### 3) Mergeable tasks mergeuj sekvenčně (bezpečně)

Pro každý MERGEABLE task v pořadí:

1. Připrav main:
   ```bash
   git fetch --all --prune
   git checkout {main_branch}
   git pull --ff-only
   ```
2. Zapamatuj si pre-merge HEAD:
   ```bash
   PRE=$(git rev-parse HEAD)
   ```
3. Ujisti se, že branch existuje:
   - pokud je lokální: `git show-ref --verify refs/heads/{branch}`
   - pokud není, ale je remote: `git checkout -b {branch} origin/{branch}`

4. Squash merge:
   ```bash
   git merge --squash {branch}
   git commit -m "feat({id}): {title} (sprint {N})"
   ```
5. Spusť quality gates na main (bezpečně, podle `QUALITY.mode`):
   - **Poznámka:** v `bootstrap` režimu mohou být `lint` / `format_check` vypnuté (`""`) → ber jako `SKIPPED`.
     Ve `strict` režimu musí být nakonfigurované (nesmí být `""` ani `TBD`).

   ```bash
   # lint (optional)
   if [ "{COMMANDS.lint}" = "TBD" ]; then echo "lint: TBD (configure COMMANDS.lint)"; exit 2; fi
   if [ -n "{COMMANDS.lint}" ]; then {COMMANDS.lint}; else echo "lint: SKIPPED"; fi

   # format_check (optional)
   if [ "{COMMANDS.format_check}" = "TBD" ]; then echo "format_check: TBD (configure COMMANDS.format_check)"; exit 2; fi
   if [ -n "{COMMANDS.format_check}" ]; then {COMMANDS.format_check}; else echo "format_check: SKIPPED"; fi

   # test (required)
   if [ "{COMMANDS.test}" = "TBD" ] || [ -z "{COMMANDS.test}" ]; then echo "test: NOT CONFIGURED (configure COMMANDS.test)"; exit 2; fi
   {COMMANDS.test}

   # e2e test (optional — spusť pokud existuje a není TBD)
   if [ -n "{COMMANDS.test_e2e}" ] && [ "{COMMANDS.test_e2e}" != "TBD" ]; then {COMMANDS.test_e2e}; else echo "test_e2e: SKIPPED"; fi
   ```

6. Pokud gates FAIL:

   **6a) Pokus o auto-fix (max 1×, jen pro lint/format):**
   Pokud selhaly lint nebo format_check (ne test), zkus auto-fix před revertem:

   ```bash
   # lint auto-fix (pokud lint failnul a lint_fix existuje)
   if [ -n "{COMMANDS.lint_fix}" ] && [ "{COMMANDS.lint_fix}" != "TBD" ]; then {COMMANDS.lint_fix}; fi

   # format auto-fix (pokud format_check failnul a format existuje)
   if [ -n "{COMMANDS.format}" ] && [ "{COMMANDS.format}" != "TBD" ]; then {COMMANDS.format}; fi
   ```

   Pokud auto-fix opravil něco, commitni a znovu spusť všechny gates:
   ```bash
   git add -A && git commit -m "chore({id}): auto-fix lint/format on main"
   {COMMANDS.lint}
   {COMMANDS.format_check}
   {COMMANDS.test}
   ```

   Pokud po auto-fixu všechny gates PASS → pokračuj krokem 7 (úspěch).
   Pokud stále FAIL (nebo selhaly testy, ne jen lint/format) → pokračuj revertem níže.

   **6b) Revert (pokud auto-fix nepomohl nebo selhaly testy):**
   - **NEPOUŽÍVEJ** `git reset --hard` ani force push.
   - rollback proveď přes **revert commit** (zachová historii main):
     ```bash
     MERGE_COMMIT=$(git rev-parse HEAD)
     PARENTS=$(git show -s --format=%P "$MERGE_COMMIT")
     if [ "$(echo "$PARENTS" | wc -w)" -ge 2 ]; then
       git revert -m 1 --no-edit "$MERGE_COMMIT"
     else
       git revert --no-edit "$MERGE_COMMIT"
     fi
     ```
   - Pokud revert FAIL (konflikty):
     vytvoř intake item `intake/close-revert-conflict-{id}.md` (zahrň `git status` + konfliktové soubory), nastav `state.error` a **STOP**.
   - Po úspěšném revertu znovu spusť `{COMMANDS.test}` (main musí zůstat green). Pokud to FAIL, nastav `state.error` a **STOP**.
   - vytvoř intake item `intake/close-merge-failed-{id}.md` s výpisem failu + odkazem na revert commit
   - označ task jako carry-over (reason: merge gates failed)
   - pokračuj dalším taskem (nesmí to zablokovat celý sprint)

7. Pokud gates PASS:
   - získej commit SHA: `SHA=$(git rev-parse HEAD)`
   - aktualizuj backlog item:
     - `merge_commit: {SHA}`
     - `status: DONE`
     - `updated: {YYYY-MM-DD}`
   - **smaž feature branch** (povinné — zabraňuje hromadění stale branches):
     ```bash
     git branch -d {branch} 2>/dev/null || true
     git push origin --delete {branch} 2>/dev/null || true
     ```
     Poznámka: `-d` (ne `-D`) = safe delete (odmítne smazat nemerged branch). Remote delete je best-effort (může selhat bez push práv — to je OK, zapiš do reportu).

> Poznámka: Když má projekt CI, je vhodné po merge udělat `git push origin main` (pokud má agent práva). Pokud ne, aspoň to uveď v reportu jako next action.

### 4) Regeneruj backlog index (po KAŽDÉM merge)

Deterministicky:
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```

Tím se `{WORK_ROOT}/backlog.md` synchronizuje se skutečným stavem backlog items. Nečekej na konec sprintu — **regeneruj po každém merge**, aby byl backlog.md vždy aktuální.

### 5) Per-task close report (povinné)

Pro KAŽDÝ mergovaný task vytvoř **samostatný** report:

`{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md`

Obsah:
- Task ID, title, branch, merge commit SHA
- Quality evidence (test PASS/FAIL, lint PASS/FAIL/SKIPPED)
- Carry-over: ne (pokud DONE) nebo důvod

> **NESMÍŠ přepisovat existující per-task close report.** Každý task = 1 soubor. To zajišťuje kompletní audit trail.

### 6) Sprint summary report (append-only)

`{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md` dle `{WORK_ROOT}/templates/close-report.md`:

Po KAŽDÉM merge aktualizuj tento soubor:
- **Completed & Merged** — tabulka (append řádek pro nový task)
- **Carry-over** — aktualizuj zbývající tasky
- **Not started** / **Blocked**
- **Quality evidence** (jaké commands běžely, PASS/FAIL)
- **Summary** + **Next** — přepiš aktuální stav

### 6) Reset WIP (doporučeno)

Po uzavření sprintu nastav ve `{WORK_ROOT}/state.md`:
- `wip_item: null`
- `wip_branch: null`

> Nesahej na `phase/step`.

---

## Fail conditions

- sprint plan nemá Task Queue
- `COMMANDS.test` je `TBD` nebo prázdné
- `COMMANDS.lint` je `TBD`
- `COMMANDS.format_check` je `TBD`
- git working tree není čistý na main při merge

V těchto případech: vytvoř intake item + CRITICAL v close reportu.

### Idempotence a recovery

**Re-run je bezpečný.** Pokud fabric-close spadne uprostřed:
- **Merge už proběhl, gates ještě ne:** Re-run detekuje `git log --oneline main | head -1` s merge commitem → přeskočí merge, pokračuje gates.
- **Gates selhaly, revert ještě neproběhl:** Re-run znovu spustí gates → auto-fix → revert fallback.
- **Revert proběhl:** Re-run detekuje `HEAD` bez merge commitu → začne od merge znovu.
- **Branch delete selhal (remote):** Zalogováno jako warning v reportu, nefatální. Re-run zkusí znovu.
- **Částečný sprint (některé tasky merged, jiné ne):** Close zpracovává tasky sekvenčně; hotové tasky přeskočí (status=DONE v backlog).

---

## Self-check

Před návratem:
- všechny DONE tasky squash-mergnuty do main (nebo přeskočeny při REDESIGN/BLOCKED)
- `COMMANDS.test` PASS na main (post-merge)
- `COMMANDS.test_e2e` PASS na main (pokud definován)
- `COMMANDS.lint` PASS na main (po případném auto-fix)
- WIP branch smazán lokálně i remote (nebo zachován při REDESIGN)
- `state.wip_item = null` a `state.wip_branch = null`
- close report existuje v `{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md`
- sprint plan aktualizován (task statuses)

Pokud ne → FAIL + vytvoř intake item `intake/close-selfcheck-failed-{date}.md`.

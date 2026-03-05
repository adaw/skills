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

## OWNERSHIP — Backlog index

**Odpovědnost:** `fabric-intake`, `fabric-prio` a `fabric-close` MUSÍ spolupracovat na údržbě centrálního backlog indexu (`{WORK_ROOT}/backlog.md`):
- `fabric-intake` → regeneruje index po triážích
- `fabric-prio` → regeneruje po prioritizaci
- `fabric-close` → regeneruje po uzavření sprintu (DONE items, carry-over logika)

**Invariant:** Index je vždy aktuální s jednotlivými backlog soubory v `{WORK_ROOT}/backlog/{id}.md` (asynchronní update je povolený, ale konsistence se musí ověřit v auditu).

---

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
  ```bash
  # Overwrite guard (povinné):
  CLOSE_REPORT="{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md"
  if [ -f "$CLOSE_REPORT" ]; then
    echo "ERROR: close report already exists: $CLOSE_REPORT (idempotence — skip)"
  fi
  ```
- **Sprint summary:** `{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md` *(aktualizuj po každém close — append-only tabulky, přepiš jen Summary/Next)*
  ```bash
  # Append-only guard: sprint summary může existovat z předchozího task close
  # Přidávej řádky do tabulky, neprůpiš existující data
  SPRINT_REPORT="{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md"
  if [ -f "$SPRINT_REPORT" ]; then
    # Dedup guard: zkontroluj zda task ID už není v tabulce (idempotence)
    if grep -q "| ${TASK_ID} |" "$SPRINT_REPORT" 2>/dev/null; then
      echo "SKIP: task $TASK_ID already in sprint summary (dedup)"
    else
      echo "Appending to existing sprint summary"
      # Přidej řádek do Task Status tabulky (ne přepiš celý soubor)
    fi
  fi
  ```
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
- pro každý task určený k merge: review report musí existovat na disku (temporal: review → close)

### Read reviews index for governance (P2 fix #37)

```bash
# Read reviews index for governance (P2 fix)
if [ -f "{WORK_ROOT}/reviews/INDEX.md" ]; then
  echo "Found reviews index — checking for REWORK verdicts"
  REWORK_COUNT=$(grep -c "REWORK" "{WORK_ROOT}/reviews/INDEX.md" 2>/dev/null || echo 0)
  if [ "$REWORK_COUNT" -gt 0 ]; then
    echo "WARN: $REWORK_COUNT tasks have REWORK verdict — verify before closing"
  fi
fi
```

Pokud `QUALITY.mode` je `strict`:
- `COMMANDS.lint` a `COMMANDS.format_check` NESMÍ být prázdné (`""`).
- Pokud jsou → vytvoř `intake/close-strict-mode-missing-lint-or-format.md` a FAIL.

Pokud preconditions nejsou splněny:
- vytvoř intake item `intake/close-missing-config-or-sprint.md`
- FAIL

### Per-task file existence checks (povinné, v merge loop)

```bash
# Pro každý task v Task Queue s verdiktem CLEAN:
TASK_ID="..."  # z iterace přes Task Queue

# 1. backlog soubor musí existovat
if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  echo "SKIP: backlog file missing for $TASK_ID — carry-over"
  continue
fi

# 2. review report musí existovat na disku (temporal: implement→test→review→close)
REVIEW_REPORT=$(grep 'review_report:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | awk '{print $2}')
if [ -z "$REVIEW_REPORT" ] || [ ! -f "{WORK_ROOT}/${REVIEW_REPORT}" ]; then
  echo "SKIP: review report missing for $TASK_ID — carry-over"
  continue
fi

# 2a. Review verdict schema validation (P2 fix #26)
LATEST_REVIEW=$(ls -t {WORK_ROOT}/reports/review-*.md 2>/dev/null | head -1)
if [ -n "$LATEST_REVIEW" ]; then
  VERDICT=$(grep '^verdict:' "$LATEST_REVIEW" | awk '{print $2}')
  if ! echo "$VERDICT" | grep -qE '^(PASS|FAIL|REWORK)$'; then
    echo "WARN: review verdict '$VERDICT' is not valid (expected PASS|FAIL|REWORK)"
  fi
fi

# 3. branch musí existovat
TASK_BRANCH=$(grep 'branch:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | awk '{print $2}')
if [ -z "$TASK_BRANCH" ] || [ "$TASK_BRANCH" = "null" ]; then
  echo "SKIP: no branch for $TASK_ID — carry-over"
  continue
fi
if ! git rev-parse --verify "$TASK_BRANCH" >/dev/null 2>&1; then
  echo "SKIP: branch $TASK_BRANCH not found for $TASK_ID — carry-over"
  continue
fi

# 4. depends_on check: všechny závislosti musí být DONE
DEPENDS=$(grep 'depends_on:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | sed 's/depends_on://' | tr -d '[],' | xargs)
for DEP in $DEPENDS; do
  DEP_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${DEP}.md" 2>/dev/null | awk '{print $2}')
  if [ "$DEP_STATUS" != "DONE" ]; then
    echo "SKIP: dependency $DEP not DONE (status=$DEP_STATUS) for $TASK_ID — carry-over"
    continue 2
  fi
done
```

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

### Orchestrační model (multi-task)

`fabric-close` zpracovává **VŠECHNY tasks v Task Queue v jednom dispatch** (procedurální loop uvnitř jednoho skill runu). To znamená:
- Orchestrátor (`fabric-loop`) dispatchne `fabric-close` **jednou** za sprint.
- `fabric-close` iteruje Task Queue sekvenčně (merge task 1, gates, merge task 2, gates, ...).
- Po zpracování VŠECH tasks (merge nebo carry-over) se `fabric-close` vrátí s jedním sprint summary reportem.
- `fabric-loop` pak pokračuje `tick --completed close` → next step (implement pokud jsou READY tasks, jinak docs).

> **Není to 1 dispatch per task.** Close je procedurální batching skill — analogicky k `fabric-intake` (zpracuje všechny intake items v jednom runu).

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
   timeout 60 git fetch --all --prune || { echo "WARN: git fetch failed/timeout"; GATE_RESULT="FETCH_FAIL"; }
   git checkout "${main_branch}"
   CHECKOUT_EXIT=$?
   if [ $CHECKOUT_EXIT -ne 0 ]; then echo "ERROR: cannot checkout main"; exit 1; fi
   git pull --ff-only
   PULL_EXIT=$?
   if [ $PULL_EXIT -ne 0 ]; then echo "WARN: pull failed (exit $PULL_EXIT), using local main"; fi
   ```
2. Zapamatuj si pre-merge HEAD:
   ```bash
   PRE=$(git rev-parse HEAD)
   ```
3. Ujisti se, že branch existuje:
   - pokud je lokální: `git show-ref --verify "refs/heads/${branch}"`
   - pokud není, ale je remote: `git checkout -b "${branch}" "origin/${branch}"`

4. Pre-merge divergence check (povinné):
   ```bash
   # Ověř, že branch je based on current main (ne na stale main)
   MERGE_BASE=$(git merge-base "${main_branch}" "${branch}")
   MAIN_HEAD=$(git rev-parse "${main_branch}")
   if [ "$MERGE_BASE" != "$MAIN_HEAD" ]; then
     echo "WARN: branch ${branch} diverged from ${main_branch} (merge-base: $MERGE_BASE, main HEAD: $MAIN_HEAD)"
     # Pokus o rebase (safe — na feature branch, ne na main)
     git checkout "${branch}"
     git rebase "${main_branch}"
     REBASE_EXIT=$?
     if [ $REBASE_EXIT -ne 0 ]; then
       git rebase --abort
       echo "ERROR: rebase failed for ${branch}, marking as carry-over"
       git checkout "${main_branch}"
       # Vytvoř intake item (povinné — evidence pro carry-over)
       # intake/close-rebase-failed-{id}.md s: branch name, merge-base, rebase error
       # Označ jako CARRY-OVER (reason: branch diverged, rebase conflict)
       # Aktualizuj sprint summary report (carry-over tabulka)
       # Přeskoč na další task (continue, ne break)
     fi
     git checkout "${main_branch}"
   fi
   ```

5. Squash merge (s conflict detection):
   ```bash
   git merge --squash "${branch}"
   MERGE_EXIT=$?
   if [ $MERGE_EXIT -ne 0 ]; then
     echo "ERROR: squash merge conflict for {branch}"
     # Vyčisti conflict stav
     git merge --abort 2>/dev/null || git reset --merge 2>/dev/null
     # Verifikace čistého working tree po abort (povinné)
     if [ -n "$(git status --porcelain)" ]; then
       echo "WARN: dirty working tree after merge abort, cleaning"
       git checkout -- . 2>/dev/null
       git clean -fd 2>/dev/null
       # Third fallback: if still dirty, hard reset to pre-merge HEAD (safe — we saved PRE)
       if [ -n "$(git status --porcelain)" ]; then
         echo "WARN: cleanup failed, resetting to pre-merge HEAD ($PRE)"
         git reset --hard "$PRE"
       fi
     fi
     # Označ jako carry-over
     # Vytvoř intake item
     echo "Carry-over: merge conflict, needs manual resolution"
     # NEPOKRAČUJ na commit — přeskoč na další task
   fi
   # Commit s exit code kontrolou
   git commit -m "feat(${id}): ${title} (sprint ${N})"
   COMMIT_EXIT=$?
   if [ $COMMIT_EXIT -ne 0 ]; then
     echo "ERROR: commit failed after squash merge (exit $COMMIT_EXIT)"
     # Vyčisti stav
     git reset HEAD 2>/dev/null
     # Označ jako carry-over (reason: commit failed)
     # Vytvoř intake item intake/close-commit-failed-{id}.md
     # Přeskoč na další task
   fi
   ```

   **Squash conflict handling:** Pokud `git merge --squash` selže (exit ≠ 0):
   - Vyčisti merge stav: `git merge --abort` (nebo `git reset --merge` pokud --abort nefunguje)
   - Ověř čistý working tree: `git status --porcelain` (pokud dirty → `git checkout -- .` + `git clean -fd`)
   - Vytvoř intake item `intake/close-merge-conflict-{id}.md` s: branch name, conflict files, pre-merge HEAD
   - Označ task jako CARRY-OVER (reason: squash merge conflict)
   - **Nepokračuj** na commit / quality gates — přeskoč na další MERGEABLE task
   - Tím se zajistí, že merge conflict jednoho tasku nezablokuje celý sprint
6. Spusť quality gates na main (bezpečně, podle `QUALITY.mode`):
   - **Poznámka:** v `bootstrap` režimu mohou být `lint` / `format_check` vypnuté (`""`) → ber jako `SKIPPED`.
     Ve `strict` režimu musí být nakonfigurované (nesmí být `""` ani `TBD`).

   ```bash
   GATE_RESULT="PASS"

   # lint (optional)
   if [ "{COMMANDS.lint}" = "TBD" ]; then echo "lint: TBD (configure COMMANDS.lint)"; exit 2; fi
   if [ -n "{COMMANDS.lint}" ]; then
     timeout 120 {COMMANDS.lint}; LINT_EXIT=$?
     if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint"; GATE_RESULT="TIMEOUT"; elif [ $LINT_EXIT -ne 0 ]; then GATE_RESULT="FAIL_LINT"; fi
   else echo "lint: SKIPPED"; fi

   # format_check (optional)
   if [ "{COMMANDS.format_check}" = "TBD" ]; then echo "format_check: TBD (configure COMMANDS.format_check)"; exit 2; fi
   if [ -n "{COMMANDS.format_check}" ]; then
     timeout 120 {COMMANDS.format_check}; FMT_EXIT=$?
     if [ $FMT_EXIT -eq 124 ]; then echo "TIMEOUT: format_check"; GATE_RESULT="TIMEOUT"; elif [ $FMT_EXIT -ne 0 ]; then GATE_RESULT="FAIL_FORMAT"; fi
   else echo "format_check: SKIPPED"; fi

   # test (required)
   if [ "{COMMANDS.test}" = "TBD" ] || [ -z "{COMMANDS.test}" ]; then echo "test: NOT CONFIGURED"; exit 2; fi
   timeout 300 {COMMANDS.test}; TEST_EXIT=$?
   if [ $TEST_EXIT -eq 124 ]; then echo "TIMEOUT: test"; GATE_RESULT="TIMEOUT"; elif [ $TEST_EXIT -ne 0 ]; then GATE_RESULT="FAIL_TEST"; fi

   # e2e test (optional)
   if [ -n "{COMMANDS.test_e2e}" ] && [ "{COMMANDS.test_e2e}" != "TBD" ]; then
     timeout 600 {COMMANDS.test_e2e}; E2E_EXIT=$?
     if [ $E2E_EXIT -eq 124 ]; then echo "TIMEOUT: test_e2e"; GATE_RESULT="TIMEOUT"; elif [ $E2E_EXIT -ne 0 ]; then GATE_RESULT="FAIL_E2E"; fi
   else echo "test_e2e: SKIPPED"; fi
   ```

   > **Timeout (exit 124) se NESMÍ zaměnit za normální test FAIL.** Timeout = killed externally, FAIL = test assertion failed. Odlišná příčina, odlišná remediace.

6. Pokud gates FAIL:

   **6a) Pokus o auto-fix (max 1× per close run, jen pro lint/format):**
   Pokud selhaly lint nebo format_check (ne test), zkus auto-fix před revertem:

   ```bash
   # Idempotence guard: auto-fix na main proběhne max 1× per close dispatch
   CLOSE_AUTOFIX_DONE=0  # lokální flag (nepersistuje — close je jednorázový)
   if [ "$CLOSE_AUTOFIX_DONE" -ge 1 ]; then
     echo "SKIP: auto-fix on main already attempted this close run"
   fi
   # lint auto-fix (pokud lint failnul a lint_fix existuje) — s timeoutem
   if [ -n "{COMMANDS.lint_fix}" ] && [ "{COMMANDS.lint_fix}" != "TBD" ]; then
     timeout 120 {COMMANDS.lint_fix}
     LINTFIX_EXIT=$?
     if [ $LINTFIX_EXIT -eq 124 ]; then echo "TIMEOUT: lint_fix on main"; GATE_RESULT="TIMEOUT"; fi
   fi

   # format auto-fix (pokud format_check failnul a format existuje) — s timeoutem
   if [ -n "{COMMANDS.format}" ] && [ "{COMMANDS.format}" != "TBD" ]; then
     timeout 120 {COMMANDS.format}
     FMTFIX_EXIT=$?
     if [ $FMTFIX_EXIT -eq 124 ]; then echo "TIMEOUT: format on main"; GATE_RESULT="TIMEOUT"; fi
   fi
   ```

   Pokud auto-fix opravil něco, commitni a znovu spusť všechny gates:
   ```bash
   git add -A && git commit -m "chore(${id}): auto-fix lint/format on main"
   CLOSE_AUTOFIX_DONE=1  # Nastav flag po úspěšném auto-fix commitu
   # Zapamatuj si PRE auto-fix test výsledek pro regression detekci
   PRE_FIX_TEST_RESULT="${GATE_RESULT}"  # PASS/FAIL/TIMEOUT z pre-autofix gates
   timeout 120 {COMMANDS.lint}; POST_FIX_LINT_EXIT=$?
   timeout 120 {COMMANDS.format_check}; POST_FIX_FMT_EXIT=$?
   timeout 300 {COMMANDS.test}; POST_FIX_TEST_EXIT=$?
   # Mapuj exit codes na výsledky (konzistentně s fabric-implement naming)
   if [ $POST_FIX_TEST_EXIT -eq 124 ]; then POST_FIX_TEST="TIMEOUT";
   elif [ $POST_FIX_TEST_EXIT -ne 0 ]; then POST_FIX_TEST="FAIL"; else POST_FIX_TEST="PASS"; fi
   ```

   **Regression detekce:** Pokud auto-fix způsobil NOVÉ selhání (testy FAILily po auto-fixu, ale ne před ním):
   ```bash
   if [ "$PRE_FIX_TEST_RESULT" = "PASS" ] && [ "$POST_FIX_TEST" != "PASS" ]; then
     echo "REGRESSION: auto-fix broke tests on main, reverting"
   fi
   ```
   - Revertni auto-fix commit: `git revert --no-edit HEAD`
   - Vytvoř intake item `intake/close-autofix-regression-{date}.md` s diff pre/post
   - Pokračuj revertem merge commitu (7b)

   Pokud po auto-fixu všechny gates PASS → pokračuj krokem 8 (úspěch).
   Pokud stále FAIL (stejné chyby jako před auto-fixem) → pokračuj revertem níže.

   **7b) Revert (pokud auto-fix nepomohl nebo selhaly testy):**
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
     1. **Vyčisti working tree:** `git revert --abort` (vrátí main do pre-revert stavu)
     2. Vytvoř intake item `intake/close-revert-conflict-{id}.md` (zahrň `git status` + konfliktové soubory)
     3. Nastav `state.error` a **STOP**
     4. Při re-run fabric-close: detekuj, že merge commit existuje ale revert selhal → zkus revert znovu (idempotentní díky `--abort` cleanup)
   - Po úspěšném revertu znovu spusť `{COMMANDS.test}` (main musí zůstat green). Pokud to FAIL, nastav `state.error` a **STOP**.
   - vytvoř intake item `intake/close-merge-failed-{id}.md` s výpisem failu + odkazem na revert commit
   - označ task jako carry-over (reason: merge gates failed)
   - pokračuj dalším taskem (nesmí to zablokovat celý sprint)

8. Pokud gates PASS:
   - získej commit SHA: `SHA=$(git rev-parse HEAD)`
   - **merge_commit enforcement (P2 fix #27):**
     ```bash
     MERGE_COMMIT=$(git log --oneline -1 --format=%H)
     if [ -z "$MERGE_COMMIT" ]; then
       echo "WARN: merge_commit is empty — close report will be incomplete"
     fi
     ```
   - aktualizuj backlog item:
     - `merge_commit: {SHA}`
     - `status: DONE`
     - `updated: {YYYY-MM-DD}`
     - `branch: null` *(vyčisti stale branch referenci — zabraňuje reuse v příštím sprintu)*
   - Explicitní kód pro backlog item update:
     ```bash
     python skills/fabric-init/tools/fabric.py backlog-set --id "{id}" --fields-json \
       '{"merge_commit": "'"$SHA"'", "status": "DONE", "updated": "'"$(date +%Y-%m-%d)"'", "branch": null}'
     ```
     > Ensure the backlog update section explicitly sets `merge_commit:` — this guard above confirms it is not empty before update.
   - **smaž feature branch** (povinné — zabraňuje hromadění stale branches):
     ```bash
     git branch -d "${branch}" 2>/dev/null || true
     git push origin --delete "${branch}" 2>/dev/null || true
     ```
     Poznámka: `-d` (ne `-D`) = safe delete (odmítne smazat nemerged branch).

     **Remote delete handling:**
     - Pokud remote delete selže (network, práva, branch neexistuje): zaloguj WARNING do close reportu.
     - Pokud lokální branch stále existuje po remote delete failure: vytvoř intake item `intake/close-branch-cleanup-{branch}.md`.
     - Při příštím `fabric-init` nebo `fabric-status` se orphaned branches detekují a reportují.

> Poznámka: Když má projekt CI, je vhodné po merge udělat `git push origin main` (pokud má agent práva). Pokud ne, aspoň to uveď v reportu jako next action.

### 4) Regeneruj backlog index (po KAŽDÉM merge)

Deterministicky:
```bash
# OWNERSHIP: backlog.md regeneraci provádí VÝHRADNĚ fabric.py backlog-index
# Nikdy neregeneruj backlog.md ručně — vždy volej tento příkaz.
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

### 7) Reset WIP (povinné — ATOMIC WRITE)

Po uzavření každého tasku (merge PASS nebo carry-over) resetuj WIP přes deterministický tool (atomický zápis):

```bash
# POVINNÉ: Použij state-patch (atomic write: tmp → mv) — nikdy nepiš do state.md přímo!
python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"wip_item": null, "wip_branch": null}'
# Fallback pokud state-patch selže:
STATE_PATCH_EXIT=$?
if [ $STATE_PATCH_EXIT -ne 0 ]; then
  echo "WARN: state-patch failed (exit $STATE_PATCH_EXIT), attempting manual atomic write"
  # Atomic write pattern: tmp → mv (nikdy přímý zápis do state.md)
  cp "{WORK_ROOT}/state.md" "{WORK_ROOT}/state.md.tmp"
  sed -i 's/^wip_item:.*/wip_item: null/' "{WORK_ROOT}/state.md.tmp"
  sed -i 's/^wip_branch:.*/wip_branch: null/' "{WORK_ROOT}/state.md.tmp"
  mv "{WORK_ROOT}/state.md.tmp" "{WORK_ROOT}/state.md"
fi
```

> Nesahej na `phase/step`. WIP reset je **mandatory** — fabric-loop předpokládá, že po close je WIP čistý pro výběr dalšího tasku.
> **NIKDY nepiš do state.md přímo (sed -i state.md).** Vždy tmp → mv pro atomicitu.

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

### Network partition a git consistency

Fabric předpokládá lokální git operace (žádný remote push na main v default flow). Proto:
- **Network outage během `git push origin --delete`:** Neblokuje — remote delete je best-effort s `|| true`.
- **Network outage během `git fetch --all --prune`:** Selže pre-merge check → `state.error` + STOP. Recovery: opakuj po obnovení sítě.
- **Partial merge (merge commit napsán, ale git process killed):**
  Detekce: `git status` ukáže „merge in progress" nebo dirty tree.
  Recovery: `git merge --abort` → clean state → re-run od začátku.
  ```bash
  # Při startu fabric-close vždy zkontroluj stav:
  if git rev-parse --verify MERGE_HEAD >/dev/null 2>&1; then
    echo "WARN: merge in progress detected, aborting stale merge"
    git merge --abort
  fi
  ```
- **Corrupted git index:** `git status` vrátí error → `state.error` + STOP + intake item `intake/close-git-corruption-{date}.md`.

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

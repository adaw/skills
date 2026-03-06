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

## K2 Fix: Task Merge Loop with Counter

```bash
MAX_TASKS=${MAX_TASKS:-50}
MERGE_COUNTER=0
```

When iterating through Task Queue to merge approved tasks:
```bash
while read -r task_id; do
  MERGE_COUNTER=$((MERGE_COUNTER + 1))
  if [ "$MERGE_COUNTER" -ge "$MAX_TASKS" ]; then
    echo "WARN: max task merges reached ($MERGE_COUNTER/$MAX_TASKS)"
    break
  fi
  # ... merge task
done
```

## K10 Fix: Concrete Close Example with LLMem Data

Here is a concrete example of closing a sprint task with real LLMem project context:

**Sprint-2 Task Merge: T-TRI-02 (Triage Heuristics)**

**Per-task close report:** `{WORK_ROOT}/reports/close-T-TRI-02-2026-03-06-run123.md`

```yaml
---
schema: fabric.report.v1
kind: close
version: "1.0"
task_id: "T-TRI-02"
sprint_number: 2
created_at: "2026-03-06T15:45:00Z"
merge_commit: "abc1234def567"
coverage_before_pct: 62
coverage_after_pct: 78
test_result: PASS
lint_result: PASS
---

# T-TRI-02 Close Report — Triage Heuristics

## Summary

Successfully merged feature/tri-02-heuristics into main. Deterministic triage heuristics now live in production. Coverage increased from 62% → 78% (target ≥60%, PASS).

## Merge Details

- **Branch:** feature/tri-02-heuristics
- **Merge Commit:** abc1234def567
- **Squash:** Yes (1 logical commit)
- **Review Status:** APPROVED (review-T-TRI-02-2026-03-05.md)
- **Test Results:** 9/9 PASS (triage suite)
- **Lint:** 0 errors

## Backlog Update

Updated `{WORK_ROOT}/backlog/T-TRI-02.md`:
```yaml
status: DONE
merge_commit: abc1234def567
branch: feature/tri-02-heuristics
updated: 2026-03-06
```

## Sprint Summary Impact

- Task Duration: 2 days (Sprint-2)
- Effort Actual: M (5 hours)
- Quality Gates: PASS (all)
- Coverage Contribution: +16% (T-TRI-02 focused: heuristics module)
```

## Vstupy

- `{WORK_ROOT}/config.md` (GIT + COMMANDS)
- `{WORK_ROOT}/state.md` (sprint N)
- `{WORK_ROOT}/sprints/sprint-{N}.md` (Task Queue)
- `{WORK_ROOT}/backlog/{id}.md` (branch + review_report)
- `{WORK_ROOT}/reports/review-*.md` (Verdict)
- `{WORK_ROOT}/reports/test-*.md` (evidence; volitelné)

---

## Výstupy

**Output schema (WQ9: version field):**

All reports use schema `fabric.report.v1` with optional `version: "1.0"` field for evolution tracking.

- **Per-task:** `{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md` *(pro každý mergovaný task — NESMÍ se přepisovat)*
  ```yaml
  ---
  schema: fabric.report.v1
  kind: close
  version: "1.0"
  task_id: "{wip_item}"
  created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
  ---
  ```
  ```bash
  # Overwrite guard (povinné):
  CLOSE_REPORT="{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md"
  if [ -f "$CLOSE_REPORT" ]; then
    echo "ERROR: close report already exists: $CLOSE_REPORT (idempotence — skip)"
  fi
  ```
- **Sprint summary:** `{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md` *(aktualizuj po každém close — append-only tabulky, přepiš jen Summary/Next)*
  ```yaml
  ---
  schema: fabric.report.v1
  kind: sprint-close
  version: "1.0"
  sprint_number: {N}
  created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
  ---
  ```
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
- (povinné) reset `state.wip_item` + `state.wip_branch` na null

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

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="closing"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-close. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

### Path Traversal Guard (K7: Input Validation)

```bash
# Path traversal guard — reject any input containing ".."
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}

# Apply to all dynamic path inputs:
# validate_path "$TASK_FILE"
# validate_path "$BRANCH_NAME"
```

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

### 2) Klasifikuj tasks: MERGEABLE vs CARRY-OVER (KONKRÉTNÍ PRAVIDLA)

Task je **MERGEABLE**, pokud:
```
MERGEABLE = backlog.status ∈ {IN_REVIEW, DONE}
  AND branch exists
  AND review verdict = CLEAN (not REWORK, not FAIL)
  AND test result = PASS
  AND no stubs in task files (grep pass/NotImplementedError)
```

Konkrétní kontrola:
```bash
TASK_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${id}.md" | awk '{print $2}')
TASK_BRANCH=$(grep 'branch:' "{WORK_ROOT}/backlog/${id}.md" | awk '{print $2}')
REVIEW_VERDICT=$(grep 'review_verdict:' "{WORK_ROOT}/backlog/${id}.md" | awk '{print $2}')

# Status check
if [ "$TASK_STATUS" != "IN_REVIEW" ] && [ "$TASK_STATUS" != "DONE" ]; then
  CARRY_OVER_REASON="STATUS_NOT_READY (status=$TASK_STATUS)"
fi

# Branch check
if ! git rev-parse --verify "$TASK_BRANCH" >/dev/null 2>&1; then
  CARRY_OVER_REASON="NO_BRANCH"
fi

# Review verdict check
if [ "$REVIEW_VERDICT" = "REWORK" ]; then
  CARRY_OVER_REASON="REWORK"
elif [ "$REVIEW_VERDICT" = "FAIL" ]; then
  CARRY_OVER_REASON="REVIEW_FAIL"
fi

# Stubs check
STUBS=$(git diff "${main_branch}...${TASK_BRANCH}" -- '*.py' 2>/dev/null | grep -cE 'pass$|raise NotImplementedError')
if [ "$STUBS" -gt 0 ]; then
  CARRY_OVER_REASON="STUBS_FOUND ($STUBS stubs)"
fi

# Decision
if [ -n "$CARRY_OVER_REASON" ]; then
  echo "CARRY_OVER: $id — reason: $CARRY_OVER_REASON"
else
  echo "MERGEABLE: $id"
fi
```

Jinak je **CARRY-OVER** s důvodem:
- `NO_BRANCH`: branch missing/deleted
- `NO_REVIEW`: review not completed
- `REWORK`: review verdict REWORK
- `BLOCKED`: external dependency not DONE
- `STUBS`: contains stubs/TODO
- `STATUS_NOT_READY`: status nije IN_REVIEW ani DONE

### 3) Pre-merge security scan (POVINNÉ na KAŽDÝ task)

Před merge proveď bezpečnostní kontrolu:
```bash
# Security scan na diff
git diff "${main_branch}...${branch}" -- '*.py' | grep -nE \
  'eval\(|exec\(|subprocess.*shell=True|__import__|pickle\.loads|yaml\.load\(|os\.system\(|input\(' \
  > /tmp/security-scan.txt 2>/dev/null

if [ -s /tmp/security-scan.txt ]; then
  echo "CRITICAL: potential security issues found in $id diff:"
  cat /tmp/security-scan.txt
  # Zapiš do intake pro review
  python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "security-scan-${id}" \
    --title "Security scan found potential issues in $id (review diff before merge)"
fi
```

### 4) Mergeable tasks mergeuj sekvenčně (bezpečně)

Pro každý MERGEABLE task v pořadí:

0. **Per-task stub verification (POVINNÉ):**
   ```bash
   # Ověř, že task kód neobsahuje stuby
   TASK_FILES=$(git diff --name-only "${main_branch}...${branch}" -- '*.py' 2>/dev/null)
   STUBS_FOUND=0
   for F in $TASK_FILES; do
     [ -f "$F" ] || continue
     if grep -qn 'pass$\|raise NotImplementedError\|# TODO\|# FIXME\|\.\.\.  # stub' "$F" 2>/dev/null; then
       echo "WARN: stub detected in $F for task $TASK_ID"
       STUBS_FOUND=$((STUBS_FOUND + 1))
     fi
   done
   if [ "$STUBS_FOUND" -gt 0 ]; then
     echo "WARN: $STUBS_FOUND files contain stubs — review may have missed them"
     # Nezastavuj merge — ale zapiš do close reportu jako WARNING
   fi
   ```

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

**Commit message quality validation (WQ8 ENFORCEMENT):**

Všechny merge commity MUSÍ splňovat:
```bash
# Pattern: feat({id}): {description} nebo fix({id}): {description}
# Requirements:
#   1. Format: type({id}): description (conventional commits)
#   2. Description: ≥10 characters (ne "fix stuff")
#   3. No generic verbs: "fix", "add", "update" alone (musí být specifické)

COMMIT_MSG=$(git log -1 --format=%B)
if ! echo "$COMMIT_MSG" | grep -qE '^(feat|fix|chore|refactor)\([A-Z]+-[0-9]+\): .{10,}'; then
  echo "ERROR: commit message format invalid: $COMMIT_MSG"
  echo "Expected: feat({id}): {description} (≥10 chars)"
  exit 1
fi

# Additional check: no lazy descriptions
if echo "$COMMIT_MSG" | grep -qE '(fix stuff|add code|update file|implement feature)'; then
  echo "WARN: commit message too generic: $COMMIT_MSG"
  echo "→ Better examples: feat(T-CAP-01): add instance_id validation in CaptureService"
fi
```

**Enforcement:**
- ✅ PASS: `feat(T-STR-01): add in-memory backend with thread-safe upsert`
- ✅ PASS: `fix(T-TRI-02): correct regex pattern for AWS secret detection`
- ❌ FAIL: `feat(T-ID): fix`
- ❌ FAIL: `feat: add feature without task id`
- ❌ WARN: `feat(T-ID): add code` (generic, but still accepted; encourage specificity)

6. **Post-merge rollback procedure (POVINNÉ — IF GATES FAIL)**:
   ```bash
   # Pokud se gates po merge failnou, rollback je MANDATORY
   # NEVER ponech failed code na main — vždy revert
   MERGE_COMMIT=$(git rev-parse HEAD)
   if [ "$GATE_RESULT" != "PASS" ]; then
     echo "ERROR: gates failed post-merge, initiating rollback"
     git revert -m 1 --no-edit "$MERGE_COMMIT"
     REVERT_EXIT=$?
     if [ $REVERT_EXIT -eq 0 ]; then
       # Verify tests pass na main AFTER revert
       timeout 300 {COMMANDS.test}
       VERIFY_EXIT=$?
       if [ $VERIFY_EXIT -eq 0 ]; then
         echo "SUCCESS: rollback complete, main is green again"
         # Vytvoř intake item pro triage
         python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "post-merge-rollback-${id}" \
           --title "Post-merge rollback for $id — gates failed, needs investigation"
       else
         echo "CRITICAL: tests FAIL after rollback — main is broken"
         echo "Manual intervention required: git log main, git diff main"
         exit 1
       fi
     fi
   fi
   ```
7. Spusť quality gates na main (bezpečně, podle `QUALITY.mode`):
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

8. Pokud gates FAIL:

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

   **8b) Revert (pokud auto-fix nepomohl nebo selhaly testy):**
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

9. Pokud gates PASS:
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

### 10) Regeneruj backlog index (po KAŽDÉM merge)

Deterministicky:
```bash
# OWNERSHIP: backlog.md regeneraci provádí VÝHRADNĚ fabric.py backlog-index
# Nikdy neregeneruj backlog.md ručně — vždy volej tento příkaz.
python skills/fabric-init/tools/fabric.py backlog-index
```

Tím se `{WORK_ROOT}/backlog.md` synchronizuje se skutečným stavem backlog items. Nečekej na konec sprintu — **regeneruj po každém merge**, aby byl backlog.md vždy aktuální.

### 11) Per-task close report (povinné)

Pro KAŽDÝ mergovaný task vytvoř **samostatný** report:

`{WORK_ROOT}/reports/close-{wip_item}-{YYYY-MM-DD}-{run_id}.md`

Obsah:
- Task ID, title, branch, merge commit SHA
- Quality evidence (test PASS/FAIL, lint PASS/FAIL/SKIPPED)
- Carry-over: ne (pokud DONE) nebo důvod

> **NESMÍŠ přepisovat existující per-task close report.** Každý task = 1 soubor. To zajišťuje kompletní audit trail.

### 12) Sprint summary report (append-only, strukturovaný)

`{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md` — MUSÍ MAJÍ tuto strukturu:

```markdown
## Sprint {N} Summary

### Merged Tasks
| ID | Title | Branch | Merge Commit | Coverage Delta | Status |
|---|---|---|---|---|---|
| {id} | {title} | {branch} | {sha} | +2% | DONE |

### Carry-over Tasks
| ID | Title | Reason | Next Action |
|---|---|---|---|
| {id2} | {title2} | REWORK | Address review feedback, re-run review |

### Quality Metrics
- Coverage: {CURRENT_COV}% (delta: {COV_DELTA}%)
- Lint: PASS | SKIPPED
- Format: PASS | SKIPPED
- Tests: PASS
- E2E: PASS | SKIPPED

### Risk Register
- {any regressions detected}
- {security findings}

### Summary
Sprint {N} merged {N_DONE} tasks, {N_CARRY} carry-over. Coverage trend: {up|stable|down}. No critical blockers.

### Next
For sprint {N+1}: {carry-over recommendations}
```

**FILLED-IN EXAMPLE (Sprint 1, LLMem project):**

```markdown
## Sprint 1 Summary

### Merged Tasks
| ID | Title | Branch | Merge Commit | Coverage Delta | Status |
|---|---|---|---|---|---|
| T-CAP-01 | Add ObservationEvent schema validation | feature/cap-01-validation | 5a8c2d9 | +3% | DONE |
| T-TRI-02 | Implement deterministic triage heuristics | feature/tri-02-heuristics | 7b4f1e2 | +5% | DONE |
| T-STR-01 | Add in-memory backend for dev/test | feature/str-01-inmem | 3c9e6b5 | +2% | DONE |

### Carry-over Tasks
| ID | Title | Reason | Next Action |
|---|---|---|---|
| T-REC-01 | Add recall scoring + injection | REWORK | Review found missing error handling in scoring edge cases; revise ≥2 tests, re-run review |

### Quality Metrics
- Coverage: 74% (delta: +3% vs Sprint 0)
- Lint: PASS
- Format: PASS
- Tests: PASS
- E2E: SKIPPED (not configured)

### Risk Register
- **Deterministic ID generation**: SHA256-based; depends on stable content hash (low risk, unit tested)
- **Secrets in triage output**: No new secrets leaked in non-secret items; regex patterns validated

### Summary
Sprint 1 merged 3 tasks (T-CAP-01, T-TRI-02, T-STR-01), 1 carry-over (T-REC-01 pending rework). Coverage improved +3% to 74% (target: ≥70%). Core capture/triage/store pipeline validated end-to-end. No critical blockers.

### Next
For sprint 2: Start with T-REC-01 rework (should be quick), then tackle T-REC-01 again + new tasks from recall path. Consider adding E2E test suite to catch integration gaps earlier.
```

**Enforcement (konkrétní):**
```bash
# Vytvoř sprint summary na ZAČÁTKU close (jedna instance per sprint)
SPRINT_REPORT="{WORK_ROOT}/reports/close-sprint-${N}-$(date +%Y-%m-%d).md"
if [ ! -f "$SPRINT_REPORT" ]; then
  # Create fresh from template
  cp {WORK_ROOT}/templates/close-report.md "$SPRINT_REPORT"
fi

# Nyní append do tabulek, NEPŘEPISUJ existující
# Po KAŽDÉM merge: aktualizuj "Merged Tasks" tabulka
# Po ALL merges: update "Carry-over" tabulka
# At END: update "Quality Metrics" + "Summary" + "Next"
```

### 13) Reset WIP (povinné — ATOMIC WRITE)

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

### 14) Sprint-wide quality gates (povinné — BLOCKING)

Po zpracování VŠECH tasks (merge/carry-over) a PŘED finálním sprint summary spusť sprint-wide quality gates:

#### 14a) Coverage delta check (BLOCKING — delta < -5% = FAIL)

```bash
# Spusť coverage na main po všech mergích
if [ -n "{COMMANDS.test}" ] && [ "{COMMANDS.test}" != "TBD" ]; then
  # Baseline: coverage z minulého sprintu (pokud existuje)
  PREV_SPRINT=$((N - 1))
  BASELINE_COV=$(grep 'coverage_pct:' "{WORK_ROOT}/reports/close-sprint-${PREV_SPRINT}-"*.md 2>/dev/null | tail -1 | awk '{print $2}' | tr -d '%')
  BASELINE_COV=${BASELINE_COV:-0}

  # Aktuální coverage
  timeout 300 pytest --cov=src --cov-report=term-missing --tb=no -q 2>/dev/null | tee /tmp/cov-output.txt
  CURRENT_COV=$(grep '^TOTAL' /tmp/cov-output.txt | awk '{print $NF}' | tr -d '%')
  CURRENT_COV=${CURRENT_COV:-0}

  # Delta
  COV_DELTA=$((CURRENT_COV - BASELINE_COV))
  echo "Coverage: ${CURRENT_COV}% (delta: ${COV_DELTA}% vs sprint $PREV_SPRINT)"

  # BLOCKING GATE: coverage delta < -5% = FAIL sprint close
  if [ "$COV_DELTA" -lt -5 ]; then
    echo "CRITICAL: coverage regression ${COV_DELTA}% detected — BLOCKING close"
    python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "coverage-regression-block-sprint-${N}" \
      --title "Coverage regression BLOCKS close: ${CURRENT_COV}% (was ${BASELINE_COV}%, delta ${COV_DELTA}%, threshold -5%)"
    exit 1  # FAIL entire close operation
  # WARN pokud coverage klesla o 0-5%
  elif [ "$COV_DELTA" -lt 0 ]; then
    echo "WARN: coverage regressed ${COV_DELTA}% (acceptable, delta > -5%)"
    python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "coverage-warn-sprint-${N}" \
      --title "Coverage regressed ${COV_DELTA}% — acceptable but investigate"
  fi
fi
```

**Anti-patterns:**
- ❌ Přeskočit coverage check protože „testy prošly"
- ❌ Akceptovat delta < -5% bez FAIL
- ✅ Vždy zaznamenat coverage_pct do sprint summary reportu
- ✅ BLOCKING gate: delta < -5% = FAIL sprint close

**Carry-over anti-patterns (WQ4: detection + fix):**

| Anti-pattern | Description | Detection Bash | Remediation |
|---|---|---|---|
| **Same task carried 2+ sprints** | Task in CARRY-OVER for ≥2 consecutive sprints = scope/priority issue | `grep -r "^id: T-ID$" {WORK_ROOT}/reports/close-sprint-*.md \| wc -l` (if ≥2, WARN) | 1. Assess if task is still valuable (consider removing). 2. If yes: split into smaller sub-tasks with clearer AC. 3. Add blocker intake item: `task-stuck-{N}-sprints.md` |
| **Reason not documented** | Carry-over without explicit reason = unclear what blocks it | `grep -A1 "T-ID\|" {WORK_ROOT}/reports/close-sprint-*.md \| grep -q "Reason"` (if no match, FAIL) | 1. Retrospectively document reason in close report. 2. File intake item: `carry-over-reason-missing-{id}.md` with details. |
| **No concrete next action** | "Address feedback" is too vague; should be: "Fix line 42 in models.py, add 2 edge case tests" | `grep "Next Action" {WORK_ROOT}/reports/close-sprint-*.md \| grep -cE "^(fix|add|refactor)\s+" ` (count concrete verbs) | Rewrite next action with: concrete file/line + specific test to add + estimated effort for sprint N+1. |
| **REWORK carried >1 sprint** | REWORK verdict but task not re-reviewed yet = review blocker not cleared | For each REWORK in close report: `ls -t {WORK_ROOT}/reports/review-${id}-*.md \| head -1 | xargs grep "verdict:" \| grep -q "REWORK"` then check if review_report updated in backlog; if no new review, CRITICAL | 1. Schedule immediate re-review with explicit feedback addressed. 2. Update backlog `review_report:` field with path to new review when available. 3. Create intake item: `rework-stuck-${id}.md`. |
| **Dependency never resolves** | Task blocked on DEP that is also CARRY-OVER or never reaches DONE | `for task in $(grep "depends_on:" {WORK_ROOT}/backlog/{id}.md); do grep "status: DONE" {WORK_ROOT}/backlog/${task}.md || echo "UNRESOLVED: $task"; done` | 1. Break circular dependency: reassign blockers to separate sprint. 2. Or: implement task without blocker (architectural change). 3. Create intake item: `dependency-blocker-{id}-{dep}.md` with options. |

#### 14b) E2E verification (WARN + INTAKE, ne BLOCKING)

```bash
# E2E smoke test na main po všech mergích
if [ -n "{COMMANDS.test_e2e}" ] && [ "{COMMANDS.test_e2e}" != "TBD" ]; then
  echo "Running sprint-wide E2E verification on main..."
  timeout 600 {COMMANDS.test_e2e}
  E2E_EXIT=$?
  if [ $E2E_EXIT -eq 124 ]; then
    echo "TIMEOUT: E2E sprint verification exceeded 600s"
    E2E_SPRINT_RESULT="TIMEOUT"
    # WARN + INTAKE, ne FAIL close
    python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "e2e-sprint-timeout-${N}" \
      --title "E2E sprint verification TIMEOUT (600s) — investigate performance"
  elif [ $E2E_EXIT -ne 0 ]; then
    echo "WARN: E2E sprint verification FAILED"
    E2E_SPRINT_RESULT="FAIL"
    # WARN + INTAKE, ne FAIL close
    python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "e2e-sprint-fail-${N}" \
      --title "E2E sprint verification failed after all merges (sprint ${N}) — investigate flakiness"
  else
    E2E_SPRINT_RESULT="PASS"
  fi
else
  E2E_SPRINT_RESULT="SKIPPED"
fi
```

**Note:** E2E FAIL/TIMEOUT je WARN + INTAKE, NENÍ blocking close. Close pokračuje, ale E2E failure se sleduje jako issue.

#### 14c) Sprint-diff review (doporučeno, WARN na security)

Celkový diff sprintu může odhalit problémy, které per-task review nechytil (cross-task interakce, duplicitní kód, nekonzistentní naming):

```bash
# Sprint diff: všechny změny od začátku sprintu
SPRINT_START_SHA=$(grep 'sprint_start_sha:' "{WORK_ROOT}/sprints/sprint-${N}.md" 2>/dev/null | awk '{print $2}')
if [ -n "$SPRINT_START_SHA" ]; then
  SPRINT_DIFF_STAT=$(git diff --stat "$SPRINT_START_SHA"...HEAD)
  SPRINT_DIFF_FILES=$(git diff --name-only "$SPRINT_START_SHA"...HEAD | wc -l)
  echo "Sprint diff: $SPRINT_DIFF_FILES files changed"

  # Pokud ≥20 souborů změněno → spusť sprint-wide review dimenze
  if [ "$SPRINT_DIFF_FILES" -ge 20 ]; then
    echo "ACTION: large sprint diff ($SPRINT_DIFF_FILES files) — running sprint-wide R1-R8 quick scan"
    # Quick R1-R8 scan na sprint diff (ne plný review — jen critical/high hledání)
    SPRINT_DIFF=$(git diff "$SPRINT_START_SHA"...HEAD -- '*.py')

    # R2 Security quick scan
    SECURITY_HITS=$(echo "$SPRINT_DIFF" | grep -c 'eval(\|exec(\|subprocess.*shell=True\|pickle.loads\|yaml.load(' 2>/dev/null || echo 0)
    if [ "$SECURITY_HITS" -gt 0 ]; then
      echo "CRITICAL: $SECURITY_HITS potential security issues in sprint diff"
    fi

    # R4 Reliability quick scan
    RELIABILITY_HITS=$(echo "$SPRINT_DIFF" | grep -c 'except:$\|except Exception:$' 2>/dev/null || echo 0)
    if [ "$RELIABILITY_HITS" -gt 0 ]; then
      echo "WARN: $RELIABILITY_HITS bare except blocks in sprint diff"
    fi

    # R6 Maintainability quick scan
    # (large functions detection is harder in diff, skip for now)

    echo "Sprint R1-R8 quick scan: security=$SECURITY_HITS, reliability=$RELIABILITY_HITS"
    # Pokud CRITICAL > 0 → vytvoř intake item
    if [ "$SECURITY_HITS" -gt 0 ]; then
      python skills/fabric-init/tools/fabric.py intake-new --source "close" --slug "sprint-security-scan-${N}" \
        --title "Sprint-wide security scan found $SECURITY_HITS potential issues"
    fi
  fi
else
  echo "WARN: sprint_start_sha not found — cannot compute sprint diff"
fi
```

**Minimum:** Sprint summary report MUSÍ obsahovat:
- `coverage_pct: {CURRENT_COV}%` (nebo `N/A` pokud nelze spočítat)
- `e2e_result: {PASS|FAIL|TIMEOUT|SKIPPED}`
- `sprint_diff_files: {N}`

---

## Downstream Contract (WQ7)

**fabric-close** contracts with **downstream skills:**

| Skill | Contract | Enforcement |
|-------|----------|------------|
| **fabric-loop** | Sprint must end with: all tasks DONE or CARRY-OVER (no BLOCKED/PAUSED). WIP fields reset to null. Close report + sprint summary present. | Loop detects malformed state via `state.md` validation; fails if wip_item not null after close |
| **fabric-implement** (rework cycle) | CARRY-OVER tasks have explicit reason + next action. Review report path in backlog updated (if rework). | Implement reads CARRY-OVER reason; if missing, creates intake item + skips task |
| **fabric-review** (next sprint) | Merge commits recorded in backlog (`merge_commit:` field). Task status = DONE. Branch deleted or documented as remote. | Review may query merge_commit for cherry-pick decisions; if missing, raises WARN |
| **backlog index** | All DONE items updated in index. Coverage metrics in sprint report. | `fabric-loop` runs backlog-index after close; verifies DONE count consistency |

**Errors that break contract (CRITICAL):**
- ❌ WIP fields not reset (wip_item or wip_branch not null) → loop cannot select next task
- ❌ Sprint summary missing or malformed → no metrics for decision-making
- ❌ CARRY-OVER task without documented reason → implement cannot decide if to retry
- ❌ Merge commit missing in backlog DONE tasks → loss of audit trail

---

## Fail conditions

**BLOCKING ENFORCEMENT (WQ10: CRITICAL findings MUST fail close):**

- ❌ CRITICAL: `COMMANDS.test` je `TBD` nebo prázdné → **EXIT 1** (entire close fails)
  ```bash
  if [ -z "{COMMANDS.test}" ] || [ "{COMMANDS.test}" = "TBD" ]; then
    echo "CRITICAL: COMMANDS.test not configured"
    exit 1
  fi
  ```
- ❌ CRITICAL: Coverage regression ≥ -5% → **EXIT 1** (sprint close blocked)
- ❌ CRITICAL: Security scan finds ≥1 critical issue (eval, exec, pickle.loads) → **EXIT 1** (merge blocked for that task, intake created)
- ❌ CRITICAL: Tests FAIL on main post-merge AND revert fails → **EXIT 1** (manual intervention required)
- ❌ CRITICAL: Git corruption detected (merge-in-progress, index error) → **EXIT 1** (manual recovery)

**Non-blocking (warnings that don't fail close):**
- ⚠️ WARN: Coverage regressed 0–4% (acceptable)
- ⚠️ WARN: E2E test timeout (investigate, but don't block)
- ⚠️ WARN: Lint/format skipped (mode=bootstrap)

V těchto CRITICAL případech: vytvoř intake item + loguj error + **exit 1 (FAIL entire close dispatch)**.

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

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/close-sprint-{N}-{YYYY-MM-DD}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] WIP branch smazán (nebo explicitně zachován s důvodem v reportu)
- [ ] Protocol log má START a END záznam s `skill: close`

### Quality checks (BLOCKING ENFORCEMENT)
- [ ] **Všechny DONE tasky squash-mergnuty do main** (nebo REDESIGN/BLOCKED) — commit history čistý
- [ ] **COMMANDS.test PASS na main** (post-merge) — testy prošly po integraci
- [ ] **COMMANDS.test_e2e PASS na main** (pokud definován) — e2e testy bez regresí
- [ ] **COMMANDS.lint PASS na main** (po případném auto-fix) — kód je čistý
- [ ] **state.wip_item = null** a **state.wip_branch = null** — state reset po zavření
- [ ] **Close report** obsahuje sekce: Summary (N tasků DONE, M REDESIGN, K BLOCKED), Changes, Quality, Warnings
- [ ] **Sprint plan** aktualizován — všechny task statuses reflektují final state

### Invariants
- [ ] Backlog itemy se statusem DONE mají aktualizované metadata (`merged_at`, `commit_hash`)
- [ ] State.md aktualizován: `current_sprint = null` (pokud je end-of-sprint close) nebo `sprint = N+1` (pokud next sprint)
- [ ] Protocol log má START i END záznam
- [ ] Žádný lokální commit zbývá nemergnený v main

Pokud ANY check FAIL → **FAIL + vytvoř intake item `intake/close-selfcheck-failed-{date}.md`** (ne exit, ale WARN).

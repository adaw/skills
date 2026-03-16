---
name: fabric-hotfix
description: "Ad-hoc implementation outside sprint planning: analysis, code, tests, review, and merge in one dispatch. For urgent XS/S fixes and small features with full quality gates and fast-track lifecycle."
---
<!-- built from: builder-template -->

# HOTFIX — Ad-hoc implementace mimo sprint (fast-track)

---

## §1 — Účel

Rychlá implementace malých fixů a features **mimo sprint plánování**. Kompletní mini-lifecycle
v jednom dispatch: analýza → kód → testy → review → merge → report.

Bez tohoto skillu urgentní fixy buď blokují sprint (čekají na další cyklus),
nebo se dělají ad-hoc bez quality gates (regrese).

**Kdy použít:**
- XS/S effort (max 1 den práce)
- Urgentní bug fix nebo drobná feature
- Infrastrukturní vylepšení (tooling, config, DX)
- Cokoli co nestojí za celý sprint

**Kdy NEPOUŽÍT:**
- M/L/XL effort → plný sprint (fabric-sprint → fabric-implement)
- Architektonické změny → fabric-design → sprint
- Nová feature vyžadující specifikaci → fabric-intake → fabric-design → sprint

---

## §2 — Protokol (povinné — NEKRÁTIT)

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "hotfix" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "hotfix" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "hotfix" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Hotfix NEMÁ sprint prereqs — celý smysl je obejít sprint planning. Ale potřebuje:

**5 povinných kontroly:**
1. Config existuje: `{WORK_ROOT}/config.md`
2. State existuje: `{WORK_ROOT}/state.md`
3. COMMANDS.test nakonfigurován (ověř v config.md)
4. Git working tree čistý (no uncommitted changes)
5. Effort guard: akceptuj jen effort z config.md `HOTFIX.max_effort` (default: XS,S; M+ → doporuč sprint)

```bash
# K7: Path traversal guard
for VAR in "{WORK_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# K6: Dependency enforcement — init must have run
if [ ! -f "{WORK_ROOT}/config.md" ] || [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: fabric-init must run first (config.md or state.md missing)"
  exit 1
fi

# K6: Backlog directory must exist (for optional backlog item linking)
if [ ! -d "{WORK_ROOT}/backlog" ]; then
  echo "STOP: backlog/ directory required — run fabric-init first"
  exit 1
fi

# K4: Git safety — verify clean working tree before hotfix
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "STOP: git working tree not clean — commit or stash changes first"
  exit 1
fi

# K4: COMMANDS.test configured
COMMANDS_TEST=$(grep 'COMMANDS.test:' "{WORK_ROOT}/config.md" 2>/dev/null | grep -v test_e2e | head -1 | sed 's/.*: //' || echo "") || { echo "ERROR: failed to read COMMANDS.test from config.md"; exit 1; }
if [ -z "$COMMANDS_TEST" ] || [ "$COMMANDS_TEST" = "TBD" ]; then
  echo "STOP: COMMANDS.test not configured"
  exit 1
fi
```

**Detail implementace viz:** `references/preconditions.md`

**Dependency chain:** `fabric-init → [tento skill] (bez dalších prereqs)`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (COMMANDS, GIT, cesty)
- `{WORK_ROOT}/state.md` (aktuální stav — hotfix ho NESMÍ modifikovat kromě wip)
- Popis požadavku od uživatele (text — co má hotfix udělat)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/backlog/{id}.md` — pokud hotfix řeší existující backlog item
- `{WORK_ROOT}/decisions/` — pro governance cross-check
- `{WORK_ROOT}/specs/` — pro compliance check
- `dev/workflows/hotfix.md` — referenční kvalita starého workflow

---

## §5 — Výstupy

### Primární (vždy)
- Merge commit na main (squash merge hotfix branch)
- Report: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Backlog item: `{WORK_ROOT}/backlog/{id}.md` (nový nebo aktualizovaný → DONE)
- Intake items: `{WORK_ROOT}/intake/hotfix-{slug}.md` (pokud findings)
- Regenerovaný `{WORK_ROOT}/backlog.md` (po merge)

---

## §6 — Deterministic FAST PATH

```bash
# 1. Backlog index sync (pokud hotfix pracuje s backlogem)
python skills/fabric-init/tools/fabric.py backlog-index 2>/dev/null || true

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null || true

# 3. Zjisti hlavní branch
MAIN_BRANCH=$(grep 'main_branch:' "{WORK_ROOT}/config.md" 2>/dev/null | awk '{print $2}' || echo "") || { echo "ERROR: failed to read main_branch from config.md"; exit 1; }
MAIN_BRANCH=${MAIN_BRANCH:-main}
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### State Validation (K1: State Machine)
Check current phase is compatible with this skill. Valid phases: `implementation`, `closing`.

### Path Traversal Guard (K7: Input Validation)
Reject any input containing `..` (path traversal attack prevention).

### Counter Initialization (K2)

```bash
# K5: Read from config.md
CONFIG_MAX_RETRIES=$(grep 'HOTFIX.max_retries:' "{WORK_ROOT}/config.md" 2>/dev/null | awk '{print $2}' || echo "") || { echo "ERROR: failed to read MAX_RETRIES from config.md"; exit 1; }
MAX_RETRIES=${CONFIG_MAX_RETRIES:-${MAX_RETRIES:-3}}
LINT_RETRY_COUNT=0
FORMAT_RETRY_COUNT=0

# K2: Numeric validation
if ! echo "$MAX_RETRIES" | grep -qE '^[0-9]+$'; then
  MAX_RETRIES=3
  echo "WARN: MAX_RETRIES not numeric, reset to default (3)"
fi
```

### H1: Analýza požadavku
Pochop co hotfix má udělat, ověř effort, zkontroluj backlog.
**Detail:** `references/h1-analysis.md`

### H2: Implementace
Kód + minimálně 3 testy (happy/edge/error) na dedikované hotfix branch.
**Detail:** `references/h2-implementation.md`

### H3: Quality Gates
Spusť lint + testy (K2 guards: LINT_RETRY_COUNT, FORMAT_RETRY_COUNT numeric validation).
**Detail:** `references/h3-quality-gates.md`

### H4: Fast-track Review (self-review)
Quick review hotfix diff PŘED merge (R1–R4 dimenze: správnost, error handling, bezpečnost, testy).
**Detail:** `references/h4-review.md`

### H5: Commit + Merge
Commitni na hotfix branch, squash merge do main, post-merge test run POVINNÝ.
**Detail:** `references/h5-commit-merge.md`

### H6: Backlog + Docs Update
Aktualizuj backlog item na DONE, regeneruj index, updatuj docs pokud se týká.
**Detail:** `references/h6-backlog-docs.md`

### H7: Report
Hotfix report se souhrnem evidence (schema: fabric.report.v1).
**Detail:** `references/h7-report.md`

### K10: Inline Example — LLMem Hotfix Null Pointer Fix

**Input:** Critical bug report: "null pointer in scoring.py L127 when recall_query.scope is None", effort: XS, task-b020 created.
**Output:** Hotfix branch created, bug fixed in scoring.py (1 file touched), 3 tests added (happy: scope=None returns default, edge: scope=explicit, error: invalid scope type), lint PASS, tests PASS pre-merge, squash merged: fix(b020): handle null scope in scoring.combine_score, post-merge tests PASS, backlog item task-b020 status→DONE, report: hotfix-2026-03-06-run1.md with evidence table.

### K10: Anti-patterns (s detekcí)
```bash
# A1: Hotfixing M-effort tasks (>1 day work) — Detection: effort field = M|L|XL in hotfix request
# A2: Hotfix without minimum 3 tests — Detection: git diff --name-only hotfix | grep test | wc -l < 3
# A3: Force push to main (git push --force) — Detection: git log --oneline -5 | grep 'Merge pull request' (should be merge commit)
# A4: Skipping lint/format gates — Detection: ! grep -E 'lint_result: (PASS|SKIP)' {hotfix-report}
```

---

## §8 — Quality Gates

Four gates (detailed viz `references/quality-gates-summary.md`):
1. **Lint** — timeout 120s, auto-fix with K2 guards
2. **Format Check** — timeout 120s, auto-fix with K2 guards
3. **Tests (pre-merge)** — timeout 300s, MUST PASS
4. **Tests (post-merge)** — timeout 300s, MUST PASS (else revert)

---

## §9 — Report

Hotfix report path: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md`

Schema: `fabric.report.v1` with status, task_id, effort, merge_commit, evidence table, changed files.

**Template viz:** `references/h7-report.md`

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence Checks
- [ ] Report exists: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md` with schema frontmatter
- [ ] Backlog item exists: `{WORK_ROOT}/backlog/{TASK_ID}.md` with `status: DONE`
- [ ] Merge commit on main: `git log --oneline | grep "${TASK_ID}"` (commit on main branch)
- [ ] Protocol log has START and END: both entries with status

```bash
# Existence verification
TASK_ID="${1}"
if [ ! -f "{WORK_ROOT}/reports/hotfix-$(date +%Y-%m-%d)-"*.md ]; then
  echo "ERROR: hotfix report not found"
  exit 1
fi
if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  echo "ERROR: backlog item not found: {WORK_ROOT}/backlog/${TASK_ID}.md"
  exit 1
fi
STATUS=$(grep "^status:" "{WORK_ROOT}/backlog/${TASK_ID}.md" | awk '{print $2}')
if [ "$STATUS" != "DONE" ]; then
  echo "ERROR: backlog item status is '$STATUS' (expected DONE)"
  exit 1
fi
echo "✓ Existence checks passed"
```

### Quality Checks
- [ ] Post-merge tests PASS: `{COMMANDS.test}` exit code = 0 after merge
- [ ] Hotfix branch deleted: `git branch -a | grep -c "hotfix-${TASK_ID}"` = 0
- [ ] Backlog index regenerated: `{WORK_ROOT}/backlog.md` includes merged item
- [ ] Report has schema: `schema: fabric.report.v1` in frontmatter
- [ ] Minimum 3 tests: git diff shows ≥3 test additions/updates (happy/edge/error)
- [ ] Self-review documented: report contains R1-R4 (Correctness, Error Handling, Security, Tests)

```bash
# Quality verification
REPORT=$(ls -t "{WORK_ROOT}/reports/hotfix-"*.md 2>/dev/null | head -1)
[ -z "$REPORT" ] && exit 1

if ! grep -q "schema: fabric.report.v1" "$REPORT"; then
  echo "ERROR: report missing schema frontmatter"
  exit 1
fi

# Verify branch is deleted
if git branch -a 2>/dev/null | grep -q "hotfix-"; then
  echo "WARN: hotfix branches still exist (should be deleted)"
fi

# Verify test count (approximate via diff)
TESTS_TOUCHED=$(git diff HEAD~1 HEAD --name-only 2>/dev/null | grep -c test)
if [ "$TESTS_TOUCHED" -lt 1 ]; then
  echo "WARN: no test files in merge commit (expected ≥3 test cases)"
fi

echo "✓ Quality checks passed"
```

### Invariants
- [ ] `state.md` unchanged: phase/step/sprint values identical to pre-hotfix
- [ ] Only wip_item/wip_branch reset to null: no other state changes
- [ ] Protocol log clean: START < END, both with status
- [ ] No force push: `git log --oneline -1 | grep "^[a-f0-9]" | grep -v "Merge"` = standard commit
- [ ] Working tree clean: `git status --porcelain` only shows reports/

```bash
# Invariant verification
# 1. Verify state.md not modified (except wip fields)
STATE_HASH_BEFORE=$(git show HEAD~1:"{WORK_ROOT}/state.md" 2>/dev/null | grep -v "^wip_" | md5sum)
STATE_HASH_AFTER=$(cat "{WORK_ROOT}/state.md" | grep -v "^wip_" | md5sum)

if [ "$STATE_HASH_BEFORE" != "$STATE_HASH_AFTER" ]; then
  echo "ERROR: state.md was modified beyond wip fields"
  exit 1
fi

# 2. Verify wip_item/wip_branch reset
WIP_ITEM=$(grep "^wip_item:" "{WORK_ROOT}/state.md" | awk '{print $2}')
WIP_BRANCH=$(grep "^wip_branch:" "{WORK_ROOT}/state.md" | awk '{print $2}')

if [ "$WIP_ITEM" != "null" ] || [ "$WIP_BRANCH" != "null" ]; then
  echo "ERROR: wip_item/wip_branch not reset to null"
  exit 1
fi

# 3. Verify no force push
if git log --oneline -3 2>/dev/null | grep -q "force"; then
  echo "ERROR: force push detected (use only standard merges)"
  exit 1
fi

echo "✓ Invariant checks passed"
```

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Config/state chybí | STOP + „run fabric-init first" |
| Preconditions | Effort > S | STOP + „use fabric-sprint" |
| Preconditions | Dirty working tree | STOP + „commit or stash first" |
| H2 Implementace | Testy stále failing | Oprav testy (max 3 iterace) → FAIL + intake item |
| H3 Quality Gates | Lint FAIL po auto-fix | Oprav manuálně → pokud stále FAIL → intake item |
| H3 Quality Gates | Tests TIMEOUT (124) | WARN + intake item pro slow tests |
| H4 Review | R1/R2/R3 finding | Oprav PŘED merge (nečekej) |
| H5 Merge | Merge conflict | Abort merge → intake item → manuální resolution |
| H5 Merge | Post-merge tests FAIL | `git revert --no-edit HEAD` → intake item |
| H5 Merge | Revert FAIL (conflict) | `git revert --abort` → CRITICAL → manuální intervence |

**Obecné pravidlo:** Hotfix je fail-fast — při jakémkoli problému raději STOP než riskovat regresi na main.

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
depends_on: [fabric-init]
feeds_into: [fabric-check]
phase: utility
lifecycle_step: hotfix
touches_state: false
touches_git: true
estimated_ticks: 1
idempotent: false
fail_mode: fail-open
```

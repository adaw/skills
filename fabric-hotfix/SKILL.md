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

```bash
# --- Precondition 1: Config existuje ---
if [ ! -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: {WORK_ROOT}/config.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 2: State existuje ---
if [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: {WORK_ROOT}/state.md not found — run fabric-init first"
  exit 1
fi

# --- Precondition 3: COMMANDS.test je nakonfigurovaný ---
TEST_CMD=$(grep 'test:' "{WORK_ROOT}/config.md" | head -1 | sed 's/.*test:\s*//')
if [ -z "$TEST_CMD" ] || [ "$TEST_CMD" = "TBD" ]; then
  echo "STOP: COMMANDS.test not configured — hotfix needs tests"
  exit 1
fi

# --- Precondition 4: Git working tree čistý ---
if [ -n "$(git status --porcelain)" ]; then
  echo "STOP: dirty working tree — commit or stash first"
  exit 1
fi

# --- Precondition 5: Effort guard (user input) ---
# Pokud user nedal explicitní effort, zeptej se.
# Akceptuj jen XS nebo S. Pokud M+ → STOP s doporučením sprint.
EFFORT="${HOTFIX_EFFORT:-XS}"
case "$EFFORT" in
  XS|S) echo "Effort: $EFFORT — OK for hotfix" ;;
  M|L|XL) echo "STOP: effort $EFFORT is too large for hotfix — use fabric-sprint"; exit 1 ;;
  *) echo "WARN: unknown effort '$EFFORT', assuming XS" ; EFFORT="XS" ;;
esac
```

**Dependency chain:**
```
fabric-init → [tento skill] (bez dalších prereqs)
```

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
MAIN_BRANCH=$(grep 'main_branch:' "{WORK_ROOT}/config.md" | awk '{print $2}')
MAIN_BRANCH=${MAIN_BRANCH:-main}
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="implementation closing"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-hotfix. Expected: $EXPECTED_PHASES"
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
# validate_path "$HOTFIX_FILE"
# validate_path "$BRANCH_NAME"
```

### 7.1) H1: Analýza požadavku

**Co:** Pochop co hotfix má udělat, ověř effort, zkontroluj backlog.

**Jak (detailní instrukce):**
1. Přečti popis požadavku od uživatele.
2. Zkontroluj zda požadavek existuje v backlogu:
   ```bash
   # Hledej v backlogu
   grep -rl "${KEYWORD}" "{WORK_ROOT}/backlog/" 2>/dev/null | head -5
   ```
3. Pokud existuje backlog item → použij ho (zachovej ID, aktualizuj status).
4. Pokud NEexistuje → vytvoř nový:
   ```bash
   python skills/fabric-init/tools/fabric.py intake-new \
     --source "hotfix" \
     --slug "hotfix-${SLUG}" \
     --title "${TITLE}"
   ```
5. Odhadni effort:
   - XS: < 20 řádků kódu, 1–2 soubory
   - S: < 100 řádků, 3–5 souborů
   - **Pokud odhad > S → STOP a doporuč sprint.**

**Minimum:**
- Identifikovaný nebo vytvořený backlog item s ID
- Effort odhad (XS/S)
- Seznam dotčených souborů (min. 1)

**Anti-patterns (zakázáno):**
- Implementovat M+ effort jako hotfix (skrytý tech debt)
- Ignorovat existující backlog item a vytvořit duplicitu
- Začít implementovat bez pochopení scope

### 7.2) H2: Implementace

**Co:** Kód + testy na dedikované hotfix branch.

**Jak (detailní instrukce):**
1. Vytvoř branch:
   ```bash
   git checkout "${MAIN_BRANCH}"
   git pull --ff-only || echo "WARN: pull failed, using local main"
   HOTFIX_BRANCH="hotfix/${TASK_ID}"
   git checkout -b "${HOTFIX_BRANCH}"
   ```
2. Implementuj minimální změnu — jen to co je nutné.
3. Piš testy SOUČASNĚ s kódem:
   - **Minimálně 3 testy per hotfix:**
     1. Happy path — hlavní funkce funguje
     2. Edge case — hraniční vstup / prázdný vstup / null
     3. Error handling — neplatný vstup / chybový stav
   - Pokud hotfix přidává endpoint/CLI/tool → přidej integrační test
4. Dodržuj coding style projektu (ruff, type hints, 100 char line).

**Minimum:**
- Funkční kód řešící požadavek
- Minimálně 3 testy (happy/edge/error)
- Žádné `pass`, `NotImplementedError`, `# TODO` v DONE kódu

**Anti-patterns (zakázáno):**
- `pass` nebo `# TODO` v hotfix kódu — hotfix je DONE, ne WIP
- `NotImplementedError` stub — to není hotfix, to je placeholder
- Jeden test nebo žádné testy — min. 3
- Hotfix bez testů „protože je to malá změna" — NEAKCEPTOVATELNÉ
- Změna v nesouvisejících souborech (scope creep)

**Šablona testu:**
```python
# tests/test_{module}_hotfix.py
import pytest

class TestHotfix{Feature}:
    """Tests for hotfix: {popis}."""

    def test_happy_path(self):
        """Main functionality works as expected."""
        # Arrange
        # Act
        # Assert
        ...

    def test_edge_case(self):
        """Boundary/empty/null input handled correctly."""
        ...

    def test_error_handling(self):
        """Invalid input raises appropriate error."""
        with pytest.raises(ValueError):
            ...
```

### 7.3) H3: Quality Gates

**Co:** Spusť lint + testy, oprav problémy.

**Jak (detailní instrukce):**
```bash
# 1. Lint (pokud nakonfigurován)
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint}
  LINT_EXIT=$?
  if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint"; fi
  if [ $LINT_EXIT -ne 0 ] && [ -n "{COMMANDS.lint_fix}" ]; then
    echo "Auto-fixing lint..."
    timeout 120 {COMMANDS.lint_fix}
    timeout 120 {COMMANDS.lint}
    if [ $? -ne 0 ]; then echo "FAIL: lint still failing — fix manually"; fi
  fi
fi

# 2. Format check (pokud nakonfigurován)
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check}
  if [ $? -ne 0 ] && [ -n "{COMMANDS.format}" ]; then
    timeout 120 {COMMANDS.format}
    timeout 120 {COMMANDS.format_check}
  fi
fi

# 3. Tests (POVINNÉ)
timeout 300 {COMMANDS.test}
TEST_EXIT=$?
if [ $TEST_EXIT -eq 124 ]; then echo "TIMEOUT: tests exceeded 300s"; fi
if [ $TEST_EXIT -ne 0 ]; then echo "FAIL: tests not passing — fix before continuing"; fi
```

**Minimum:**
- Lint PASS (nebo SKIPPED pokud není nakonfigurován)
- Tests PASS (POVINNÉ — hotfix NESMÍ mergovat s failing testy)

**Anti-patterns:**
- Mergovat hotfix s failing testy „protože je to urgent" — NIKDY
- Ignorovat lint warnings — oprav nebo zaloguj

### 7.4) H4: Fast-track Review (self-review)

**Co:** Quick review hotfix diff PŘED merge — odchytí regrese.

**Jak (detailní instrukce):**
Hotfix neprocházi plným fabric-review cyklem (to by negoval fast-track). Místo toho proveď **self-review** na diff:

```bash
git diff "${MAIN_BRANCH}...HEAD" --stat
git diff "${MAIN_BRANCH}...HEAD"
```

Kontroluj tyto 4 dimenze (zkrácený review):
1. **R1 — Správnost:** Řeší kód skutečně požadavek? Nejsou tam edge cases?
2. **R2 — Error handling:** Každý nový try/except, každá síťová operace má fallback?
3. **R3 — Bezpečnost:** Žádné hardcoded secrets, žádný SQL injection, žádný path traversal?
4. **R4 — Testy:** Pokrývají testy hlavní scénáře? Nejsou to triviální pass-through testy?

**Minimum:**
- 4 dimenze zkontrolované
- Pokud R1/R2/R3 finding: oprav PŘED merge
- Pokud R4 finding (nedostatečné testy): doplň testy

**Anti-patterns:**
- Přeskočit review „protože je to hotfix" — tím se zavádějí regrese
- Review bez čtení diffu — to není review

### 7.5) H5: Commit + Merge

**Co:** Commitni na hotfix branch, squash merge do main.

**Jak (detailní instrukce):**
```bash
# 1. Commit na hotfix branch
git add -A
git commit -m "fix(${TASK_ID}): ${TITLE}"

# 2. Checkout main a merge
git checkout "${MAIN_BRANCH}"
git pull --ff-only || echo "WARN: pull failed"

# 3. Pre-merge divergence check
MERGE_BASE=$(git merge-base "${MAIN_BRANCH}" "${HOTFIX_BRANCH}")
MAIN_HEAD=$(git rev-parse "${MAIN_BRANCH}")
if [ "$MERGE_BASE" != "$MAIN_HEAD" ]; then
  echo "WARN: hotfix branch diverged, rebasing..."
  git checkout "${HOTFIX_BRANCH}"
  git rebase "${MAIN_BRANCH}"
  if [ $? -ne 0 ]; then
    git rebase --abort
    echo "FAIL: rebase conflict — manual resolution needed"
    # → intake item
    exit 1
  fi
  git checkout "${MAIN_BRANCH}"
fi

# 4. Squash merge
git merge --squash "${HOTFIX_BRANCH}"
if [ $? -ne 0 ]; then
  git merge --abort 2>/dev/null || git reset --merge 2>/dev/null
  echo "FAIL: merge conflict — manual resolution needed"
  exit 1
fi
git commit -m "fix(${TASK_ID}): ${TITLE} (hotfix)"

# 5. Post-merge gates (POVINNÉ)
timeout 300 {COMMANDS.test}
POST_MERGE_EXIT=$?
if [ $POST_MERGE_EXIT -ne 0 ]; then
  echo "FAIL: post-merge tests failing — reverting"
  git revert --no-edit HEAD
  # → intake item
  exit 1
fi

# 6. Cleanup
git branch -d "${HOTFIX_BRANCH}" 2>/dev/null || true
```

**Minimum:**
- Squash merge commit na main
- Post-merge tests PASS
- Hotfix branch smazaná

**Anti-patterns:**
- Merge bez post-merge test run — regrese na main
- `git push --force` — ZAKÁZÁNO
- `git reset --hard` na main — ZAKÁZÁNO (použij `git revert`)
- Nechat hotfix branch viset — smaž ji

### 7.6) H6: Backlog + Docs Update

**Co:** Aktualizuj backlog item na DONE, regeneruj index.

**Jak:**
```bash
# 1. Backlog update
SHA=$(git rev-parse HEAD)
python skills/fabric-init/tools/fabric.py backlog-set --id "${TASK_ID}" \
  --fields-json '{"status": "DONE", "merge_commit": "'"$SHA"'", "updated": "'"$(date +%Y-%m-%d)"'", "branch": null}'

# 2. Regeneruj backlog index
python skills/fabric-init/tools/fabric.py backlog-index

# 3. Docs update (pokud se týká)
# Aktualizuj relevantní docs/ soubory pokud hotfix mění veřejné chování
# Přidej changelog záznam pokud existuje CHANGELOG.md
```

**Minimum:**
- Backlog item má `status: DONE` a `merge_commit`
- Backlog index regenerován

**Anti-patterns (zakázáno):**
- Nastavit `status: DONE` bez `merge_commit` — DONE bez evidence není DONE
- Nechat `branch:` vyplněné po merge — smaž (nastavit `null`), jinak příští sprint uvidí stale branch
- Zapomenout regenerovat backlog index — backlog.md bude nekonzistentní se soubory
- Přeskočit docs update když hotfix mění veřejné API — drift mezi kódem a dokumentací

### 7.7) H7: Report

**Co:** Hotfix report se souhrnem evidence.

**Šablona výstupu:**
```md
---
schema: fabric.report.v1
kind: hotfix
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
task_id: "{TASK_ID}"
effort: "{XS|S}"
merge_commit: "{SHA}"
---

# Hotfix Report — {YYYY-MM-DD}

## Souhrn
{1–3 věty co hotfix udělal}

## Evidence
| Gate | Výsledek |
|------|----------|
| Lint | {PASS/FAIL/SKIPPED} |
| Format | {PASS/FAIL/SKIPPED} |
| Tests (pre-merge) | {PASS/FAIL} |
| Tests (post-merge) | {PASS/FAIL} |
| Self-review | {4/4 dimenze OK} |

## Změněné soubory
{git diff --stat output}

## Backlog
- ID: {TASK_ID}
- Status: DONE
- Merge commit: {SHA}

## Warnings
{Seznam nebo "žádné"}
```

---

## §8 — Quality Gates

### Gate 1: Lint
```bash
timeout 120 {COMMANDS.lint}
```
- PASS: exit 0
- FAIL: auto-fix → `{COMMANDS.lint_fix}` → retry 1×
- Timeout (124): WARN + intake item

### Gate 2: Format Check
```bash
timeout 120 {COMMANDS.format_check}
```
- PASS: exit 0
- FAIL: auto-fix → `{COMMANDS.format}` → retry 1×

### Gate 3: Tests (pre-merge)
```bash
timeout 300 {COMMANDS.test}
```
- PASS: exit 0 → pokračuj na merge
- FAIL: oprav a opakuj (NESMÍ mergovat s failing testy)
- Timeout (124): WARN + intake item

### Gate 4: Tests (post-merge)
```bash
timeout 300 {COMMANDS.test}
```
- PASS: exit 0 → hotfix DONE
- FAIL: `git revert --no-edit HEAD` + intake item

---

## §9 — Report

Viz §7.7 výše. Report path: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md`

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md`
- [ ] Backlog item existuje a má `status: DONE`
- [ ] Merge commit existuje na main: `git log --oneline -1 | grep "${TASK_ID}"`

### Quality checks
- [ ] Post-merge tests PASS
- [ ] Hotfix branch smazaná (ne na lokálu, ne na remote)
- [ ] Backlog index regenerován
- [ ] Report má schema frontmatter se status
- [ ] Minimálně 3 testy byly napsány/aktualizovány (happy/edge/error)
- [ ] Self-review proběhl na 4 dimenze (R1–R4)

### Invarianty
- [ ] Hotfix nezměnil `state.md` (phase/step/sprint) — jen wip_item/wip_branch
- [ ] Protocol log obsahuje START i END záznam
- [ ] Žádný `git push --force` nebyl proveden
- [ ] Working tree je čistý po dokončení

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
# Zařazení v lifecycle
phase: utility
step: hotfix

# Oprávnění
may_modify_state: false        # hotfix nesmí měnit phase/step/sprint
may_modify_backlog: true       # vytváří/aktualizuje backlog items
may_modify_code: true          # implementuje kód + testy
may_create_intake: true        # při failures

# Pořadí v pipeline
depends_on: [fabric-init]      # jen init — hotfix obchází sprint planning
feeds_into: [fabric-check]     # po hotfix je vhodné spustit check
```

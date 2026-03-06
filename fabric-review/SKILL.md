---
name: fabric-review
description: "Perform automated code review for the current WIP task across 9 dimensions (R1–R9). Uses config COMMANDS.lint + COMMANDS.format_check as objective gates, then performs a structured diff review including process-chain validation. Writes a review report, updates backlog item review_report, and creates intake items for systemic improvements."
---

# REVIEW — Code review (R1–R9) + verdikt

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

## Příklad vyplněného review reportu (všechny R1-R9 dimenze)

```markdown
---
title: "Review Report - T-101 (Add Pydantic Validation)"
version: "1.0"
date: "2026-03-10"
wip_item: "T-101"
wip_branch: "feature/pydantic-validation"
schema: "fabric.report.v1"
verdict: "CLEAN"
---

## Executive Summary

**Verdict:** CLEAN ✓

T-101 implementation is production-ready. All gates pass. R1-R9 review complete. No CRITICAL findings.

| Dimension | Score | Status |
|-----------|-------|--------|
| R1 Correctness | 95/100 | PASS |
| R2 Security | 100/100 | PASS |
| R3 Performance | 90/100 | PASS |
| R4 Reliability | 92/100 | PASS |
| R5 Testability | 95/100 | PASS |
| R6 Maintainability | 88/100 | PASS |
| R7 Documentation | 85/100 | MEDIUM findings (cosmetic) |
| R8 Compliance | 100/100 | PASS |
| R9 Process Chain | N/A | SKIPPED (process-map.md not present) |

## Gate Results

```
✓ PASS: Linting (ruff check)
✓ PASS: Format check (ruff format --check)
✓ PASS: Type hints (mypy)
✓ PASS: Tests (87 passed, 0 failed)
```

## R1 Correctness (95/100)

**Findings:** 1 minor

| ID | Issue | Severity | Line | Recommendation |
|----|-------|----------|------|-----------------|
| R1-F1 | Off-by-one potential in string slicing (validate_email) | MEDIUM | capture.py:120 | Use `email.validator` library instead of regex |

**Analysis:**
- Logic correctly maps to AC: POST /capture/event validates all required fields ✓
- Edge cases handled: None, empty string, oversized payload, invalid JSON ✓
- Off-by-one boundaries correct except minor email validation regex ✓
- Nesting ≤3 levels ✓ (max 2 levels in validate_input)
- Cyclomatic complexity: 8 (threshold: ≤10) ✓
- No dead code ✓
- All magic numbers named (MAX_PAYLOAD_SIZE, MIN_REQUIRED_FIELDS) ✓

**Score:** 95/100 (1 finding reduces from perfect)

---

## R2 Security (100/100)

**Findings:** None

**Analysis:**
- ✓ ALL user inputs validated at entry point (Pydantic BaseModel)
- ✓ No eval(), exec(), pickle.loads()
- ✓ Secrets not in code/logs (checked via grep for "password\|secret\|token")
- ✓ No SQL—using ORM for all DB access
- ✓ No path traversal (no file operations in capture)
- ✓ Auth on /capture endpoint (@auth_required decorator applied)

**Score:** 100/100 (no findings; implementation is secure)

---

## R3 Performance (90/100)

**Findings:** 1 medium

| ID | Issue | Severity | Location | Impact |
|----|-------|----------|----------|--------|
| R3-F1 | List.append in loop (observation batch processing) | MEDIUM | triage.py:210-215 | O(n) but could hit memory with 10k+ items |

**Analysis:**
- ✓ Algorithms ≤O(n log n) for hot paths (capture, triage) ✓
- ✓ No N+1 queries (using batch insert for observations)
- ✓ I/O operations paginated (recall returns top-10, not all)
- ✓ Cache: repeated hash computations cached in memory (HashEmbedder)
- Potential: Memory unbounded in batch processing; add MAX_BATCH_SIZE check

**Score:** 90/100 (list append is functional but could have cap)

---

## R4 Reliability (92/100)

**Findings:** 1 medium

| ID | Issue | Severity | Code | Mitigation |
|----|-------|----------|------|-----------|
| R4-F1 | Missing timeout on Pydantic validation call | MEDIUM | capture.py:88 | Add explicit timeout parameter (30s default) |

**Analysis:**
- ✓ Try/except blocks on all I/O (observation store insert, log write)
- ✓ Specific exceptions: ValidationError, StorageError (not bare except:)
- ✓ Graceful degradation: if store fails, log warning and return 202 (async)
- ✓ Resource cleanup: context managers for file/connection handles
- Retry logic: exponential backoff with max_retries=3 ✓
- Error messages include context: "Failed to write observation for item={item_id}" ✓
- One medium: validation call should have timeout guard

**Score:** 92/100

---

## R5 Testability (95/100)

**Findings:** 0

**Analysis:**
- ✓ Tests cover ALL AC (12 test cases for 12 AC items, 1:1 mapping)
- ✓ ≥2 assertions per test (avg 2.1 assertions per test)
- ✓ Edge case tests: empty payload, null fields, oversized input
- ✓ Error path tests: ValidationError raised for invalid JSON (pytest.raises)
- ✓ Test isolation: no global state, pytest fixtures used correctly
- ✓ Mock boundaries: mocking only external storage, not internal models
- ✓ No hardcoded sleep() or time-dependent tests

**Score:** 95/100 (one minor: coverage could be 1-2% higher for corner cases)

---

## R6 Maintainability (88/100)

**Findings:** 2 medium (cosmetic)

| ID | Issue | Severity | Code | Recommendation |
|----|-------|----------|------|-----------------|
| R6-F1 | Function name clarity | MEDIUM | capture.py:75 | Rename validate_input → validate_capture_payload (more specific) |
| R6-F2 | Module length | MEDIUM | capture.py:250 LOC | Consider splitting into validation + handler submodules |

**Analysis:**
- ✓ Naming: Functions follow {verb}_{noun} (validate_input, extract_observation, store_event)
- ✓ Classes: CaptureService, HashEmbedder follow {Noun}{Role}
- ✓ Function size: All ≤50 LOC (largest: 48 LOC)
- ✓ Single Responsibility: validate_input only validates, doesn't store
- ✓ DRY: No copy-paste code detected (≥3 line dedup check passed)
- ✓ Import ordering: stdlib, 3rd-party (pydantic, fastapi), local (llmem.*)

**Score:** 88/100 (naming clarity + module organization minor issues)

---

## R7 Documentation (85/100)

**Findings:** 2 medium (docs)

| ID | Issue | Severity | Code | Action |
|----|-------|----------|------|--------|
| R7-F1 | Missing docstring on validate_payload | MEDIUM | capture.py:75 | Add 1-2 line docstring: """Validate capture payload against schema.""" |
| R7-F2 | CHANGELOG not updated | MEDIUM | CHANGELOG.md | Add: "- Add Pydantic validation to /capture endpoint (T-101)" |

**Analysis:**
- ✓ Public functions have docstrings (CaptureService, extract_observation)
- ✓ Complex logic commented (heuristic matching logic in triage)
- ✗ CHANGELOG missing entry for T-101 changes
- ✓ API specs updated in docs/api.md
- ✓ No ADR required (validation is standard pattern)

**Score:** 85/100 (docstring + changelog gaps)

---

## R8 Compliance (100/100)

**ADR & Spec Audit:**

Accepted ADRs checked:
- D0001 (secrets-policy): ✓ No secrets in validate_input code path
- D0002 (ids-and-idempotency): ✓ Observations include idempotency_key
- D0003 (event-sourcing): ✓ Events logged to JSONL before processing

Active Specs checked:
- LLMEM_DATA_MODEL_V1: ✓ ObservationEvent schema respected
- LLMEM_API_V1: ✓ /capture endpoint request/response schema correct

**Findings:** None. Implementation compliant with all accepted ADR and active specs.

**Score:** 100/100

---

## R9 Process Chain Validation (SKIPPED)

**Status:** SKIPPED — process-map.md does not exist in {WORK_ROOT}/fabric/processes/

(Fail-open: R9 check skipped; not applicable at early phase)

---

## Summary of Findings

| Severity | Count | Details |
|----------|-------|---------|
| CRITICAL | 0 | ✓ None |
| HIGH | 0 | ✓ None |
| MEDIUM | 5 | R1-F1, R3-F1, R4-F1, R6-F1, R6-F2, R7-F1, R7-F2 (7 total) |
| LOW | 0 | ✓ None |

**Verdict Justification:**
- 0 CRITICAL findings → No blocker
- 0 HIGH findings → No merge blocker
- 7 MEDIUM findings → Cosmetic/process improvements, not code quality blockers
- All tests PASS
- All gates PASS

→ **CLEAN verdict warranted**

## Next Steps

Optional improvements (non-blocking):
1. Add email validation library (R1-F1)
2. Add MAX_BATCH_SIZE limit (R3-F1)
3. Add timeout to validation (R4-F1)
4. Improve function naming (R6-F1)
5. Update CHANGELOG (R7-F2)

Recommended for future sprint: Create intake item for systematic improvements to email validation across codebase.
```

---

## Preconditions

- `state.wip_item` a `state.wip_branch` musí existovat
- `COMMANDS.lint` a `COMMANDS.format_check` nesmí být `TBD` *(prázdné = vypnuto)*
- test report pro `wip_item` musí existovat (temporal dependency: test → review)

Pokud chybí → vytvoř intake item `intake/review-missing-wip-or-commands.md` a FAIL.

### File & branch existence checks (povinné)

```bash
WIP_ITEM=$(python skills/fabric-init/tools/fabric.py state-get --field wip_item 2>/dev/null)
WIP_BRANCH=$(python skills/fabric-init/tools/fabric.py state-get --field wip_branch 2>/dev/null)

# 1. backlog soubor musí existovat
if [ ! -f "{WORK_ROOT}/backlog/${WIP_ITEM}.md" ]; then
  echo "STOP: backlog file missing for wip_item=$WIP_ITEM"
  python skills/fabric-init/tools/fabric.py intake-new --source "review" --slug "missing-backlog-file" \
    --title "Backlog file not found: backlog/${WIP_ITEM}.md"
  exit 1
fi

# 2. branch musí existovat v git
if ! git rev-parse --verify "$WIP_BRANCH" >/dev/null 2>&1; then
  echo "STOP: branch $WIP_BRANCH does not exist in git"
  python skills/fabric-init/tools/fabric.py intake-new --source "review" --slug "missing-branch" \
    --title "Git branch not found: $WIP_BRANCH"
  exit 1
fi

# 3. test report musí existovat (temporal: implement→test→review)
LATEST_TEST_REPORT=$(ls -t {WORK_ROOT}/reports/test-${WIP_ITEM}-*.md 2>/dev/null | head -1)
if [ -z "$LATEST_TEST_REPORT" ]; then
  echo "STOP: no test report found for wip_item=$WIP_ITEM — run fabric-test first"
  python skills/fabric-init/tools/fabric.py intake-new --source "review" --slug "missing-test-report" \
    --title "Test report missing for ${WIP_ITEM} — temporal dependency violated"
  exit 1
fi

# Validate test report existence and format
LATEST_TEST_REPORT=$(ls -t "{WORK_ROOT}/reports/test-${WIP_ITEM}-"*.md 2>/dev/null | head -1)
if [ -z "$LATEST_TEST_REPORT" ]; then
  echo "STOP: no test report found for ${WIP_ITEM} — run fabric-test first"
  exit 1
fi

# --- Validate test report format (P1 fix) ---
if [ -n "$LATEST_TEST_REPORT" ]; then
  # Check required sections exist
  if ! grep -q "^## Summary\|^## Souhrn" "$LATEST_TEST_REPORT"; then
    echo "WARN: test report missing Summary section"
  fi
  if ! grep -q "^status:" "$LATEST_TEST_REPORT"; then
    echo "WARN: test report missing status in frontmatter"
  fi
  if ! grep -q "^schema: fabric.report" "$LATEST_TEST_REPORT"; then
    echo "WARN: test report missing schema declaration"
  fi
fi
```

### Rework counter check

Načti `rework_count` z backlog item metadata (persisted counter, nastavuje fabric-loop):
```bash
# Preferuj persisted counter z backlog item frontmatter
REWORK_COUNT=$(grep 'rework_count:' "{WORK_ROOT}/backlog/${wip_item}.md" | awk '{print $2}')
REWORK_COUNT=${REWORK_COUNT:-0}
# Numeric validation (viz config.md VALIDATION.counter_validation)
if ! echo "$REWORK_COUNT" | grep -qE '^[0-9]+$'; then REWORK_COUNT=0; echo "WARN: non-numeric rework_count, reset to 0"; fi
# Fallback: počet existujících review reportů (méně spolehlivé — soubory mohou být smazány/archivovány)
if [ "$REWORK_COUNT" -eq 0 ]; then
  REWORK_COUNT=$(ls "{WORK_ROOT}/reports/review-${wip_item}-"*.md 2>/dev/null | wc -l)
fi
```

Pokud REWORK_COUNT >= `SPRINT.max_rework_iters` (default 3):
- Verdikt = `REDESIGN` (ne REWORK — task vyžaduje zásadní změnu přístupu)
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

### State Validation (K1: State Machine)

```bash
# State validation — check current phase is compatible with this skill
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="implementation"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-review. Expected: $EXPECTED_PHASES"
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
# validate_path "$BRANCH_NAME"
# validate_path "$REVIEW_PATH"
```

### 1) Objective gates (must run)

Na branchi:

```bash
git checkout "${wip_branch}"

# lint (optional) — s timeoutem, aby review nikdy nehangoval
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  timeout 120 {COMMANDS.lint}
  LINT_EXIT=$?
  if [ $LINT_EXIT -eq 124 ]; then echo "TIMEOUT: lint exceeded 120s"; LINT_RESULT="TIMEOUT"; elif [ $LINT_EXIT -ne 0 ]; then LINT_RESULT="FAIL"; else LINT_RESULT="PASS"; fi
else echo "lint: SKIPPED"; LINT_RESULT="SKIPPED"; fi

# format check (optional) — s timeoutem
if [ -n "{COMMANDS.format_check}" ] && [ "{COMMANDS.format_check}" != "TBD" ]; then
  timeout 120 {COMMANDS.format_check}
  FMT_EXIT=$?
  if [ $FMT_EXIT -eq 124 ]; then echo "TIMEOUT: format_check exceeded 120s"; FMT_RESULT="TIMEOUT"; elif [ $FMT_EXIT -ne 0 ]; then FMT_RESULT="FAIL"; else FMT_RESULT="PASS"; fi
else echo "format_check: SKIPPED"; FMT_RESULT="SKIPPED"; fi
```

> **Timeout (exit 124) v review:** Pokud lint/format_check timeout v review, hodnoť gate jako FAIL (ne REWORK — TIMEOUT je infrastrukturní problém). Vytvoř intake item `intake/review-gate-timeout-{wip_item}.md` a v reportu označ gate jako `TIMEOUT` (odlišně od FAIL).

**Design note:** Review **záměrně nespouští auto-fix** (lint_fix/format). Review je read-only pozorovatel — měří stav kódu, neopravuje ho. Auto-fix je odpovědnost implement (na branchi) a close (na main). Pokud lint_fix/format příkazy chybí v configu a gate selže v task souborech → review vrátí REWORK; implement musí opravit ručně nebo vytvořit intake item pro missing lint_fix command.

Pokud gate failne, **rozliš zdroj chyby**:

1. Zjisti, zda lint/format chyby jsou v souborech **změněných tímto taskem** (diff):
   ```bash
   git diff --name-only {main_branch}...{wip_branch} > /tmp/task-files.txt
   ```
   Porovnej chybové soubory z lint/format výstupu s task-files.

2. **Chyba v diff (task soubory)** → Verdikt = `REWORK`. Do reportu napiš „Gate failed in task files” + konkrétní soubory a chyby.

3. **Chyba jen v pre-existing souborech (mimo diff)** → Verdikt = **CLEAN** (neblokuj task kvůli cizím chybám). Do reportu zapiš gate jako `PASS (pre-existing issues ignored)` a vytvoř intake item `intake/review-pre-existing-lint-{wip_item}.md` se seznamem pre-existing chyb.

4. **Chyba v obou** → Verdikt = `REWORK` (task soubory musí být čisté). Do reportu rozliš task vs pre-existing findings.

Pokud verdikt = REWORK kvůli gate fail:
- STOP (neprováděj hluboký review, dokud gates v task souborech nejsou čisté)

### 2) Zjisti změny (diff)

```bash
timeout 60 git fetch --all --prune || echo "WARN: git fetch failed/timeout"
git diff --stat {main_branch}...{wip_branch}
git diff {main_branch}...{wip_branch}
```

Vypiš seznam změněných souborů (code/test/docs).

### 3) Review rámec (R1–R8)

Pro každou dimenzi napiš:
- skóre 0–5
- konkrétní nálezy (1–N)
- doporučení nebo požadavek na rework

Dimenze s konkrétními checklisty (POVINNÉ — projdi KAŽDÝ bod):

**R1 Correctness** — správnost a edge cases:
- [ ] Logika odpovídá AC (mapuj 1:1)
- [ ] Edge cases ošetřeny: None/empty/0/negative/max_int/unicode
- [ ] Off-by-one v loops a ranges (`<` vs `<=`, indexování)
- [ ] Nesting ≤3 úrovní (jinak extrahuj funkci)
- [ ] Cyclomatic complexity ≤10 per funkce (pokud >10 → finding)
- [ ] Žádný dead code (unreachable branches, unused imports/vars)
- [ ] Magic numbers nahrazeny konstantami s popisným jménem

**R2 Security** — vstupní validace, secrets, autorizace:
- [ ] VŠECHNY user vstupy validovány na entry point (type, range, format)
- [ ] Žádný `eval()`, `exec()`, `subprocess(shell=True)`, `pickle.loads()` bez sanitizace
- [ ] Secrets/credentials nejsou v kódu, logách, ani chybových zprávách
- [ ] SQL/NoSQL queries parametrizované (ne string concatenation)
- [ ] Path traversal prevence pro dynamické cesty (`os.path.realpath` + prefix check)
- [ ] Auth/authz check na KAŽDÉM novém endpoint/handleru

**R3 Performance** — složitost, I/O, hot paths:
- [ ] Algoritmus ≤O(n log n) pro hot paths (O(n²) = finding)
- [ ] Žádné N+1 queries (databáze/API v loopu)
- [ ] I/O operace mají limit/pagination (ne unbounded `read()` nebo `fetchall()`)
- [ ] Cache hit ratio (pokud applicable): opakované výpočty cachované?
- [ ] Memory: žádné unbounded collections (list.append v loop bez limitu)

**R4 Reliability** — error handling, retries, timeouts:
- [ ] KAŽDÝ I/O call má `try/except {SpecificError}` (ne bare `except:`)
- [ ] KAŽDÝ I/O call má timeout (explicitní parametr nebo wrapper)
- [ ] Graceful degradation: pokud dependency selže, systém funguje (fail-open pro LLMem)
- [ ] Resource cleanup: `with` statement pro file/connection handles (ne manual close)
- [ ] Retry logika má backoff + max_retries (ne infinite retry)
- [ ] Error zprávy obsahují kontext: co selhalo, s jakým vstupem, proč

**R5 Testability** — kvalita testů:
- [ ] Testy pokrývají VŠECHNY AC (mapuj 1:1)
- [ ] ≥2 assertions per test (ne jen `assert True` nebo single assert)
- [ ] Edge case testy existují pro core logic
- [ ] Error path testy: `pytest.raises` pro expected exceptions
- [ ] Test isolation: žádné sdílené mutable state mezi testy
- [ ] Mock boundaries: mock jen external deps (ne internal modules)
- [ ] Flaky test detection: žádný `time.sleep()` v testech bez `@pytest.mark.timeout`

**R6 Maintainability** — čitelnost, naming, modularita:
- [ ] Funkce: `{verb}_{noun}` naming (describe_action, calculate_score, validate_input)
- [ ] Třídy: `{Noun}{Role}` naming (CaptureService, HashEmbedder, InMemoryBackend)
- [ ] Funkce ≤50 LOC (>50 = finding, doporuč split)
- [ ] Single Responsibility: každá funkce dělá JEDNU věc
- [ ] DRY: žádný copy-paste kód (≥3 řádky duplicitní → extrahuj)
- [ ] Import ordering: stdlib → third-party → local (consistent)

**R7 Documentation** — docs, komentáře, ADR:
- [ ] KAŽDÁ nová public funkce/třída má docstring (≥1 věta)
- [ ] Complex logic má inline komentář PROČ (ne CO — kód říká co)
- [ ] README/CHANGELOG aktualizován pokud user-facing change
- [ ] API changes → aktualizuj specs (nebo vytvoř intake item)
- [ ] Arch decisions → existuje ADR nebo je v analýze zdůvodnění

**R8 Compliance** — dodržení config konvencí + **accepted ADR** + **active specs** (porušení = CRITICAL):
- [ ] Načti `{WORK_ROOT}/decisions/INDEX.md` — identifikuj všechny `accepted` ADR
- [ ] Načti `{WORK_ROOT}/specs/INDEX.md` — identifikuj `active` a `draft` specs
- [ ] Ověř, že diff neodporuje žádné accepted ADR či active spec
- [ ] Pro každý changed file: zkontroluj proti GOVERNANCE registry z `{WORK_ROOT}/config.md`
- [ ] Porušení accepted ADR/active spec = CRITICAL finding

**R9 Process Chain Validation** — detekce changes v process-contract modules:
- [ ] Pokud existuje `{WORK_ROOT}/fabric/processes/process-map.md`: načti jej
- [ ] Extrahuj seznam všech procesů s jejich `contract_modules`
- [ ] Pro KAŽDÝ changed file v diffu: srovnej s `contract_modules` z každého procesu
- [ ] Pokud je changed file v `contract_modules` procesu P: ALERT se jménem procesu
- [ ] Ověř, že proces-chain unit testy (test_P) z `{WORK_ROOT}/tests/test_processes/` projdou
- [ ] Pokud process-map.md NEEXISTUJE: INFO (fail-open, skip check)
- [ ] Pokud proces-testy neexistují/failují: HIGH finding


#### R8 Compliance — konkrétně (povinné)

1) Otevři `{WORK_ROOT}/decisions/INDEX.md` a identifikuj **všechny `accepted` ADR** (ne jen ty zmíněné v analýze — analýza může opomenout závislost).
2) Otevři `{WORK_ROOT}/specs/INDEX.md` a identifikuj **`active` specs** a **`draft` specs** (draft specs nejsou enforced jako CRITICAL, ale porušení je HIGH finding).
3) Pokud diff zavádí změnu, která **odporuje accepted ADR** nebo **porušuje active spec**:
   - zapiš finding severity **CRITICAL**
   - v reportu cituj konkrétní ADR/SPEC + konkrétní změnu v diffu
   - doporuč: buď upravit implementaci, nebo vytvořit nový ADR/SPEC (nepřepisuj accepted bez procesu)
4) **Kontraktově-citlivé soubory** — načti `GOVERNANCE.decisions.registry` a `GOVERNANCE.specs.registry` z `{WORK_ROOT}/config.md` a pro KAŽDÝ changed file v diffu zkontroluj, zda spadá do `contract_modules` některého ADR/spec:

   **Postup (deterministický):**
   ```bash
   # Získej changed files
   git diff --name-only {main_branch}...{wip_branch} > /tmp/changed-files.txt
   # Pro každý soubor zkontroluj proti GOVERNANCE registru v config.md
   # Pokud soubor matchuje contract_modules některého ADR → ověř ADR compliance
   # Pokud soubor matchuje contract_modules některého spec → ověř spec compliance
   ```

   **Mapování (source of truth: `{WORK_ROOT}/config.md` GOVERNANCE registr — P2 fix #24):**
   Use variables `{WORK_ROOT}` and `{CODE_ROOT}` instead of hardcoded paths. The snapshot below is for reference only; always load the authoritative registry from config.md:
   - `{CODE_ROOT}/recall/injection.py`, `{CODE_ROOT}/recall/pipeline.py` → D0004 (injection-contract) + LLMEM_INJECTION_FORMAT_V1 (active): preamble warning musí zůstat, XML struktura musí odpovídat spec, CDATA wrapping zachován
   - `{CODE_ROOT}/storage/backends/` → LLMEM_QDRANT_SCHEMA_V1 (draft): collection schema, vector params, payload fields
   - `{CODE_ROOT}/storage/log_jsonl.py` → D0003 (event-sourcing-and-rebuild): JSONL log je immutable (append-only), rebuild musí být možný z logu
   - `{CODE_ROOT}/triage/heuristics.py`, `{CODE_ROOT}/triage/patterns.py` → D0001 (secrets-policy) + LLMEM_TRIAGE_HEURISTICS_V1 (draft): masking rules, PII hashing
   - `{CODE_ROOT}/models.py` → D0002 (ids-and-idempotency) + LLMEM_DATA_MODEL_V1 (draft): UUIDv7 z content_hash, idempotency_key musí zůstat
   - `{CODE_ROOT}/api/` → LLMEM_API_V1 (draft): endpoint paths, request/response schema
   - `{CODE_ROOT}/recall/scoring.py` → LLMEM_RECALL_PIPELINE_V1 (draft): scoring formula, budget algorithm

   > **Kanonický zdroj:** `{WORK_ROOT}/config.md` GOVERNANCE registr je JEDINÝ source of truth. Tento seznam je odvozený snapshot pro rychlou referenci. Při review POVINNĚ načti aktuální registr z config.md a automaticky ověř drift:
   > ```bash
   > # Automatický governance drift check (POVINNÉ na začátku R8)
   > # Primární: deterministický tool
   > python skills/fabric-init/tools/fabric.py governance-check --verify-snapshot
   > GOV_EXIT=$?
   > if [ $GOV_EXIT -eq 127 ]; then
   >   # Tool neexistuje — fallback na manuální grep
   >   echo "WARN: governance-check tool not found, using manual grep"
   >   grep -A 3 'contract_modules:' {WORK_ROOT}/config.md > /tmp/gov-config.txt
   >   # Manuální porovnání s R8 snapshot — pokud se liší, vytvoř intake
   > elif [ $GOV_EXIT -ne 0 ]; then
   >   echo "WARN: governance snapshot drift detected"
   >   python skills/fabric-init/tools/fabric.py intake-new \
   >     --source "review" --slug "governance-drift" \
   >     --title "R8 snapshot differs from config.md GOVERNANCE registry"
   > fi
   > # Výsledek: Pokračuj VŽDY s daty z config.md (ne snapshot)
   > ```
   > Tento check je **mandatory** — přeskočení je skill violation.

   - Porušení `accepted` ADR nebo `active` spec bez odpovídajícího supersede = **CRITICAL**
   - Porušení `draft` spec = **HIGH** (severity dle `GOVERNANCE.specs.draft_enforcement` v config.md)

### 3b) R9 Process Chain Validation (mandatory if process-map.md exists)

```bash
# Zjisti changed files
git diff --name-only {main_branch}...{wip_branch} > /tmp/changed-files.txt

PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"

if [ ! -f "$PROCESS_MAP" ]; then
  echo "INFO: process-map.md not found — R9 check skipped (fail-open)"
  R9_STATUS="SKIPPED"
else
  R9_STATUS="PASS"
  R9_ALERTS=""

  # Pro každý changed file, zkontroluj proces-mapu
  while IFS= read -r changed_file; do
    [ -z "$changed_file" ] && continue

    # Extrahuj všechny procesy a jejich contract_modules z process-map.md
    # Format: assuming YAML-like nebo markdown list — grep pro "[contract_modules:" a následující řádky
    PROCESSES=$(grep -B2 "contract_modules:" "$PROCESS_MAP" | grep "^[a-zA-Z_-]*:" | sed 's/:$//')

    for process_name in $PROCESSES; do
      # Načti contract_modules seznam pro daný proces
      #假定struktura:
      #   process_name:
      #     contract_modules:
      #       - "path/to/module1.py"
      #       - "path/to/module2.py"

      CONTRACT_MODULES=$(awk "/^$process_name:/,/^[a-zA-Z]/ {print}" "$PROCESS_MAP" \
        | grep -A 100 "contract_modules:" \
        | grep '^\s*- "' \
        | sed 's/^\s*- "//' | sed 's/".*//')

      # Srovnání: je changed_file v CONTRACT_MODULES?
      if echo "$CONTRACT_MODULES" | grep -qF "$changed_file"; then
        echo "ALERT: Changed file '$changed_file' is in process '$process_name' contract"
        R9_ALERTS="${R9_ALERTS}
- **ALERT:** File \`$changed_file\` is a \`contract_module\` in process **$process_name** — verify process-chain tests pass"
        R9_STATUS="ALERT"

        # Ověř, že proces-chain testy existují a projdou
        PROCESS_TEST="{WORK_ROOT}/tests/test_processes/test_${process_name}.py"
        if [ -f "$PROCESS_TEST" ]; then
          echo "Running process-chain test for $process_name..."
          timeout 60 python -m pytest "$PROCESS_TEST" -v 2>&1 | head -20
          TEST_EXIT=$?
          if [ $TEST_EXIT -ne 0 ] && [ $TEST_EXIT -ne 124 ]; then
            echo "CRITICAL: Process-chain test FAILED: $PROCESS_TEST"
            R9_STATUS="CRITICAL"
          fi
        else
          echo "INFO: Process-chain test not found: $PROCESS_TEST (skipped)"
        fi
      fi
    done
  done < /tmp/changed-files.txt

  if [ "$R9_STATUS" = "ALERT" ] || [ "$R9_STATUS" = "CRITICAL" ]; then
    echo "R9 Finding: $R9_STATUS"
    echo "$R9_ALERTS"
  fi
fi
```

> **R9 Fail-open design:** Pokud `process-map.md` neexistuje (early sprints bez procesů), R9 se skipne s INFO statusem a neblokuje review. Jakmile procesy existují, kontrola se spustí automaticky.

> **Process contract violation severity:** Pokud changed file je v `contract_modules` procesu, je to **HIGH** finding (minimum). Pokud proces-chain testy failují, eskaluj na **CRITICAL**.


### 4) Verdikt (jednoznačně)

**Důležité:** Verdikt musí být parsovatelný. Do reportu napiš řádek přesně ve tvaru:
- `Verdict: CLEAN`
- nebo `Verdict: REWORK`
- nebo `Verdict: REDESIGN`


- `CLEAN` pokud:
  - gates PASS (nebo pre-existing only)
  - žádné CRITICAL findings
  - test evidence existuje a je PASS (nebo je v reportu vysvětleno proč ne)

- `REWORK` pokud:
  - gates fail v task souborech
  - nebo existuje alespoň 1 CRITICAL finding, který je opravitelný v rámci současného přístupu

- `REDESIGN` pokud:
  - CRITICAL finding vyžaduje zásadní změnu přístupu (jiná architektura, nový ADR/spec)
  - nebo task porušuje accepted ADR / active spec a nelze to vyřešit drobnou úpravou
  - nebo 3× REWORK na stejném tasku nepomohl (max_rework_iters dosažen — viz rework counter check)

### Finding severity taxonomy

Každý individual finding musí mít severity:

- **CRITICAL** — blokuje merge: security issue, data corruption risk, testy nevalidují AC, breaking change bez docs, ambiguous behavior, porušení ADR/spec
- **HIGH** — měl by se opravit před merge: chybějící error handling pro hlavní flow, netestovaný edge case pro core logic, performance regrese
- **MEDIUM** — doporučeno opravit, neblokuje: naming, minor refactor, chybějící doc komentář, neoptimální ale funkční řešení
- **LOW** — nice-to-have: stylistické, preference, minor improvements

Verdikt pravidla:
- ≥1 CRITICAL (opravitelný) → `REWORK`
- ≥1 CRITICAL (vyžaduje redesign) → `REDESIGN`
- ≥3 HIGH bez CRITICAL → `REWORK` (akumulace)
- Jen MEDIUM/LOW → `CLEAN` (findings zapiš do reportu jako doporučení)

**Severity→Score numerické mapování (pro konzistentní prioritizaci intake items):**

| Severity | Score range | Intake raw_priority | Příklad |
|----------|-----------|-------------------|---------|
| CRITICAL | 9.0–10.0 | 9–10 | SQL injection, data corruption, untested AC |
| HIGH | 7.0–8.9 | 7–8 | Missing error handling for core flow, performance regression |
| MEDIUM | 5.0–6.9 | 5–6 | Bad naming, minor refactor, missing doc comment |
| LOW | 3.0–4.9 | 3–4 | Stylistic, preference, minor improvements |

Score formule per finding: `base_severity + impact_modifier + fixability_modifier`
- `base_severity`: CRITICAL=9, HIGH=7, MEDIUM=5, LOW=3
- `impact_modifier`: +1 pokud affects >3 files, +0.5 pokud affects public API
- `fixability_modifier`: -0.5 pokud quick fix (<5 min), +0.5 pokud requires redesign

Zapiš score ke každému finding v review reportu: `| R2 | Missing validation | HIGH (7.5) | ... |`

---

### **Numeric Scoring Anchors per Dimension (WQ10 fix — enforceable standards)**

Pro konzistentní, veřejné, a měřitelné review scoring, použij TYTO specifické kritéria:

**R1 Correctness (0–100 % per finding):**
- **100 %** = Zero logic bugs observed. All edge cases handled: None/empty/0/negative/max_int/unicode. Off-by-one boundaries correct. Nesting ≤3. Complexity ≤10. No dead code. Constants named.
- **80 %** = Minor edge cases partially handled. Off-by-one potential in 1 boundary. Nesting 4 levels (should be 3). Complexity 10–15. One unused variable.
- **50 %** = Significant logic bug exists (e.g., inverted condition, missing range check, N+1 access pattern). AC not fully met.
- **0 %** = Logic fundamentally broken. AC fail. Crash risk.
**Finding format:** `| R1 | Edge case not handled: None input at line 45 | MEDIUM | R1 score drops from 100 to 80 |`

**R2 Security (0–100 % per finding):**
- **100 %** = All inputs validated at entry (type, range, format). No eval/exec/pickle. Secrets absent from code + logs + errors. Queries parametrized. Path traversal protected. Auth on every endpoint.
- **80 %** = 1 minor gap: missing validation on one optional field, or one log might leak PII.
- **50 %** = Unvalidated user input reaches code. No SQL param guards. Secrets in comments. Missing auth on 1 endpoint.
- **0 %** = Critical vulns: code injection, credential exposure, no auth.
**Finding format:** `| R2 | Missing input validation on 'instance_id' (SQL injection risk) | CRITICAL | R2 score 100→50 |`

**R3 Performance (0–100 % per finding):**
- **100 %** = Algorithms ≤O(n log n). No N+1 queries. Unbounded I/O limited (pagination, streaming). Cache hits optimized. Memory bounded.
- **80 %** = One O(n²) loop on non-critical path. Or 1 potential N+1 in rare case.
- **50 %** = O(n²) on hot path. N+1 detected. Unbounded read() without limit.
- **0 %** = Triple loop O(n³). Infinite recursion. Memory leak.
**Finding format:** `| R3 | Nested loop O(n²) in dedup (line 150) | HIGH | R3 score 100→50 |`

**R4 Reliability (0–100 % per finding):**
- **100 %** = Every I/O call has specific try/except. Timeouts present. Graceful degradation (fail-open). Resources cleaned up (with statements). Retry with backoff + max_retries. Error messages contextual.
- **80 %** = Missing timeout on 1 I/O call. Or bare except: on 1 handler.
- **50 %** = Multiple I/O calls without error handling or timeout. Infinite retry loop. No graceful fallback.
- **0 %** = Crashes on any transient error. Resource leaks. Deadlock risk.
**Finding format:** `| R4 | Qdrant search has no timeout (could hang forever) | HIGH | R4 score 100→70 |`

**R5 Testability (0–100 % per finding):**
- **100 %** = All AC tested. ≥2 assertions per test. Edge cases covered. Error paths tested (pytest.raises). Isolated (no shared state). Mock boundaries correct (external deps only). No flaky tests.
- **80 %** = Missing 1 edge case test. Or 1 test has only 1 assertion.
- **50 %** = 1 AC untested. Tests use time.sleep. Shared state between tests.
- **0 %** = No tests for core logic. Flaky tests. Impossible to debug test failures.
**Finding format:** `| R5 | Error path for invalid score type untested | HIGH | R5 score 100→70 |`

**R6 Maintainability (0–100 % per finding):**
- **100 %** = Functions {verb}_{noun}. Classes {Noun}{Role}. Functions ≤50 LOC. Single responsibility. DRY (no copy-paste). Imports ordered (stdlib → third-party → local).
- **80 %** = Function 60 LOC (should be <50). Or 1 naming anomaly.
- **50 %** = Function >100 LOC (god function). Multiple responsibilities. Copy-paste code block (8 lines) appears 3 times.
- **0 %** = Function >200 LOC, unreadable. Massive duplication. Circular imports.
**Finding format:** `| R6 | capture() is 120 LOC (should split into _validate, _triage, _store) | MEDIUM | R6 score 100→70 |`

**R7 Documentation (0–100 % per finding):**
- **100 %** = Every public function has docstring (≥1 sentence + Args/Returns/Raises). Complex logic has PROCE comment (why, not what). README updated if user-facing. API changes in specs. ADR for arch decisions.
- **80 %** = Missing 1 docstring on private function. Or 1 complex block without comment.
- **50 %** = Missing docstrings on >2 functions. README/CHANGELOG stale. API change not in specs.
- **0 %** = No docstrings. Code completely unexplained. Impossible to use.
**Finding format:** `| R7 | Function combine_score() has no docstring | LOW | R7 score 100→90 |`

**R8 Compliance (0–100 % per finding):**
- **100 %** = Zero violations of accepted ADR or active spec. All changed files match governance registry contracts.
- **0 %** = Violates accepted ADR or active spec (supersede ADR required to fix).
**Finding format:** `| R8 | Violates D0001 (secrets masking required) — stores plaintext | CRITICAL | R8 score 100→0 (must redesign) |`

**R9 Process Chain (0–100 % per finding):**
- **100 %** = No changed files in contract_modules. Or if changed, process-chain tests all PASS.
- **50 %** = Changed file in contract_modules, process-chain test didn't run (missing test).
- **0 %** = Changed file in contract_modules, process-chain test FAILS (process broken).
**Finding format:** `| R9 | File triage/heuristics.py changed (contract_modules) but test_triage_and_recall.py FAILED | CRITICAL | R9 score 100→0 |`

**Per-dimension final scoring:** Average score across all findings in dimension.
- Dimension R1: findings [100, 80, 50] → avg 76.67 → Grade: "R1: 76/100 (MEDIUM)" → detail findings list

### Fix strategy per finding type — Standardized Format (WQ2, WQ3 fixes)

Když verdikt je REWORK, review report MUSÍ obsahovat per-finding konkrétní fix strategii v SJEDNOCENÉM formátu:

**Standardní sloupce (POVINNÉ pro VŠECHNY findings):**
```
| File:Line | Dimension | Severity | Finding | Fix | Confidence |
```

**KAŽDÝ finding MUSÍ obsahovat:**
- **(a) exact file:line** — kde je chyba (e.g. `src/llmem/models.py:45`)
- **(b) co je špatně** — konkrétní problém (ne vágní "oprav")
- **(c) jak to opravit** — explicitní kroky (ne "vylepši")
- **(d) estimated effort** — čas na opravu (e.g. "5 min" či "2 hours")

Pokud KTERÝKOLI z (a)-(d) chybí → finding je **INCOMPLETE** a musí se doplnit.

**Fix strategy table — per finding type:**

| Dim | Typ finding | Exact format | Example |
|-----|-------------|--------------|---------|
| R1 | Missing edge case handling | `src/llmem/recall/scoring.py:78` \| R1 \| HIGH \| Missing None check for score value \| Add guard: `if score is None: return 0.0` with test `test_scoring_none_input()` \| HIGH | `src/llmem/recall/scoring.py:78 \| R1 \| HIGH \| Missing None check before float() call \| Add `if score is None: return 0.0; return float(score)` + test case \| HIGH |
| R1 | Off-by-one / boundary | `src/llmem/storage/log_jsonl.py:102` \| R1 \| MEDIUM \| Loop range off-by-one (uses `<` but should use `<=`) \| Change `for i in range(n):` to `range(n+1)` if boundary-inclusive. Add test with n=0,1,max_int \| MEDIUM | For actual: `src/llmem/storage/log_jsonl.py:102 \| R1 \| MEDIUM \| Off-by-one in chunk size loop (line 102 processes n-1 instead of n items) \| Change `for i in range(len(items)-1):` to `range(len(items))` + add boundary test \| MEDIUM |
| R1 | Logic error | `src/llmem/triage/heuristics.py:45` \| R1 \| CRITICAL \| Inverted if condition (masks PII when should keep it) \| (a) Write failing test first: `test_pii_masking_should_mask_emails()` expecting mask output. (b) Flip condition `if not is_pii:` → `if is_pii:`. (c) Run test, confirm PASS. \| HIGH | For actual: `src/llmem/triage/heuristics.py:45 \| R1 \| CRITICAL \| Logic inverted: sensitivity marked as 'secret' when should be 'sensitive' \| (1) Write TDD test `test_sensitivity_detection_email_should_be_sensitive()` expecting 'sensitive'. (2) Fix line 45: `if matches_secret_pattern:` → `if matches_pii_pattern:` \| HIGH |
| R2 | Missing input validation | `src/llmem/api/routes/recall.py:15` \| R2 \| CRITICAL \| RecallQuery.query_text not validated for max length (DOS risk) \| Add Pydantic validator: `@field_validator('query_text') def validate_length(v): if len(v) > 10000: raise ValueError('max 10k chars')` \| HIGH | For actual: `src/llmem/api/routes/recall.py:15 \| R2 \| CRITICAL \| User input 'instance_id' not validated for format (SQL injection risk) \| Use Pydantic UUID validator or add regex check: `if not re.match(r'^[a-z0-9-]{36}$', instance_id):` raise ValueError() \| HIGH |
| R2 | Secret/credential exposure | `src/llmem/config.py:120` \| R2 \| CRITICAL \| Database password logged in error message \| Remove from log: change `log.error(f"DB error: {url}")` to `log.error(f"DB error: {mask_secrets(str(e))}")`. Use patterns.py detect_secrets(). \| HIGH | For actual: `src/llmem/config.py:120 \| R2 \| CRITICAL \| API key appears in debug logs (line prints full environ) \| Replace `print(environ)` with `{k: mask_secrets(v) for k, v in environ.items()}`. Add test: `test_config_no_secrets_in_logs()` \| HIGH |
| R2 | SQL/Command injection | `src/llmem/storage/backends/qdrant.py:200` \| R2 \| CRITICAL \| Collection name from user input not escaped \| Use parameterized Qdrant API (collection name is enum, not string). Pass as arg: `self.client.search(collection_name=safe_name)` not string interp. \| HIGH | For actual: `src/llmem/storage/backends/qdrant.py:200 \| R2 \| CRITICAL \| Collection name concatenated in filter ('{collection}_v1' vulnerable) \| Whitelist collection names: `VALID_COLLECTIONS = {'capture', 'recall'}; assert user_coll in VALID_COLLECTIONS` + test \| HIGH |
| R3 | O(n²) algoritmus | `src/llmem/recall/pipeline.py:150` \| R3 \| HIGH \| Nested loop compares every candidate with every other (O(n²) dedup) \| Change to set-based: `seen = set(); dedup = [x for x in candidates if not (h := hash(x)) in seen and not seen.add(h)]` (O(n)). Add benchmark test. \| HIGH | For actual: `src/llmem/recall/pipeline.py:150 \| R3 \| HIGH \| Triple nested loop searching items (O(n³) complexity) \| Refactor: pre-index by tier in dict, then iterate tier→candidates. Complexity O(n). Add test with 1000 items. \| MEDIUM |
| R3 | Unbounded I/O | `src/llmem/api/routes/memories.py:40` \| R3 \| HIGH \| GET /memories returns all records without limit (unbounded) \| Add pagination: `query_limit = request.limit or 100; limit to min(query_limit, 1000)`. Add test with 10k items, verify only 1000 returned. \| HIGH | For actual: `src/llmem/storage/log_jsonl.py:80 \| R3 \| HIGH \| JSONL read() loads entire file into memory (no streaming) \| Replace `with open(f) as f: data = f.read()` with streaming: `for line in f: process(json.loads(line))`. Verify memory usage <10MB on 100MB file. \| MEDIUM |
| R4 | Missing error handling | `src/llmem/api/routes/recall.py:25` \| R4 \| CRITICAL \| Backend.search() call has no try/except (unhandled 500) \| Wrap: `try: results = backend.search(...) except BackendError as e: log.warning(...); return graceful_empty_response()` \| HIGH | For actual: `src/llmem/services/capture_service.py:60 \| R4 \| HIGH \| Qdrant upsert() can fail but error not caught (event data lost) \| Add: `try: backend.upsert(...) except QdrantError: log.warning('backend unavailable'); pass` (fail-open per design). Test: `test_capture_backend_unavailable_still_logs()` \| HIGH |
| R4 | Missing timeout | `src/llmem/api/server.py:100` \| R4 \| HIGH \| Backend Qdrant calls have no timeout (could hang forever) \| Add from config: `timeout = config.QDRANT_TIMEOUT or 30`. Pass `timeout=timeout` to qdrant_client calls. Test: `test_qdrant_timeout_detected()` with mock delay. \| HIGH | For actual: `src/llmem/recall/pipeline.py:180 \| R4 \| MEDIUM \| Backend search() lacks timeout in deployment (QA issue) \| Add timeout from config.md COMMANDS.timeout_backend. Wrap with `signal.alarm()` or asyncio timeout. Test simulated 10s delay. \| MEDIUM |
| R4 | Missing retry | `src/llmem/services/capture_service.py:75` \| R4 \| MEDIUM \| JSONL append fails on transient error, no retry \| Add exponential backoff: `for attempt in range(3): try: log_manager.append(...); break; except IOError: sleep(0.1 * 2^attempt)` \| MEDIUM | For actual: `src/llmem/storage/backends/qdrant.py:95 \| R4 \| MEDIUM \| Qdrant connection can fail transiently, no retry logic \| Implement: `@retry(max_attempts=3, backoff=exponential)` decorator from tenacity. Test: simulate flaky connection. \| MEDIUM |
| R5 | Untested code path | `src/llmem/triage/patterns.py:200` \| R5 \| HIGH \| Line 200-210 (secret detection for Bearer tokens) has no unit test \| Add test: `test_detect_secrets_bearer_token()` with inputs `"Bearer sk-1234"` expecting found=True, masked properly. Check pattern matches real token examples. \| HIGH | For actual: `src/llmem/recall/scoring.py:88` \| R5 \| HIGH \| Error path (invalid score type) untested \| Add: `test_combine_score_invalid_score_type()` calling with invalid type, expect ValueError or fallback score=0.0. Cover all 3 score components. \| HIGH |
| R5 | Flaky test | `tests/test_recall_pipeline.py:120` \| R5 \| MEDIUM \| Test uses time.sleep(0.5) causing intermittent failures under load \| Remove sleep. Mock time with freezegun or mock datetime. Or add `@pytest.mark.timeout(10)` to catch hangs. Isolate external call (mock backend.search()). \| MEDIUM | For actual: `tests/test_capture_service.py:45 \| R5 \| MEDIUM \| Test has random delay (time.sleep in loop), flakes on slow CI \| Replace sleep with mock/fixture. Use pytest-asyncio for async tests. Add `@pytest.mark.timeout(5s)` to fail fast. \| MEDIUM |
| R6 | Bad naming | `src/llmem/scoring.py:50` \| R6 \| LOW \| Function `calc()` unclear (should be `calculate_importance_score()`) \| Rename: `calc()` → `calculate_importance_score()` via grep-replace across 2 call sites. Add docstring. \| MEDIUM | For actual: `src/llmem/models.py:12` \| R6 \| LOW \| Class `S()` opaque (should be `SensitivityLevel` or `SensitivityEnum`) \| Rename to `SensitivityLevel` + update 8 references (grep -r 'from.*S[^A-Za-z]' + manual inspect). \| LOW |
| R6 | God function (>50 LOC) | `src/llmem/services/capture_service.py:30` \| R6 \| MEDIUM \| `capture()` is 120 LOC (validation + triage + storage + logging all mixed) \| Refactor into: `_validate_input()`, `_triage_items()`, `_store_items()` (each ~30 LOC). Compose in `capture()`. Update docstrings. \| MEDIUM | For actual: `src/llmem/recall/pipeline.py:45` \| R6 \| MEDIUM \| `generate_recall_response()` is 150 LOC (candidate search + scoring + dedup + injection + formatting) \| Split: extract `_score_candidates()`, `_dedup_by_hash()`, `_apply_budget()`, `_format_injection_block()`. Update tests to use internal functions directly (or keep them public). \| MEDIUM |
| R6 | Dead code | `src/llmem/storage/backends/inmemory.py:100` \| R6 \| LOW \| Function `legacy_search_hybrid()` never called (deprecated) \| Remove the function. Add test: `test_removed_legacy_search_hybrid_not_in_api()` (verify it doesn't exist in final module). \| LOW | For actual: `src/llmem/api/routes/health.py:45` \| R6 \| LOW \| Unused import `datetime` not used in file \| Remove line `import datetime`. Verify no other usage via grep. Test: run linter (ruff check) to confirm. \| LOW |
| R7 | Missing docstring | `src/llmem/recall/scoring.py:78` \| R7 \| LOW \| Function `combine_score()` has no docstring (public API) \| Add: `def combine_score(...): """Combine multi-layer recall scores with tier/scope/recency boosts. Args: base_score (float): raw similarity score. tier_boost (float): bonus for must_remember tier. Returns: float ≥0, ≤1 (normalized). Raises: ValueError if inputs invalid."""` \| MEDIUM |
| R7 | Stale documentation | `src/llmem/ARCHITECTURE.md:45` \| R7 \| LOW \| Doc mentions "v0.1 prototype" but we're on v1.2 \| Update: remove "prototype", add current version, verify all code examples match line numbers (3 examples in doc need spot-check). Add footer: `<!-- last-verified: 2026-03-06 -->`. \| LOW | For actual: `docs/API.md:100` \| R7 \| MEDIUM \| API examples show old endpoint paths (/recall/query instead of /recall) \| Update 5 examples. Cross-check against actual routes.py. Add test: `docs_examples_match_actual_routes()` (parse doc code blocks, run them). \| LOW |
| R8 | ADR violation | `src/llmem/triage/heuristics.py:50` \| R8 \| CRITICAL \| Secrets stored plaintext, violates D0001 (accepted ADR: secrets policy: masked or encrypted) \| Either: (a) Implement masking per D0001 Section 3 pattern examples, OR (b) Create new ADR-0006 "Plaintext Secrets MVP" with sunset date + link from D0001. \| HIGH | For actual: `src/llmem/storage/log_jsonl.py:80` \| R8 \| CRITICAL \| JSONL log allows truncation, violates D0003 (append-only requirement) \| Ensure rebuild.py validates log integrity. Disallow truncate API. Update log writing to use O_APPEND flag. Test: verify truncate rejected. OR file ADR superseding D0003 with rationale. \| HIGH |
| R8 | Spec violation | `src/llmem/recall/injection.py:100` \| R8 \| HIGH \| XML output missing CDATA wrapper (violates LLMEM_INJECTION_FORMAT_V1 active spec) \| Wrap memory content in CDATA: `<memory><![CDATA[{content}]]></memory>`. Add test: `test_injection_cdata_for_special_chars()` with &, <, > in content. \| MEDIUM | For actual: `src/llmem/models.py:35` \| R8 \| HIGH \| Model MemoryItem.timestamp format (epoch int) differs from spec (ISO 8601 string) \| Change timestamp to ISO: `datetime.isoformat()`. Update 5 places that construct MemoryItem. Add test: `test_memory_timestamp_iso_format()`. \| MEDIUM |
| R9 | Process contract violation | `src/llmem/triage/heuristics.py` (changed) \| R9 \| HIGH \| Changed file is in contract_modules of process int-capture-triage-store, but process-chain test fails (test_triage_and_recall.py FAILS) \| (a) Debug process test (run `pytest tests/test_triage_and_recall.py -v`). (b) Fix the implementation to restore test PASS. (c) Verify: `git diff` shows only triage.py changed, not models/patterns. (d) Verify backward compat with prev data. \| HIGH |
| R9 | Process-test missing/failing | int-capture-triage-store has no process-chain test \| R9 \| HIGH \| No test file `tests/test_processes/test_int_capture_triage_store.py` (process-chain validation) \| Create test: `tests/test_processes/test_int_capture_triage_store.py` with (1) valid event → verify all contract modules invoked correctly, (2) invalid event → verify error handling, (3) side effect check (JSONL written, backend updated). \| MEDIUM |

**Anti-patterns (ZAKÁZÁNO v REWORK doporučeních):**
- ❌ „Oprav bug v souboru X" (neříká JAK)
- ❌ „Přidej testy" (neříká KOLIK a JAKÉ)
- ❌ „Vylepši error handling" (neříká KTERÝ error a JAK)
- ✅ „V `scoring.py:45` přidej `try/except ValueError:` kolem `float(score)` s fallback `score=0.0` + test `test_scoring_invalid_input`"

### Anti-Pattern Detection Bash for All R1-R9 Dimensions (WQ4 fix)

```bash
#!/bin/bash
echo "=== R1-R9 ANTI-PATTERN DETECTION ==="

# Get changed files
git diff --name-only {main_branch}...{wip_branch} > /tmp/changed_files.txt

# R1: Logic bugs & edge cases
echo "=== R1: Correctness Anti-Patterns ==="
grep -rn "if.*==" /tmp/changed_files.txt | while read file; do
  grep -n "^\s*else:" "$file" | wc -l | { read count; [ $count -eq 0 ] && echo "R1-WARN: $file has if/elif but no else (potential unhandled case)"; }
done
# Detection: inverted logic
grep -rn "if not\|if !" /tmp/changed_files.txt | head -5 | while read line; do
  echo "R1-CHECK (inverted logic): $line"
done
# Detection: magic numbers
grep -rn "[0-9]\{2,\}" /tmp/changed_files.txt | grep -v ":\s*#" | head -5 | while read line; do
  echo "R1-CHECK (magic number?): $line"
done

# R2: Security
echo "=== R2: Security Anti-Patterns ==="
# Check for eval/exec/pickle
grep -rn "eval\|exec\|pickle\.loads" /tmp/changed_files.txt && echo "R2-FAIL: Found eval/exec/pickle usage (CRITICAL)"
# Check for hardcoded secrets
grep -rn "password\|secret\|api_key\|token" /tmp/changed_files.txt | grep -i "=\s*['\"]" | grep -v "# \|mock\|test" && echo "R2-FAIL: Potential hardcoded secret"
# Check for unvalidated user input
grep -rn "request\.\|args\[" /tmp/changed_files.txt | grep -v "Pydantic\|BaseModel\|validate" | head -3 && echo "R2-WARN: User input used without validation guard visible"
# Check for bare SQL
grep -rn "f\"\|\.format\|%\s" /tmp/changed_files.txt | grep -i "select\|insert\|update\|delete" && echo "R2-WARN: Potential SQL concatenation (not parameterized)"

# R3: Performance
echo "=== R3: Performance Anti-Patterns ==="
# Check for nested loops (O(n²))
grep -rn "for.*in.*for.*in" /tmp/changed_files.txt && echo "R3-WARN: Nested loop detected (check for O(n²) complexity)"
# Check for list.append in loop
grep -rn "\.append\(" /tmp/changed_files.txt | grep -B 2 "for " | grep -c "append" | { read count; [ $count -gt 0 ] && echo "R3-WARN: list.append in loop (consider pre-allocation or set)"; }
# Check for N+1 queries
grep -rn "for.*in.*\|while" /tmp/changed_files.txt | grep -A 5 "db\.\|backend\.\|request\." | grep -c "backend" | { read count; [ $count -gt 1 ] && echo "R3-WARN: Potential N+1 query pattern"; }

# R4: Reliability
echo "=== R4: Reliability Anti-Patterns ==="
# Check for bare except
grep -rn "except:" /tmp/changed_files.txt && echo "R4-FAIL: Found bare except: (should specify exception type)"
# Check for missing timeout
grep -rn "request\.\|urllib\.\|socket\." /tmp/changed_files.txt | grep -v "timeout\|timeout=" && echo "R4-WARN: Network call without explicit timeout guard"
# Check for missing error handling on I/O
grep -rn "open(\|read(\|write(" /tmp/changed_files.txt | grep -v "try\|with " && echo "R4-WARN: File operation without context manager or try/except"

# R5: Testability
echo "=== R5: Testability Anti-Patterns ==="
grep -rn "def test_" tests/ | while read test_line; do
  TEST_FILE=$(echo "$test_line" | cut -d: -f1)
  ASSERT_COUNT=$(echo "$test_line" | grep -o "assert" | wc -l)
  [ "$ASSERT_COUNT" -lt 1 ] && echo "R5-FAIL: Test has no assertions: $test_line"
  [ "$ASSERT_COUNT" -lt 2 ] && echo "R5-WARN: Test has <2 assertions (weak validation): $test_line"
done
# Check for time.sleep in tests
grep -rn "sleep(" tests/ --include='*.py' | grep -v "mock\|patch" && echo "R5-FAIL: Found sleep() in test (should use mock time)"

# R6: Maintainability
echo "=== R6: Maintainability Anti-Patterns ==="
# Check function size (LOC)
grep -rn "^def " /tmp/changed_files.txt | while read func; do
  FUNC_NAME=$(echo "$func" | grep -oP 'def \K\w+')
  FILE=$(echo "$func" | cut -d: -f1)
  START_LINE=$(echo "$func" | cut -d: -f2)
  END_LINE=$((START_LINE + 50))  # Heuristic: count lines
  LOC=$(sed -n "${START_LINE},${END_LINE}p" "$FILE" | wc -l)
  [ "$LOC" -gt 50 ] && echo "R6-WARN: Function $FUNC_NAME in $FILE is >50 LOC (consider splitting)"
done
# Check for DRY violations (copy-paste)
git diff {main_branch}...{wip_branch} | grep "^+" | head -100 | sort | uniq -c | sort -rn | head -5 | { read count; [ $count -gt 3 ] && echo "R6-WARN: Potential copy-paste code detected"; }

# R7: Documentation
echo "=== R7: Documentation Anti-Patterns ==="
# Check for missing docstrings on public functions
grep -rn "^def [^_]" /tmp/changed_files.txt | while read func; do
  FILE=$(echo "$func" | cut -d: -f1)
  LINE=$(echo "$func" | cut -d: -f2)
  NEXT_LINE=$((LINE + 1))
  HAS_DOCSTRING=$(sed -n "${NEXT_LINE}p" "$FILE" | grep -c "\"\"\"")
  [ "$HAS_DOCSTRING" -eq 0 ] && echo "R7-WARN: Public function missing docstring: $func"
done
# Check for CHANGELOG update (if code changed)
if [ -n "$(git diff --name-only {main_branch}...{wip_branch} | grep -v test)" ]; then
  git diff --name-only {main_branch}...{wip_branch} | grep -q "CHANGELOG" || echo "R7-WARN: Code changed but CHANGELOG not updated"
fi

# R8: Compliance (ADR/Spec)
echo "=== R8: Compliance Anti-Patterns ==="
# Check if diff violates any accepted ADR
for adr_file in {WORK_ROOT}/decisions/*.md; do
  [ -f "$adr_file" ] && grep -q "Status: Accepted\|Status: Active" "$adr_file" && {
    ADR_NAME=$(basename "$adr_file" .md)
    # Check if any changed file is in contract_modules
    grep -q "contract_modules:" "$adr_file" && {
      MODULES=$(grep -A 10 "contract_modules:" "$adr_file" | grep "^\s*-" | sed 's/^.*"\(.*\)".*/\1/')
      while read module; do
        git diff --name-only {main_branch}...{wip_branch} | grep -q "$module" && {
          echo "R8-CHECK: Changed file $module is in ADR $ADR_NAME — verify compliance"
        }
      done <<< "$MODULES"
    }
  }
done

# R9: Process Chain
echo "=== R9: Process Chain Anti-Patterns ==="
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if [ -f "$PROCESS_MAP" ]; then
  git diff --name-only {main_branch}...{wip_branch} | while read changed_file; do
    PROCESSES=$(grep "contract_modules:" "$PROCESS_MAP" -B 2 | grep "^[a-zA-Z_-]*:" | sed 's/:$//')
    for process in $PROCESSES; do
      grep -A 10 "^$process:" "$PROCESS_MAP" | grep -q "$changed_file" && {
        PROCESS_TEST="{WORK_ROOT}/tests/test_processes/test_${process}.py"
        if [ ! -f "$PROCESS_TEST" ]; then
          echo "R9-FAIL: Changed file in process $process but process-test missing: $PROCESS_TEST"
        fi
      }
    done
  done
fi

echo "=== ANTI-PATTERN DETECTION COMPLETE ==="
```

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
   - `status:` (fabric-review nastaví předběžně; fabric-loop je autoritativní owner a může přepsat)
     - `CLEAN` → `DONE`
     - `REWORK` → `IN_PROGRESS`
     - `REDESIGN` → `BLOCKED` (fabric-loop ověří a potvrdí; pokud review nenastaví, loop nastaví sám)

---

> Skeleton reportu nepiš ručně — používej template `review-summary.md`.

## Downstream Contract

**fabric-close** (next skill) reads from review report:
- `version` (string) — report schema version (e.g., "1.0")
- `verdict` (enum) — CLEAN | REWORK | REDESIGN (parsovatelný — MUST be on own line exactly: "Verdict: CLEAN")
- `r1_score` through `r9_score` (float) — per-dimension scores (0-100)
- `findings[]` (list) — all identified issues with structure:
  - `dimension` (enum) — R1 through R9
  - `severity` (enum) — CRITICAL | HIGH | MEDIUM | LOW
  - `file_line` (string) — e.g., "src/llmem/capture.py:45"
  - `description` (string)
  - `fix_procedure` (string) — concrete steps to fix
  - `estimated_effort` (string) — time to fix
- `gate_results` (dict) — outcome of objective gates:
  - `lint_pass` (bool)
  - `format_pass` (bool)
  - `test_pass` (bool)
  - `test_report_path` (string)
- `critical_findings_count` (int) — number of CRITICAL severity findings
- `rework_verdict_blocks_close` (bool) — True if verdict != CLEAN (blocks fabric-close from marking DONE)

## Blocking Validation (WQ10 fix — CRITICAL findings MUST return FAIL verdict)

```bash
#!/bin/bash
echo "=== REVIEW REPORT VALIDATION GATE ==="

REPORT="{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-*.md"

if [ ! -f "$REPORT" ]; then
  echo "FAIL: Review report does not exist"
  exit 1
fi

# 1. Verdict must be present and valid
VERDICT=$(grep "^Verdict:" "$REPORT" | awk '{print $2}')
if [ -z "$VERDICT" ]; then
  echo "FAIL: Report has no Verdict line (required: 'Verdict: CLEAN|REWORK|REDESIGN')"
  exit 1
fi
if ! echo "$VERDICT" | grep -qE "^(CLEAN|REWORK|REDESIGN)$"; then
  echo "FAIL: Verdict '$VERDICT' is invalid (must be CLEAN, REWORK, or REDESIGN)"
  exit 1
fi

# 2. All R1-R9 dimensions must be scored
for dim in R1 R2 R3 R4 R5 R6 R7 R8 R9; do
  SCORE=$(grep "^## $dim\|^| $dim " "$REPORT" | grep -oP '\d+/100|\d+\.\d+/100' | head -1)
  if [ -z "$SCORE" ]; then
    # R9 can be skipped if process-map doesn't exist
    if [ "$dim" != "R9" ]; then
      echo "WARN: Dimension $dim has no score (optional for R9 if process-map missing)"
    fi
  fi
done

# 3. CRITICAL findings MUST cause REWORK or REDESIGN verdict (NOT CLEAN)
CRITICAL_COUNT=$(grep -c "CRITICAL" "$REPORT" || echo 0)
if [ "$CRITICAL_COUNT" -gt 0 ] && [ "$VERDICT" = "CLEAN" ]; then
  echo "FAIL: Report has $CRITICAL_COUNT CRITICAL findings but verdict is CLEAN"
  echo "CRITICAL findings MUST result in REWORK or REDESIGN verdict"
  exit 1
fi

# 4. All findings must have required fields
FINDING_COUNT=$(grep "^| [R][1-9].*|" "$REPORT" | wc -l)
if [ "$FINDING_COUNT" -gt 0 ]; then
  # Check each finding has: dimension, severity, file:line, description, fix
  INCOMPLETE=$(grep "^| [R][1-9]" "$REPORT" | while read line; do
    FIELDS=$(echo "$line" | awk -F'|' '{print NF}')
    if [ "$FIELDS" -lt 5 ]; then
      echo "INCOMPLETE_FINDING"
    fi
  done | wc -l)

  if [ "$INCOMPLETE" -gt 0 ]; then
    echo "FAIL: $INCOMPLETE findings are incomplete (missing fields: severity, file:line, fix, effort)"
    exit 1
  fi
fi

# 5. If verdict is REWORK, must explain why (findings present)
if [ "$VERDICT" = "REWORK" ]; then
  if [ "$CRITICAL_COUNT" -eq 0 ] && [ "$(grep -c 'HIGH' "$REPORT" || echo 0)" -lt 1 ]; then
    echo "WARN: Verdict is REWORK but <1 CRITICAL/HIGH finding visible"
  fi
fi

# 6. Gates must all show explicit results
for gate in "Linting\|ruff check\|lint" "Format\|ruff format\|format" "Test\|pytest\|test"; do
  if ! grep -q "$gate" "$REPORT"; then
    echo "WARN: Gate result not documented: $gate"
  fi
done

echo "PASS: Review report validation successful"
echo "  Verdict: $VERDICT"
echo "  Critical Findings: $CRITICAL_COUNT"
echo "  All dimensions scored and findings have required fields"
exit 0
```

## Checklist (co musí být v reportu — vše povinné)

- **Per-dimension R1–R9 tabulka** — VŽDY, i pro triviální změny. Minimální formát:

  ```markdown
  | Dim | Score | Findings |
  |-----|-------|----------|
  | R1 Correctness | 5/5 | No issues |
  | R2 Security | 5/5 | No issues |
  | R3 Performance | 5/5 | No issues |
  | R4 Reliability | 5/5 | No issues |
  | R5 Testability | 5/5 | No issues |
  | R6 Maintainability | 5/5 | No issues |
  | R7 Documentation | 5/5 | No issues |
  | R8 Compliance | 5/5 | No ADR/spec conflicts |
  | R9 Process Chain | 5/5 | No process contract violations |
  ```

- **CRITICAL/HIGH findings** — pokud existují, vypiš konkrétně (soubor, řádek, důvod)
- **Verdict** — explicitně: `Verdict: CLEAN` nebo `Verdict: REWORK`
- **Suggested next step** — 1 věta

> **Zkrácený review ("All 5/5, no findings") je skill violation.** I pro triviální change musíš uvést R1–R9 tabulku, aby bylo jasné, že jsi každou dimenzi reálně prověřil.

---

## Self-check

### Existence checks
- [ ] Review report existuje: `{WORK_ROOT}/reports/review-{wip_item}-{YYYY-MM-DD}-{run_id}.md`
- [ ] Report má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Backlog item `{WORK_ROOT}/backlog/{wip_item}.md` aktualizován s `review_report` polem
- [ ] Protocol log má START a END záznam s `skill: review`

### Quality checks
- [ ] **R1–R9 tabulka je přítomna** (ne jen souhrnné „All 5/5") — každá dimenze má konkrétní nalezení
- [ ] **R9 status je recorded**: SKIPPED / PASS / ALERT / CRITICAL pro každou dimenzi
- [ ] **Verdict je explicitní**: CLEAN / REWORK / REDESIGN s vysvětlením
- [ ] **Backlog item aktualizován**: `review_report: {report_path}` + `status: IN_REVIEW` (během) nebo `APPROVED` (po CLEAN verdict)
- [ ] **Findings mají evidence**: Každé finding má soubor:linie nebo konkrétní evidence (ne „code quality issues")
- [ ] **Risk hodnocení**: ALERT/CRITICAL findings mají risk/impact/mitigation

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/reports/`, `{WORK_ROOT}/backlog/` nebyl modifikován (review je read-only code audit)
- [ ] Git working tree NENÍ změněn (review nesmí commitovat)
- [ ] State.md NENÍ modifikován (review jen analyzuje)
- [ ] Protocol log má START i END záznam

---

## Scope varianty (volitelné — dispatcher určuje scope)

### `--scope=codebase` — Codebase-wide review — SPECIFICATION (WQ9 fix)

Pokud dispatcher (fabric-loop nebo člověk) spustí review se `scope=codebase`:

**Step 1: Identify largest files (potential god-objects)**
```bash
find "${CODE_ROOT}" -name "*.py" -type f -exec wc -l {} \; | sort -rn | head -20
# Files >200 LOC are candidates for breakdown → R6 finding
# Files >500 LOC are critical for refactor → intake item
```

**Step 2: Cyclomatic complexity check (for large files)**
```bash
# For each file with >200 LOC, estimate complexity via decision points
for file in $(find "${CODE_ROOT}" -name "*.py" -type f); do
  LOC=$(wc -l < "$file")
  if [ "$LOC" -gt 200 ]; then
    # Count if/for/while/try/and/or — rough complexity estimate
    COMPLEXITY=$(grep -E '^\s*(if |for |while |try:|elif |except|and |or )' "$file" | wc -l)
    if [ "$COMPLEXITY" -gt 30 ]; then
      echo "HIGH complexity: $file (${LOC} LOC, ~${COMPLEXITY} decisions)"
    fi
  fi
done
```

**Step 3: Duplicate code detection (cross-file patterns)**
```bash
# Find code blocks appearing ≥3 times across different files
for file1 in $(find "${CODE_ROOT}" -name "*.py"); do
  for file2 in $(find "${CODE_ROOT}" -name "*.py"); do
    [ "$file1" != "$file2" ] || continue
    # Simplified: grep for common patterns (e.g., error handling templates)
    SHARED=$(grep -F "try:" "$file1" | grep -F "except" | wc -l)
    if [ "$SHARED" -gt 5 ]; then
      echo "Potential duplicate error handling patterns: $file1 vs $file2"
    fi
  done
done
```

**Step 4: Consistent patterns check (naming, style)**
```bash
# Check function naming consistency
echo "=== Function naming patterns ==="
grep -rn "^def [a-z_]*(" "${CODE_ROOT}" | sed 's/.*def //' | sed 's/(.*/:/' | sort | uniq -c | sort -rn | head -20
# Expect: verb_noun pattern dominant. Anomalies → R6 finding

# Check class naming consistency
echo "=== Class naming patterns ==="
grep -rn "^class [A-Z]" "${CODE_ROOT}" | sed 's/.*class //' | sed 's/(.*/:/' | sort | uniq -c | sort -rn
# Expect: PascalCase {Noun}{Role} dominant. Anomalies → R6 finding
```

**Step 5: Dead code detection (unused imports, orphaned functions)**
```bash
# Unused imports
echo "=== Potentially unused imports ==="
grep -rn "^import\|^from" "${CODE_ROOT}" --include="*.py" | cut -d: -f1 | sort | uniq > /tmp/all-imports.txt

for imp in $(cat /tmp/all-imports.txt); do
  MOD=$(grep "^import\|^from" "$imp" | head -1 | awk '{print $2}' | sed 's/\..*//')
  if ! grep -q "$MOD" "$imp" | grep -v "^import\|^from"; then
    echo "WARN: Unused import in $imp: $MOD"
  fi
done
```

**Step 6: Orphaned test files (tests for non-existent modules)**
```bash
for test_file in $(find "${TEST_ROOT}" -name "test_*.py"); do
  MODULE=$(basename "$test_file" | sed 's/^test_//' | sed 's/.py$//')
  if ! find "${CODE_ROOT}" -name "${MODULE}.py" | grep -q .; then
    echo "WARN: Orphaned test file: $test_file (no matching module)"
  fi
done
```

1. Ignoruj `wip_item` / `wip_branch` — review se týká CELÉHO codebase na `main`
2. Pro R1-R8: projdi CELÝ `{CODE_ROOT}/` (ne jen diff) per specifikaci výše
3. Fokus na systémové problémy:
   - Duplicitní kód across souborů (grep pro podobné bloky ≥10 řádků)
   - Nekonzistentní patterns (různé error handling styly, různý naming)
   - Dead code (unused imports: `grep -rn "^import\|^from" | sort | uniq -c | sort -rn`)
   - Orphaned testy (test soubory pro moduly které neexistují)
4. Verdikt: `CLEAN` / `NEEDS_ATTENTION` (ne REWORK — codebase review nemá single task k opravě)
5. Výstup: intake items pro systémové problémy (ne per-task REWORK)

### `--scope=sprint` — Sprint-wide review — SPECIFICATION (WQ9 fix)

Pokud dispatcher spustí review se `scope=sprint`:

**Step 1: Gather all sprint changes**
```bash
SPRINT=$(grep '^sprint:' "{WORK_ROOT}/state.md" | awk '{print $2}')
SPRINT_START_DATE=$(grep -A 3 "^## Sprint ${SPRINT}" "{WORK_ROOT}/sprints/sprint-${SPRINT}.md" | grep 'start_date:' | awk '{print $2}')
SPRINT_START_SHA=$(git log --before="${SPRINT_START_DATE}" --oneline | head -1 | awk '{print $1}')

echo "Analyzing sprint ${SPRINT} (${SPRINT_START_SHA}...HEAD)"
git diff --stat "${SPRINT_START_SHA}...HEAD"
git diff --name-only "${SPRINT_START_SHA}...HEAD" > /tmp/sprint-files.txt
```

**Step 2: Per-file R1-R9 checklist (map to tasks)**
```bash
# For each changed file, identify which backlog item (task) introduced it
while IFS= read -r changed_file; do
  TASK=$(git log --oneline "${SPRINT_START_SHA}...HEAD" -- "$changed_file" | head -1 | grep -o '[A-Za-z0-9_-]*' | tail -1)
  echo "File: $changed_file → Task: $TASK"

  # Run R1-R9 checklist on this file
  # R1: Correctness — logic bugs?
  grep -n "if.*==\|<\|>" "$changed_file" | head -5 # Sample boundary checks

  # R2: Security — validation present?
  grep -n "raise ValueError\|TypeError\|assert" "$changed_file" | head -3

  # R3: Performance — N+1 loops?
  grep -n "for.*for\|while.*while" "$changed_file"
done < /tmp/sprint-files.txt
```

**Step 3: Cross-task interaction check (task A breaks task B?)**
```bash
# Identify model/API changes that might affect other tasks
echo "=== Model/API changes (potential cross-task impact) ==="
git diff "${SPRINT_START_SHA}...HEAD" -- "{CODE_ROOT}/models.py" "{CODE_ROOT}/api/routes/*.py" \
  | grep "^+\|^-" | grep -E "class |def |@router" | head -20

# For each change, check if it breaks tests from other tasks
echo "=== Cross-task test impact ==="
for task in $(grep '^id:' {WORK_ROOT}/backlog/*.md | grep "^{WORK_ROOT}/backlog/" | awk -F: '{print $1}' | sed 's|.*/||' | sed 's/.md//'); do
  TEST_REPORT=$(ls -t {WORK_ROOT}/reports/test-${task}-*.md 2>/dev/null | head -1)
  if [ -f "$TEST_REPORT" ]; then
    if grep -q "FAIL\|ERROR" "$TEST_REPORT"; then
      echo "ALERT: Task $task test report shows FAIL (cross-task regression?)"
    fi
  fi
done
```

**Step 4: Naming/pattern consistency across sprint tasks**
```bash
echo "=== Function naming consistency across sprint changes ==="
git diff "${SPRINT_START_SHA}...HEAD" -- "${CODE_ROOT}" | grep "^+.*def " | sed 's/.*def //' | sed 's/(.*/:/' | sort | uniq -c
# Expect: consistent {verb}_{noun} pattern. Anomalies → HIGH finding
```

**Step 5: Duplicated code introduced by sprint**
```bash
# Find code blocks added in sprint that appear >2 times
git diff "${SPRINT_START_SHA}...HEAD" -- "${CODE_ROOT}/*.py" \
  | grep "^+" \
  | grep -v "^+++" \
  | sort | uniq -c | sort -rn | head -20 \
  | awk '$1 > 2 { print "WARN: Duplicated code pattern: " $0 }'
```

1. Diff: `git diff {sprint_start_sha}...HEAD` (celý sprint, ne jeden task)
2. Pro R1-R8: hodnoť CELÝ sprint diff per specifikaci výše
3. Fokus na cross-task problémy:
   - Cross-task interakce (task A mění model, task B ho čte — kompatibilita?)
   - Duplicitní kód zavedený různými tasks (copy-paste across tasks)
   - Nekonzistentní naming/patterns zavedené různými tasks
   - Celková architektonická koherence sprint diffu
4. Verdikt: `CLEAN` / `REWORK` (pokud cross-task problémy vyžadují opravu)
5. Výstup: review report s `scope: sprint` + intake items pro systémové findings

> **Poznámka:** Sprint-scope review by měl být volán z `fabric-close` po všech mergích (krok 8c) pokud sprint diff ≥20 souborů.

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

1) Otevři `decisions/INDEX.md` a identifikuj **všechny `accepted` ADR** (ne jen ty zmíněné v analýze — analýza může opomenout závislost).
2) Otevři `specs/INDEX.md` a identifikuj **`active` specs** a **`draft` specs** (draft specs nejsou enforced jako CRITICAL, ale porušení je HIGH finding).
3) Pokud diff zavádí změnu, která **odporuje accepted ADR** nebo **porušuje active spec**:
   - zapiš finding severity **CRITICAL**
   - v reportu cituj konkrétní ADR/SPEC + konkrétní změnu v diffu
   - doporuč: buď upravit implementaci, nebo vytvořit nový ADR/SPEC (nepřepisuj accepted bez procesu)
4) **Kontraktově-citlivé soubory** — pokud diff mění některý z těchto modulů, ověř příslušný kontrakt explicitně:
   - `recall/injection.py` nebo `recall/pipeline.py` → D0004 (injection-contract) + LLMEM_INJECTION_FORMAT_V1 (active): preamble warning musí zůstat, XML struktura musí odpovídat spec, CDATA wrapping zachován
   - `storage/backends/` → LLMEM_QDRANT_SCHEMA_V1 (draft): collection schema, vector params, payload fields
   - `storage/log_jsonl.py` → D0003 (event-sourcing-and-rebuild): JSONL log je immutable (append-only), rebuild musí být možný z logu
   - `triage/heuristics.py` nebo `triage/patterns.py` → D0001 (secrets-policy) + LLMEM_TRIAGE_HEURISTICS_V1 (draft): masking rules, PII hashing
   - `models.py` → D0002 (ids-and-idempotency) + LLMEM_DATA_MODEL_V1 (draft): UUIDv7 z content_hash, idempotency_key musí zůstat, field names/types/enums
   - `api/` → LLMEM_API_V1 (draft): endpoint paths, request/response schema
   - `recall/scoring.py` nebo `recall/pipeline.py` → LLMEM_RECALL_PIPELINE_V1 (draft): scoring formula, budget algorithm
   - Porušení `accepted` ADR nebo `active` spec bez odpovídajícího supersede = **CRITICAL**
   - Porušení `draft` spec = **HIGH** (draft může být upraven, ale musí být vědomé rozhodnutí)


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

## Checklist (co musí být v reportu — vše povinné)

- **Per-dimension R1–R8 tabulka** — VŽDY, i pro triviální změny. Minimální formát:

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
  ```

- **CRITICAL/HIGH findings** — pokud existují, vypiš konkrétně (soubor, řádek, důvod)
- **Verdict** — explicitně: `Verdict: CLEAN` nebo `Verdict: REWORK`
- **Suggested next step** — 1 věta

> **Zkrácený review ("All 5/5, no findings") je skill violation.** I pro triviální change musíš uvést R1–R8 tabulku, aby bylo jasné, že jsi každou dimenzi reálně prověřil.

---

## Self-check

- review report exists
- **R1–R8 tabulka je přítomna** (ne jen souhrnné "All 5/5")
- backlog item has `review_report`
- verdict is explicit (CLEAN/REWORK/REDESIGN)

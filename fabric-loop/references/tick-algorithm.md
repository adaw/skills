# Tick Algorithm — Detailed Reference

This document contains the detailed tick algorithm, counters, auto-fix logic, and verdict parsing from fabric-loop. See SKILL.md for the main orchestration logic.

---

## Tick algoritmus (deterministický)

V rámci každého loopu proveď nejvýše `MAX_TICKS_PER_LOOP` ticků. Pro každý tick:

1) Načti `{WORK_ROOT}/state.md`.
2) Pokud `state.error != null` → spusť crash recovery (sekce níže) a **STOP**.
3) Pokud `state.step == "idle"`:
   - proveď *idle tick* deterministicky (bez `--completed`):

     ```bash
     python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}
     ```

   - znovu načti `{WORK_ROOT}/state.md`:
     - pokud je stále `idle` → zaloguj "no work, idle" a **STOP (OK)**
     - pokud `state.error != null` → **STOP + ESCALATE**
     - jinak pokračuj (nový sprint začíná).
4) Dispatchni skill pro aktuální `state.step` (podle tabulky „next step" v references/dispatch-recovery.md).
   - ulož si `COMPLETED_STEP = state.step` (budeš ho používat pro kontrakt + tick + run report)
5) Ověř kontrakt výstupů deterministicky:

   ```bash
   python skills/fabric-init/tools/fabric.py contract-check --step "<COMPLETED_STEP>"
   CONTRACT_EXIT=$?
   if [ $CONTRACT_EXIT -ne 0 ]; then
     echo "STOP: contract-check FAIL for step $COMPLETED_STEP (exit $CONTRACT_EXIT)"
     python skills/fabric-init/tools/fabric.py state-patch --fields-json "{\"error\": \"STOP: contract-check FAIL — $COMPLETED_STEP\"}"
     # Vytvoř intake item
     python skills/fabric-init/tools/fabric.py intake-new --source "loop" --slug "contract-breach-$COMPLETED_STEP" \
       --title "Contract check failed for $COMPLETED_STEP"
     exit 1
   fi
   ```
6) Deterministicky posuň stav jedním příkazem (gating + next step + patch state):

   ```bash
   python skills/fabric-init/tools/fabric.py tick --completed "<COMPLETED_STEP>" --run-mode auto {GOAL_ARG}
   ```

   - `tick` řeší všechny guardy:
     - po `test` čte poslední test report (vyžaduje `Result: PASS|FAIL|TIMEOUT`)
     - po `review` čte poslední review report (vyžaduje `verdict: CLEAN|REWORK|REDESIGN` nebo `Verdict:`)
     - po `analyze` kontroluje Task Queue — pokud je prázdná (0 tasks) → next step = `docs` (přeskoč implement)
     - po `close` rozhodne mezi `implement` vs `docs` podle sprint plánu
     - po `prio` a po `archive` umí spadnout do `idle` (pokud není práce)
      - po `archive` incrementuje `state.sprint` a tím uzavírá loop
   - `tick` patchne `state.md` (`step/phase/last_completed/last_run/last_tick_at`).
   - pokud chybí důkazy nebo je kontrakt porušen → nastaví `state.error` a vrátí non‑zero → **STOP + ESCALATE**.

   Mapování `step → phase`:
   - **orientation:** vision, status, architect, process, gap, generate, intake, prio
   - **planning:** sprint, analyze
   - **implementation:** implement, test, review
   - **closing:** close, docs, check, archive
   - **idle:** idle
7) Zapiš odkaz na hlavní run report do `{WORK_ROOT}/reports/run-{run_id}.md` (append-only).

   **run_id mechanismus:** `--ensure-run-id` flag zajistí, že:
   - Pokud `state.run_id` EXISTUJE (nastavený z předchozího tick v tomto runu) → použij ho (append do stejného run reportu).
   - Pokud `state.run_id` je `null` (nový run) → vygeneruj nový `run_id` (formát: `{YYYY-MM-DD}-{sekvence}`), zapiš ho do `state.run_id` a vytvoř nový run report.
   - Sub-skilly (implement, test, review, close) NEPOUŽÍVAJÍ run_id přímo — run report je zodpovědnost fabric-loop, ne sub-skillů. Sub-skilly píší vlastní reporty (test-*.md, review-*.md atd.) a fabric-loop na ně odkazuje v run reportu.
   - `run_id` se resetuje na `null` při `state.step = idle` (nový cyklus = nový run).

   **Explicitní kód pro run_id lifecycle:**
   ```bash
   # Na začátku každého tick cyklu (krok 2):
   RUN_ID=$(python skills/fabric-init/tools/fabric.py state-read --field run_id 2>/dev/null)
   STATE_GET_EXIT=$?
   if [ $STATE_GET_EXIT -ne 0 ]; then
     echo "WARN: state-read failed (exit $STATE_GET_EXIT), treating as null"
     RUN_ID=""
   fi
   # Validate existing run_id format (YYYY-MM-DD-N)
   if [ -n "$RUN_ID" ] && [ "$RUN_ID" != "null" ]; then
     if ! echo "$RUN_ID" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]+$'; then
       echo "WARN: invalid run_id format '$RUN_ID', regenerating"
       RUN_ID=""
     fi
   fi
   if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
     # Nový run — generuj run_id
     SEQ=$(ls {WORK_ROOT}/reports/run-*.md 2>/dev/null | wc -l)
     RUN_ID="$(date +%Y-%m-%d)-$((SEQ + 1))"
     python skills/fabric-init/tools/fabric.py state-patch --fields-json "{\"run_id\": \"$RUN_ID\"}"
     PATCH_EXIT=$?
     if [ $PATCH_EXIT -ne 0 ]; then
       echo "WARN: state-patch run_id failed (exit $PATCH_EXIT), continuing with local RUN_ID"
     fi
   fi

   # Po archive (přechod do idle) — preserve run_id monotonicity (P2 fix):
   # run_id MUST be monotonically increasing. When idle, set run_id to next integer, never null.
   # This ensures that each run_id is unique and ordered, enabling reproducibility and audit trails.
   NEXT_RUN_ID=$(python skills/fabric-init/tools/fabric.py state-read --field run_id 2>/dev/null)
   if [ -n "$NEXT_RUN_ID" ] && echo "$NEXT_RUN_ID" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]+$'; then
     # Extract counter part and increment
     COUNTER=$(echo "$NEXT_RUN_ID" | awk -F'-' '{print $NF}')
     NEW_COUNTER=$((COUNTER + 1))
     DATE=$(echo "$NEXT_RUN_ID" | cut -d'-' -f1-3)
     INCREMENTED_RUN_ID="${DATE}-${NEW_COUNTER}"
     python skills/fabric-init/tools/fabric.py state-patch --fields-json "{\"run_id\": \"$INCREMENTED_RUN_ID\"}"
   else
     # Fallback: preserve existing run_id instead of null
     echo "WARN: run_id format invalid or missing, preserving current state"
   fi
   ```

   Deterministicky (povinné):

   ```bash
   python skills/fabric-init/tools/fabric.py run-report \
     --ensure-run-id \
     --completed "<COMPLETED_STEP>" \
     --status "OK" \
     --note "<1-line-summary>"
   RR_EXIT=$?
   if [ $RR_EXIT -ne 0 ]; then
     echo "WARN: run-report append failed (exit $RR_EXIT)"
     # Run-report failure je WARNING, ne STOP — audit trail je neúplný, ale orchestrace pokračuje.
     # Zaloguj do protocol.jsonl pro post-mortem analýzu.
   fi
   ```

8) Pokud `AUDIT=1`: proveď **audit provedeného skillu** (po každém ticku).
   > **Poznámka:** Audit logika je INLINE v fabric-loop (ne separátní skill). Audit se provádí jako součást tick algoritmu — contract-check + reports-validate + counter cross-check + audit report zápis. Toto je záměr: audit musí proběhnout atomicky PO každém dispatch a PŘED pokračováním na další tick.

**Kdo generuje:** Audit report generuje **fabric-loop** (orchestrátor), NE sub-skilly. Sub-skilly (implement, test, review, close) generují své vlastní reporty; fabric-loop nad nimi provádí nezávislý audit.

**Kdy:** Po KAŽDÉM úspěšném ticku (krok 6), PŘED zápisem do run reportu (krok 7). Pokud tick selhal (non-zero), audit se neprovádí (state.error je nastavený, následuje STOP).

**Cíl auditu:** Ověřit, že se stalo to, co se mělo stát, že výstupy jsou konzistentní, a že nevznikl drift.

**Deterministické minimum (vždy):**
```bash
# reports-validate je subcommand fabric.py — validuje:
# 1. YAML frontmatter parsovatelný (schema/kind/date povinné)
# 2. Report naming matchuje CONTRACTS.outputs pattern
# 3. Povinné sekce přítomné (Notes nesmí být prázdné pro test/review)
# 4. Verdict/Result řádek přítomný a parsovatelný (pro test/review reporty)
python skills/fabric-init/tools/fabric.py reports-validate --strict
VALIDATE_EXIT=$?
if [ $VALIDATE_EXIT -ne 0 ]; then
  echo "WARN: reports-validate failed (exit $VALIDATE_EXIT)"
fi
```

**Audit report** (1 soubor na tick):
- **Naming:** `{WORK_ROOT}/reports/audit-{COMPLETED_STEP}-{YYYY-MM-DD}-{run_id}.md`
- **Formát (povinný):**

```markdown
---
schema: fabric.audit.v1
kind: audit-{COMPLETED_STEP}
date: {YYYY-MM-DD}
run_id: {run_id}
wip_item: {wip_item nebo null}
verdict: PASS|FAIL
---

# Audit: {COMPLETED_STEP}

## Contract check
{contract-check výstup — PASS/FAIL + detaily}

## Report validation
{reports-validate výstup — PASS/FAIL}

## Evidence
- Step report: reports/{step}-{wip_item}-{date}-{run_id}.md
- State after tick: step={new_step}, phase={new_phase}
{+ counter cross-check pokud step=test nebo review}

## Risks / Notes
{krátký komentář — max 3 řádky}
```

**Postup:**
1. Zavolej `contract-check --step "<COMPLETED_STEP>"` (nebo přečti JSON z kroku 5)
2. Zavolej `reports-validate --strict`
3. Načti poslední report daného kroku (`fabric.py report-latest --kind "<COMPLETED_STEP>"`)
4. **Counter cross-check** (jen po test/review): přečti `test_fail_count` a `rework_count` z backlog itemu, ověř, že souhlasí s počtem FAIL/REWORK reportů v `reports/`
5. Napiš audit report s verdiktem PASS/FAIL

**Audit severity taxonomie:** Definována v `config.md AUDIT_SEVERITY` (source of truth). Shrnutí:
- **CRITICAL** (→ `state.error` + STOP): viz `config.md AUDIT_SEVERITY.CRITICAL.triggers`
- **HIGH** (→ intake item, pokračuj): viz `config.md AUDIT_SEVERITY.HIGH.triggers`
- **LOW** (→ poznámka v audit reportu): viz `config.md AUDIT_SEVERITY.LOW.triggers`

**Audit report schema:** Definován v `config.md AUDIT_REPORT_SCHEMA` — povinné YAML frontmatter fields: `schema`, `kind`, `date`, `run_id`, `wip_item`, `verdict`. Povinné sekce: Contract check, Report validation, Evidence, Risks / Notes.

**Stop pravidlo:** pokud audit verdikt = FAIL (aspoň 1 CRITICAL finding) → nastav `state.error = "STOP: audit CRITICAL — {finding_summary}"` a **STOP**. Pokud verdikt = PASS (žádný CRITICAL, jen HIGH/LOW) → zapiš HIGH findings jako intake itemy a pokračuj.



Pokud kdykoliv nastavíš `state.error` nebo vytvoříš CRITICAL intake (kontrakt breach / config drift) → **STOP okamžitě** (neprováděj další tick).

---

## Countery a limity (per task) — PERSISTED

Countery jsou **persistované v backlog item metadata** (ne in-memory). Tím přežijí crash orchestrátoru.

Při dispatchování implement/test/review, orchestrátor:
1. Načte backlog item `{WORK_ROOT}/backlog/{wip_item}.md`
2. Přečte frontmatter klíče `test_fail_count` a `rework_count` (default 0 pokud chybí)
3. Po tiku — pokud verdict vyžaduje inkrement — aktualizuje hodnotu v backlog itemu (viz explicitní kód níže)

Klíče v backlog item frontmatter (přidej pokud chybí):
```yaml
test_fail_count: 0    # inkrementuje fabric-loop po test FAIL
rework_count: 0       # inkrementuje fabric-loop po review REWORK
```

### Kdy a jak inkrementovat (explicitní kód)

**Po tick() pro step=test**, pokud tick vrátil next_step=implement (tzn. test FAIL):
```bash
# Přečti aktuální counter (s numerickou validací — viz config.md VALIDATION.counter_validation)
CURRENT=$(grep 'test_fail_count:' "{WORK_ROOT}/backlog/${wip_item}.md" | awk '{print $2}')
CURRENT=${CURRENT:-0}
if ! echo "$CURRENT" | grep -qE '^[0-9]+$'; then CURRENT=0; echo "WARN: non-numeric test_fail_count, reset to 0"; fi
NEW=$((CURRENT + 1))
# Zapiš zpět do backlog item frontmatter
sed -i "s/^test_fail_count:.*/test_fail_count: $NEW/" {WORK_ROOT}/backlog/{wip_item}.md || echo "WARN: counter increment failed for test_fail_count"
# Limit check
if [ $NEW -ge {SPRINT.max_rework_iters} ]; then
  # STOP — task je nestabilní
  # Nastav state.error a vytvoř intake item
  echo "STOP: test_fail_count ($NEW) >= max_rework_iters ({SPRINT.max_rework_iters})"
fi
```

**Po tick() pro step=review**, pokud tick vrátil next_step=implement (tzn. review REWORK):
```bash
# Přečti aktuální counter (s numerickou validací)
CURRENT=$(grep 'rework_count:' "{WORK_ROOT}/backlog/${wip_item}.md" | awk '{print $2}')
CURRENT=${CURRENT:-0}
if ! echo "$CURRENT" | grep -qE '^[0-9]+$'; then CURRENT=0; echo "WARN: non-numeric rework_count, reset to 0"; fi
NEW=$((CURRENT + 1))
# Zapiš zpět do backlog item frontmatter
sed -i "s/^rework_count:.*/rework_count: $NEW/" {WORK_ROOT}/backlog/{wip_item}.md || echo "WARN: counter increment failed for rework_count"
```

**Poznámka:** Inkrement se provádí VŽDY v fabric-loop, NIKDY v sub-skillech. Sub-skilly (fabric-test, fabric-review) pouze generují reporty s verdikty. Loop čte verdikty a aktualizuje countery.

- **test_fail_count**: Inkrementuj při `test → FAIL → implement` (viz kód výše). Pokud `test_fail_count >= max_rework_iters` (default 3) → STOP + set `state.error = "test_fail_count exceeded"` + vytvoř intake item. Neposílej zpět na implement — task je nestabilní.
- **rework_count**: Inkrementuj při `review → REWORK → implement` (viz kód výše). Pokud `rework_count >= max_rework_iters` → review by měl vrátit REDESIGN (viz fabric-review pravidla). Orchestrátor to enforceuje explicitně:

```bash
# REWORK→REDESIGN override (v tick algoritmu, PO inkrementu rework_count)
REWORK_COUNT=$(grep 'rework_count:' {WORK_ROOT}/backlog/{wip_item}.md | awk '{print $2}')
REWORK_COUNT=${REWORK_COUNT:-0}
MAX_ITERS={SPRINT.max_rework_iters}  # default 3
REVIEW_VERDICT=$(...)  # parsovaný verdict z review reportu

if [ "$REVIEW_VERDICT" = "REWORK" ] && [ "$REWORK_COUNT" -ge "$MAX_ITERS" ]; then
  echo "OVERRIDE: REWORK→REDESIGN (rework_count $REWORK_COUNT >= max $MAX_ITERS)"
  REVIEW_VERDICT="REDESIGN"
  # Zaloguj override do run reportu
  python skills/fabric-init/tools/fabric.py run-report \
    --ensure-run-id \
    --completed "review" \
    --status "OVERRIDE" \
    --note "REWORK→REDESIGN override: rework_count $REWORK_COUNT >= max_rework_iters $MAX_ITERS"
fi
```

Pokud override nastane, tick pokračuje s `REVIEW_VERDICT=REDESIGN` — tzn. backlog item → BLOCKED, WIP reset, next step = close (viz REDESIGN handling v references/dispatch-recovery.md).

### Kdy resetovat countery (explicitní)

Reset obou counterů na 0 nastává ve **dvou** situacích:
1. **Nový task**: Když fabric-loop vybere nový `wip_item` z Task Queue (tzn. změní se `state.wip_item`), přepíše `test_fail_count: 0`, `rework_count: 0` a `autofix_count: 0` v novém backlog itemu.
2. **Po úspěšném close**: Když `fabric-close` dokončí merge a gates PASS, fabric-loop resetuje countery v backlog itemu (nezávisle na tom, že task je DONE — pro audit trail).

Kdo provádí reset: **fabric-loop** (ne fabric-close, ne fabric-implement). Reset se provádí PŘED prvním dispatch na nový task, tzn. PŘED prvním implement tickem.

**Invocation point v tick algoritmu:** Counter operace se volají v kroku 6) MEZI `tick --completed` a dalším dispatch:
- Po `tick --completed "test"` → pokud next_step=implement (FAIL/TIMEOUT) → **inkrement** test_fail_count (kód níže)
- Po `tick --completed "review"` → pokud next_step=implement (REWORK) → **inkrement** rework_count (kód níže)
- Po `tick --completed "close"` → pokud next_step=implement (nový task) → **reset** obou counterů v novém wip_item (kód níže)
- Po `tick --completed "close"` → vždy → **reset** counterů v uzavřeném task (audit trail, kód níže)

### Explicitní reset kód (povinný)

**Při výběru nového tasku** (fabric-loop, před prvním implement dispatch):
```bash
# Ensure countery existují a jsou na 0 v novém backlog itemu
WIP_FILE="{WORK_ROOT}/backlog/{NEW_WIP_ITEM}.md"
if grep -q 'test_fail_count:' "$WIP_FILE"; then
  sed -i "s/^test_fail_count:.*/test_fail_count: 0/" "$WIP_FILE"
else
  # Přidej do frontmatter (před uzavírací ---)
  sed -i '/^---$/!b; N; s/\n---$/\ntest_fail_count: 0\n---/' "$WIP_FILE"
fi
if grep -q 'rework_count:' "$WIP_FILE"; then
  sed -i "s/^rework_count:.*/rework_count: 0/" "$WIP_FILE"
else
  sed -i '/^---$/!b; N; s/\n---$/\nrework_count: 0\n---/' "$WIP_FILE"
fi
if grep -q 'autofix_count:' "$WIP_FILE"; then
  sed -i "s/^autofix_count:.*/autofix_count: 0/" "$WIP_FILE"
else
  sed -i '/^---$/!b; N; s/\n---$/\nautofix_count: 0\n---/' "$WIP_FILE"
fi
```

**Po úspěšném close** (fabric-loop, po close tick):
```bash
# Reset counterů pro archivační audit trail
DONE_FILE="{WORK_ROOT}/backlog/{CLOSED_WIP_ITEM}.md"
sed -i "s/^test_fail_count:.*/test_fail_count: 0/" "$DONE_FILE" 2>/dev/null || echo "WARN: counter reset failed for test_fail_count in $DONE_FILE"
sed -i "s/^rework_count:.*/rework_count: 0/" "$DONE_FILE" 2>/dev/null || echo "WARN: counter reset failed for rework_count in $DONE_FILE"
```

**Error handling pro sed:** Pokud `sed -i` selže (permission, locked file), vypiš WARNING (zachytí run report) a pokračuj — counter na 0 je default a systém degraduje gracefully (counter check používá `${CURRENT:-0}`).

**Atomicity note:** `sed -i` není atomické (vytváří temp file + rename). Pro crash-safety:
- Preferuj `python skills/fabric-init/tools/fabric.py backlog-set --id "{wip_item}" --fields-json '{"test_fail_count": N, "rework_count": M}'` (atomic YAML write).
- Fallback: bash `sed -i` s `|| echo "WARN: ..."` je akceptabilní v single-instance mode (worst case: counter je o 1 nižší po crash → systém degraduje gracefully).
- Nikdy nepoužívej dva separátní `sed -i` pro dva countery v jednom souboru — buď jeden `sed -i` s více `-e`, nebo jeden Python call pro oba najednou.

---

## Auto-fix scope (clarifikace)

Auto-fix (`lint_fix`, `format`) se spouští **max 1× per gate per skill run**. Across rework cycles se může spustit vícekrát — to je záměr: každý implement run je čistý pokus. Celkový počet auto-fix pokusů per task je bounded `max_rework_iters` (default 3). Auto-fix nikdy neopakuje po timeoutu.

---

## Verdict parsing (kanonický formát)

`tick()` parsuje verdikty z reportů takto (vždy z **nejnovějšího** reportu podle mtime):
> **Stale report guard:** Pokud existuje více reportů pro stejný step+wip_item (z předchozích runů/rework cyklů), `tick` MUSÍ parsovat NEJNOVĚJŠÍ (ls -t | head -1). Starší reporty nesmažou se (audit trail), ale nesmí ovlivnit aktuální verdikt.
- **test report:** Hledá řádek `Result: PASS` nebo `Result: FAIL` nebo `Result: TIMEOUT` (case-insensitive). Fallback: frontmatter `result:` YAML klíč. Pokud ani jedno → error.
  - `PASS` → next step = review
  - `FAIL` → next step = implement (+ counter increment)
  - `TIMEOUT` → hodnoť jako FAIL (next step = implement, counter increment), ALE: vytvoř intake item `intake/loop-test-timeout-{wip_item}.md` s doporučením identifikovat pomalé testy. V run reportu označ jako `TIMEOUT` (odlišně od FAIL pro root cause analýzu).
- **review report:** Hledá řádek `Verdict: CLEAN|REWORK|REDESIGN` (case-insensitive). Fallback: frontmatter `verdict:` YAML klíč. Pokud ani jedno → error.
  - Pokud review report obsahuje gate výsledek `TIMEOUT` (lint/format timeout): hodnoť jako REWORK (infrastrukturní problém, ne code quality). Vytvoř intake item pokud ještě neexistuje.
- Při error (unparseable report): `state.error = "unparseable {step} report"` + STOP.

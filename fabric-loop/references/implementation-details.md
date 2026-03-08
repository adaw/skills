# Implementation Details — State Diagrams, Recovery & Concurrency

This document contains the state diagram, crash recovery algorithms, YAML recovery, manual intervention procedures, failure mode catalog, and concurrency handling from fabric-loop. See SKILL.md for the main orchestration logic.

---

## Partial State Guard

Po načtení state.md ověř přítomnost povinných polí. Chybějící pole = STOP.

```bash
# Required fields in state.md (partial state = STOP)
for FIELD in phase step sprint; do
  VALUE=$(grep "^${FIELD}:" "{WORK_ROOT}/state.md" | awk '{print $2}')
  if [ -z "$VALUE" ] || [ "$VALUE" = "null" ]; then
    echo "STOP: state.md missing required field '${FIELD}' — run fabric-init"
    python skills/fabric-init/tools/fabric.py state-patch \
      --fields-json "{\"error\":\"partial state: missing ${FIELD}\"}"
    exit 1
  fi
done
```

---

## State Diagram (textual)

```
idle ──→ vision → status → architect → process → gap → generate → intake → prio
                                                                    │
  ┌─────────────────────────────────────────────────────────────────┘
  v
sprint → analyze ──→ implement → test → review ──┐
                          ^                       │
                          │   REWORK (max 3×)     │
                          └───────────────────────┘
                                                  │ CLEAN
                                                  v
                     close → docs → check → archive → idle (loop boundary)

REDESIGN flow (explicit):
  review ──REDESIGN──→ backlog.status=BLOCKED
                     → state.wip_item=null, state.wip_branch=null
                     → if another READY task exists → implement (new task)
                     → if no READY tasks → close → docs → check → archive → idle

Error states:
  ANY_STEP ──error──→ state.error set → STOP (if intentional) or RETRY (if crash)
  RETRY ──fail──→ intake item + STOP

Counter-bounded termination:
  test FAIL:    test_fail_count++ → if >= max_rework_iters → STOP
  review REWORK: rework_count++  → if >= max_rework_iters → REDESIGN override → BLOCKED
  review REDESIGN: → task BLOCKED, WIP reset, skip to close (or next task)
```

---

## Crash Recovery Algorithm (explicitní)

```bash
# Krok 1: Načti error
STATE_ERROR=$(python skills/fabric-init/tools/fabric.py state-get --field error 2>/dev/null)
FAILED_STEP=$(python skills/fabric-init/tools/fabric.py state-get --field step 2>/dev/null)

# Krok 2: Kategorizuj (intentional vs crash)
STATE_ERROR_TRIMMED=$(echo "$STATE_ERROR" | sed 's/^[[:space:]]*//')
INTENTIONAL_PATTERN="^(BLOCKED_ONLY:|STOP:|test_fail_count exceeded|rework_count exceeded|config_drift:)"

if echo "$STATE_ERROR_TRIMMED" | grep -qE "$INTENTIONAL_PATTERN"; then
  echo "Intentional STOP — no retry, ESCALATE"
  # Zapiš do run reportu + STOP
  exit 0
fi

# Krok 3: Zkontroluj, zda výstup existuje (false alarm detection)
EXPECTED_OUTPUT=$(python skills/fabric-init/tools/fabric.py contract-check --step "$FAILED_STEP" --dry-run 2>/dev/null)
CONTRACT_EXIT=$?
if [ $CONTRACT_EXIT -eq 0 ]; then
  echo "Output exists despite error — false alarm, clearing error"
  python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"error": null}'
  # Pokračuj normálně
  exit 0
fi

# Krok 4: Retry (max 1×)
RETRY_FLAG="{WORK_ROOT}/logs/.retry-${FAILED_STEP}-$(date +%Y-%m-%d)"
if [ -f "$RETRY_FLAG" ]; then
  echo "Already retried $FAILED_STEP today — ESCALATE"
  python skills/fabric-init/tools/fabric.py evidence-pack --label "crash-${FAILED_STEP}"
  python skills/fabric-init/tools/fabric.py intake-new --source "loop" --slug "crash-retry-exhausted" \
    --title "Crash retry exhausted for ${FAILED_STEP}: ${STATE_ERROR_TRIMMED}"
  exit 1
fi
touch "$RETRY_FLAG"
echo "Retrying $FAILED_STEP (attempt 1/1)"
python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"error": null}'
# Dispatch same step again (fabric-loop tick continues normally)
```

---

## YAML Mid-Write Crash Recovery

`state.md` je kritický soubor. Pokud se zápis přeruší uprostřed (process kill, disk full):

```bash
# Na začátku každého RUN — validace state.md integrity:
python skills/fabric-init/tools/fabric.py state-read 2>/dev/null
STATE_READ_EXIT=$?
if [ $STATE_READ_EXIT -ne 0 ]; then
  echo "CRITICAL: state.md corrupted or unreadable (exit $STATE_READ_EXIT)"
  # Pokus o obnovu z posledního protokolu
  LAST_GOOD_STATE=$(grep '"event":"end"' {WORK_ROOT}/logs/protocol.jsonl 2>/dev/null | tail -1 | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('state_snapshot',''))" 2>/dev/null)
  if [ -n "$LAST_GOOD_STATE" ]; then
    echo "Restoring state.md from last protocol snapshot"
    # Atomic write: tmp → mv (nikdy přímý zápis do state.md)
    echo "$LAST_GOOD_STATE" > "{WORK_ROOT}/state.md.tmp"
    mv "{WORK_ROOT}/state.md.tmp" "{WORK_ROOT}/state.md"
    # Re-validate
    python skills/fabric-init/tools/fabric.py state-read 2>/dev/null || {
      echo "FATAL: state.md recovery failed — manual intervention required"
      exit 2
    }
  else
    echo "FATAL: no protocol snapshot available — manual intervention required"
    exit 2
  fi
fi
```

**Prevence:** `fabric.py state-patch` používá atomic write (write to temp + rename), takže k partial write dochází jen při fatálním OS/disk selhání.

---

## Manual Intervention Procedure

Pokud se orchestrátor zasekne (state.error nastavený, opakované STOP, nekonvergence):

1. **Diagnostika:**
   ```bash
   # Přečti aktuální stav
   cat {WORK_ROOT}/state.md
   # Zkontroluj posledních 10 protokolových záznamů
   tail -10 {WORK_ROOT}/logs/protocol.jsonl | python -m json.tool
   # Zkontroluj poslední reporty
   ls -lt {WORK_ROOT}/reports/ | head -10
   ```

2. **Reset error a pokračuj:**
   ```bash
   python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"error": null}'
   # Pak spusť: Načti a proveď skills/fabric-loop/SKILL.md
   ```

3. **Přeskoč zaseklý step:**
   ```bash
   # Nastav step na další v sekvenci (viz LIFECYCLE v config.md)
   python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"step": "<NEXT_STEP>", "last_completed": "<STUCK_STEP>", "error": null}'
   ```

4. **Reset celého sprintu (destruktivní):**
   ```bash
   python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"step": "idle", "phase": "idle", "wip_item": null, "wip_branch": null, "error": null, "run_id": null}'
   ```

5. **Eskalace:** Pokud nic nepomáhá, vytvořte intake item manuálně:
   ```bash
   python skills/fabric-init/tools/fabric.py intake-new --source "manual" --slug "stuck-orchestrator" \
     --title "Orchestrator stuck — manual intervention needed"
   ```

---

## Failure Mode Catalog

| Failure Mode | Detection | Recovery | Severity |
|---|---|---|---|
| Test fails repeatedly (≥max_rework_iters) | test_fail_count counter | STOP + intake item | CRITICAL |
| Review REWORK loop (≥max_rework_iters) | rework_count counter | REDESIGN override → task BLOCKED | CRITICAL |
| Merge conflict during close | git merge --squash exit ≠ 0 | Abort + carry-over + intake | HIGH |
| Branch diverged from main | merge-base ≠ main HEAD | Rebase on feature branch; if fail → carry-over | HIGH |
| Detached HEAD | git rev-parse --abbrev-ref = "HEAD" | Recovery: checkout main → recreate branch | HIGH |
| state.md corrupted (YAML unparseable) | state-read exit ≠ 0 | Restore from protocol.jsonl snapshot | CRITICAL |
| Contract-check fails | contract-check exit ≠ 0 | state.error + STOP + intake | CRITICAL |
| Auto-fix introduces regression | PRE_FIX_TEST=PASS, POST_FIX_TEST≠PASS | git checkout -- . (revert) | HIGH |
| Git fetch timeout (network) | timeout 60 exit = 124 | WARN + continue with local state | LOW |
| Governance drift (config vs snapshot) | governance-check exit ≠ 0 | intake item + continue | HIGH |
| Counter mismatch (persisted vs actual) | Cross-check in self-check | WARN in run report | HIGH |
| intake-new tool fails | intake-new exit ≠ 0 | WARN + log to run report + continue | LOW |
| Concurrent instance detected | protocol.jsonl start without end | WARN only (no lock) | LOW |
| State.error set (intentional STOP) | ERROR_TAXONOMY prefix match | No retry → intake + STOP | CRITICAL |
| State.error set (crash/failure) | No ERROR_TAXONOMY prefix | Retry 1×; if fail again → escalate + STOP | HIGH |
| Lint/format TBD in strict mode | Precondition check | intake item + FAIL | CRITICAL |

---

## Self-check Bash Scripts

### Counter Cross-check (povinné pokud wip_item existuje)

```bash
WIP_ITEM=$(grep 'wip_item:' {WORK_ROOT}/state.md | awk '{print $2}')
if [ -n "$WIP_ITEM" ] && [ "$WIP_ITEM" != "null" ]; then
  FAIL_COUNT=$(grep 'test_fail_count:' {WORK_ROOT}/backlog/$WIP_ITEM.md | awk '{print $2}')
  REWORK_COUNT=$(grep 'rework_count:' {WORK_ROOT}/backlog/$WIP_ITEM.md | awk '{print $2}')
  # Spočítej skutečné FAIL reporty
  ACTUAL_FAILS=$(ls {WORK_ROOT}/reports/test-$WIP_ITEM-*.md 2>/dev/null | while read f; do grep -l 'Result: FAIL\|Result: TIMEOUT' "$f"; done | wc -l)
  ACTUAL_REWORKS=$(ls {WORK_ROOT}/reports/review-$WIP_ITEM-*.md 2>/dev/null | while read f; do grep -l 'Verdict: REWORK' "$f"; done | wc -l)
  if [ "${FAIL_COUNT:-0}" -ne "$ACTUAL_FAILS" ] || [ "${REWORK_COUNT:-0}" -ne "$ACTUAL_REWORKS" ]; then
    echo "WARN: counter mismatch — test_fail_count=$FAIL_COUNT (actual $ACTUAL_FAILS), rework_count=$REWORK_COUNT (actual $ACTUAL_REWORKS)"
    # Non-blocking WARNING — counter drift je recoverable (graceful degradation)
  fi
fi
```

### Autofix Counter Cross-check

```bash
if [ -n "$WIP_ITEM" ] && [ "$WIP_ITEM" != "null" ]; then
  AUTOFIX_COUNT=$(grep 'autofix_count:' {WORK_ROOT}/backlog/$WIP_ITEM.md | awk '{print $2}')
  AUTOFIX_COUNT=${AUTOFIX_COUNT:-0}
  if ! echo "$AUTOFIX_COUNT" | grep -qE '^[0-9]+$'; then AUTOFIX_COUNT=0; echo "WARN: non-numeric autofix_count, treating as 0"; fi
  # Spočítej skutečné auto-fix commity na branchi
  ACTUAL_AUTOFIX=$(git log --oneline --grep="chore.*auto-fix" {main_branch}..HEAD 2>/dev/null | wc -l)
  if [ "${AUTOFIX_COUNT}" -ne "$ACTUAL_AUTOFIX" ]; then
    echo "WARN: autofix_count mismatch — persisted=$AUTOFIX_COUNT, actual=$ACTUAL_AUTOFIX"
  fi
fi
```

### Cross-sprint Prio Staleness Check

```bash
# Po close, pokud existují carry-over tasks
SPRINT_N=$(grep 'sprint:' {WORK_ROOT}/state.md | awk '{print $2}')
for ITEM_FILE in {WORK_ROOT}/backlog/*.md; do
  ITEM_STATUS=$(grep 'status:' "$ITEM_FILE" | head -1 | awk '{print $2}')
  if [ "$ITEM_STATUS" != "DONE" ] && [ "$ITEM_STATUS" != "BLOCKED" ]; then
    ITEM_UPDATED=$(grep 'updated:' "$ITEM_FILE" | awk '{print $2}')
    SPRINT_STARTED=$(grep 'sprint_started:' {WORK_ROOT}/state.md | awk '{print $2}')
    if [ -n "$SPRINT_STARTED" ] && [ "$ITEM_UPDATED" \< "$SPRINT_STARTED" ]; then
      echo "WARN: backlog item $(basename $ITEM_FILE) has stale prio (updated=$ITEM_UPDATED, sprint started=$SPRINT_STARTED)"
    fi
  fi
done
```

---

## Concurrency (single-instance assumption)

Fabric-loop předpokládá **single-instance** operaci — v jednu chvíli smí běžet **nejvýše jeden** orchestrátor pro daný `{WORK_ROOT}`. Concurrent přístup není podporován a způsobí:
- race conditions na `state.md` (dva loopy přepisují step/wip)
- dvojitý merge do main (data corruption)
- counter inkonsistence (test_fail_count / rework_count)

**Detekce (best-effort):** Na začátku RUN zkontroluj `{WORK_ROOT}/logs/protocol.jsonl` — pokud poslední záznam je `event: start` pro `fabric-loop` BEZ odpovídajícího `event: end` a `last_tick_at` je < 10 minut → zaloguj WARNING „possible concurrent instance" do run reportu. Toto NENÍ lock — pouze upozornění.

**Prevence:** Leží na uživateli / CI — nespouštět dva RUN cykly současně.

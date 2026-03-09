---
name: fabric-loop
description: "Orchestrate full Fabric lifecycle as file-driven state machine. Reads config.md and state.md, dispatches next skill, validates outputs, advances state, and performs crash recovery. Single entrypoint for agent via RUN command."
---

# FABRIC-LOOP — Orchestrátor (RUN)
## Účel
`fabric-loop` je **jediný dispatcher**. Dostaneš příkaz `RUN` a:
1) načteš `config.md` (cesty, příkazy, kontrakty),
2) načteš `state.md` (kde jsme),
3) rozhodneš **další krok**,
4) spustíš příslušný skill,
5) ověříš výstupy,
6) posuneš `state.md` a pokračuješ dál.



## Spuštění (1 věta + volitelný limit)
Uživatel má mít **minimální prompt**. Standardní spuštění je:

- `Načti a proveď skills/fabric-loop/SKILL.md`

Volitelně může uživatel přidat parametry:

- `Načti a proveď skills/fabric-loop/SKILL.md loop=10`
- `Načti a proveď skills/fabric-loop/SKILL.md loop=auto`
- `Načti a proveď skills/fabric-loop/SKILL.md goal=mvp`
- `Načti a proveď skills/fabric-loop/SKILL.md goal=t1`
- `Načti a proveď skills/fabric-loop/SKILL.md goal=release`
- `Načti a proveď skills/fabric-loop/SKILL.md audit=1`
- `Načti a proveď skills/fabric-loop/SKILL.md loop=auto goal=mvp audit=1`

### Semantika
Chování je vždy stejné: pokud je stav `idle`, provede se idle tick (detekce práce). Pokud práce existuje, sprint začne. Pokud ne, skonči. Rozdíl mezi `loop=<N>` a `loop=auto` je **jen v MAX_LOOPS**.

- `loop=<N>` = maximální počet orchestrátor **loopů** v rámci tohoto spuštění.
  - 1 loop = opakuj orchestrátor ticků, dokud nenastane **loop boundary**:
    - `COMPLETED_STEP == "archive"` (sprint uzavřen), nebo
    - `state.step == "idle"` a idle tick potvrdí, že není práce, nebo
    - STOP/CRITICAL (např. `state.error`, kontrakt breach).
  - Default: `loop=1` (= 1 sprint).
  - Limit: `N` omez na rozsah **1–50** (cokoliv mimo clampni na nejbližší mez).

- `loop=auto` = „běž, dokud je co dělat":
  - totéž co `loop=N`, ale `MAX_LOOPS` je high-cap (default `100`, lze přepsat v `config.md` jako `RUN.auto_max_loops`).
  - jakmile dojde práce a idle tick potvrdí `idle`, skonči (OK).

- `goal=<...>` = **done-condition / scope** pro `loop=auto` i pro work‑status.
  - Goal říká, které backlog items se počítají jako „zbývající práce" (tier filter).
  - Goal se mapuje na `tier_max` přes `{WORK_ROOT}/config.md` (`RUN.goals`).
  - Pokud uživatel goal neuvede, použij `RUN.default_goal` (default `release`).
  - Přijímané hodnoty: `mvp|t1|release` (typicky) nebo přímo `T0|T1|T2|T3`.
  - Semantika: „hotovo" = **žádný pending intake** a **žádná backlog práce / blokéry do `tier_max`**.

- `audit=<0|1>` = zapne **provozní audit** po každém ticku.
  - `audit=1` vytvoří audit report pro každý provedený skill a může loop zastavit při CRITICAL zjištění.
  - Default: `audit=0`.

### Parsování
V uživatelském triggeru (promptu) hledej tyto tokeny (case-insensitive). Pokud existuje více výskytů, vezmi **první**:

- `loop=<...>` → řídí počet loopů (`MAX_LOOPS`)
- `goal=<...>` → řídí goal/tier scope (viz výše)
- `audit=<...>` → 0/1 (nebo jen `audit` jako synonymum pro `audit=1`)


- pokud je hodnota `auto` → `MAX_LOOPS = RUN.auto_max_loops` (default `100`)
- jinak parsuj jako integer → `MAX_LOOPS=<N>` (clamp 1–50)

**Stop dřív než vyčerpáš limit, pokud nastane STOP/CRITICAL** (např. `state.error`, kontrakt breach, missing config/commands). Skonči také, když se systém dostane do `state.step=idle` a idle tick potvrdí, že není práce.

#### Explicitní parsovací kód (povinný)

```bash
# Parsuj parametry z user promptu (case-insensitive)
USER_PROMPT="$1"

# LOOP parameter
LOOP_RAW=$(echo "$USER_PROMPT" | grep -oiE 'loop=[a-z0-9]+' | head -1 | cut -d= -f2)
if [ -z "$LOOP_RAW" ]; then
  MAX_LOOPS=1
elif echo "$LOOP_RAW" | grep -qiE '^auto$'; then
  MAX_LOOPS=100  # hard cap from config RUN.auto_max_loops
elif echo "$LOOP_RAW" | grep -qE '^[0-9]+$'; then
  MAX_LOOPS=$LOOP_RAW
  # Clamp to [1, 50]
  [ "$MAX_LOOPS" -lt 1 ] && MAX_LOOPS=1
  [ "$MAX_LOOPS" -gt 50 ] && MAX_LOOPS=50
else
  echo "WARN: invalid loop value '$LOOP_RAW', using default loop=1"
  MAX_LOOPS=1
fi

# TIMEOUT parameter: max seconds per dispatched skill (from config or default)
SKILL_TIMEOUT=$(grep 'RUN.skill_timeout:' "{WORK_ROOT}/config.md" | awk '{print $2}' 2>/dev/null)
SKILL_TIMEOUT=${SKILL_TIMEOUT:-600}
if ! echo "$SKILL_TIMEOUT" | grep -qE '^[0-9]+$'; then SKILL_TIMEOUT=600; fi

# GOAL parameter
GOAL_RAW=$(echo "$USER_PROMPT" | grep -oiE 'goal=[a-z0-9]+' | head -1 | cut -d= -f2)
if [ -z "$GOAL_RAW" ]; then
  GOAL="release"  # default from config RUN.default_goal
elif echo "$GOAL_RAW" | grep -qiE '^(mvp|t1|release|T[0-3])$'; then
  GOAL=$(echo "$GOAL_RAW" | tr 'A-Z' 'a-z')
else
  echo "WARN: unknown goal '$GOAL_RAW', falling back to 'release'"
  GOAL="release"
fi

# AUDIT parameter
AUDIT_RAW=$(echo "$USER_PROMPT" | grep -oiE 'audit(=[a-z0-9]+)?' | head -1)
if echo "$AUDIT_RAW" | grep -qiE '(=1|=true|=yes|=on|^audit$)'; then
  AUDIT=1
else
  AUDIT=0
fi
```

#### GOAL (tier scope)
- Pokud token `goal=<...>` chybí, použij `RUN.default_goal` z configu (default `release`).
- Pokud goal neexistuje v `RUN.goals` a zároveň není ve tvaru `T<digit>`, považuj ho za `release` (no filter) a zaloguj warning do run reportu.

#### AUDIT (provozní audit)
- `audit=1|true|yes|on` nebo samotný token `audit` → `AUDIT=1`.
- Cokoliv jiného / chybí → `AUDIT=0`.

## Idle režim (state.step=idle)
`idle` je **sentinel step** znamenající: „momentálně není žádná akční práce".
Nejde o lifecycle krok; `idle` používá pouze `fabric-loop` jako **stop marker** a jako „sleep state".

### Deterministická detekce práce (povinné)
K detekci práce nepoužívej heuristiky ani ruční procházení stovek souborů.

Preferovaná cesta je **`tick` bez `--completed`**, který udělá work‑status + patch stavu deterministicky:

```bash
python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}
```

Pro debugging / evidence můžeš volat i samostatný `work-status`:

```bash
python skills/fabric-init/tools/fabric.py work-status {GOAL_ARG} --json-out "{WORK_ROOT}/reports/work-status.json"
```

Výstup (JSON) obsahuje `status`:

- `work` = existuje práce (pending intake a/nebo backlog práce mimo DONE/BLOCKED)
- `blocked` = backlog existuje, ale všechno je BLOCKED (vyžaduje člověka)
- `none` = nic k práci (žádný intake, žádná backlog práce)

### Chování při `idle`
Když `state.step == "idle"` na začátku ticku (platí pro **jakýkoliv** `loop=` režim):

1) zavolej `tick` bez `--completed`:

```bash
python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}
```

2) znovu načti `state.md`:
   - pokud je stále `idle` → zaloguj "no work, idle" a skonči (OK)
   - pokud `state.error != null` → STOP + ESCALATE
   - jinak pokračuj v loopu (nový sprint začíná).

### Kdy nastavovat `idle`
`idle` je nastavený deterministicky přes `tick`:
- po `prio` (auto guard): pokud není práce → `idle`
- po `archive` (auto guard): pokud není práce → `idle`



### Blocker escalation (deterministické)
> **Preferovaně:** tohle typicky udělá deterministicky `python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}`.
> Vygeneruje `reports/blocker-*.md` a nastaví `state.error = "BLOCKED_ONLY: see ..."`.
> V takovém případě už jen **ESCALATE** s odkazem na report.

Manuální postup použij jen když:
- `tick` nebyl použit (nebo běžíš mimo loop), nebo
- chceš report doplnit o hlubší kontext / rozhodnutí.

Pokud `work-status.status == "blocked"`: backlog existuje, ale **všechno je BLOCKED** → autonomně nemůžeš pokračovat.

Manuální minimum (jen když není blocker report z `tick`):

1) Snapshot evidence:
```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan.json"
```
2) Vytvoř/aktualizuj 1 blocker report v `{WORK_ROOT}/reports/`.
3) Nastav `state.error = "BLOCKED_ONLY: see <path>"` a **STOP**.

## Downstream Contract

**Kdo konzumuje výstupy fabric-loop a jaká pole čte:**

- **Všechny fabric skills** read:
  - `state.md` fields: `phase`, `step`, `sprint`, `wip_item`, `error`, `loop_count`
  - `state.md` field `completed_step` — signalizuje, který step právě skončil

- **fabric-prio** reads:
  - `state.sprint` → aktuální číslo sprintu pro scheduling
  - `state.wip_item` → ověřuje, zda není konflikt s WIP limitem

- **fabric-sprint** reads:
  - `state.sprint` → inkrementuje číslo sprintu
  - `state.phase` → ověřuje, že jsme v planning fázi

- **fabric-implement** reads:
  - `state.wip_item` → aktuální task k implementaci
  - `state.wip_branch` → branch pro commit

- **fabric-archive** reads:
  - `state.sprint` → číslo sprintu pro archivaci
  - `state.phase` → ověřuje closing fázi
  - `state.completed_step` → kontroluje, že všechny předchozí kroky proběhly

**Invariant:** Loop NIKDY nemodifikuje state.md přímo. Pouze volá `state-patch` s explicitním diff. Každý patch je atomický a logovaný v protocol_log.

## Protokol (povinné)
Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-loop" --event start --message "run window" --data '{"max_loops": <MAX_LOOPS>, "max_ticks_per_loop": <MAX_TICKS_PER_LOOP>, "goal": "<GOAL>", "audit": <AUDIT>}'`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-loop" --event end --status OK --report "{WORK_ROOT}/reports/run-{run_id}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


---

## Preconditions (K6 — povinná validace před spuštěním)

```bash
# --- fabric-loop preconditions ---
# P1: config.md musí existovat (discovery najde, ale validuj výsledek)
if [ -z "$CONFIG_PATH" ] || [ ! -f "$CONFIG_PATH" ]; then
  echo "STOP: config.md not found — run fabric-init first"
  exit 1
fi

# P2: WORK_ROOT musí být nastavený a existovat
WORK_ROOT=$(grep 'WORK_ROOT:' "$CONFIG_PATH" | awk '{print $2}' | tr -d '"')
if [ -z "$WORK_ROOT" ] || [ ! -d "$WORK_ROOT" ]; then
  echo "STOP: WORK_ROOT '$WORK_ROOT' not found or not set in config.md"
  exit 1
fi

# P3: state.md musí existovat (nebo bootstrap přes init)
# NOTE: WARN (not STOP) is intentional — loop auto-bootstraps via fabric-init
# If state.md is missing, loop dispatches fabric-init which creates it.
# This is the ONLY precondition that uses WARN because loop IS the bootstrap trigger.
if [ ! -f "$WORK_ROOT/state.md" ]; then
  echo "WARN: state.md missing — triggering fabric-init bootstrap"
fi

# P4: skills adresář musí existovat
SKILLS_ROOT=$(grep 'SKILLS_ROOT:' "$CONFIG_PATH" | awk '{print $2}' | tr -d '"')
if [ -z "$SKILLS_ROOT" ] || [ ! -d "$SKILLS_ROOT" ]; then
  echo "STOP: SKILLS_ROOT '$SKILLS_ROOT' not found"
  exit 1
fi

# P5: fabric.py tool musí být dostupný
if [ ! -f "$SKILLS_ROOT/fabric-init/tools/fabric.py" ]; then
  echo "STOP: fabric.py tool not found at $SKILLS_ROOT/fabric-init/tools/fabric.py"
  exit 1
fi

# P6: validate_fabric.py musí být dostupný
if [ ! -f "$SKILLS_ROOT/fabric-init/tools/validate_fabric.py" ]; then
  echo "STOP: validate_fabric.py not found"
  exit 1
fi
# P7: READ references/tick-algorithm.md NOW (contains exact CLI commands for contract-check, tick, run-report, audit)
```

## Input Validation (K7 — path traversal ochrana)

```bash
# validate_path: odmítne cesty obsahující ".." nebo absolutní cesty mimo WORK_ROOT
validate_path() {
  local path="$1"
  local context="$2"
  if echo "$path" | grep -qE '(\.\./|/\.\.)'; then
    echo "STOP: path traversal detected in $context: '$path'"
    return 1
  fi
  # Ověř že cesta je pod WORK_ROOT (pro runtime cesty)
  local resolved
  resolved=$(realpath -m "$path" 2>/dev/null)
  local work_resolved
  work_resolved=$(realpath -m "$WORK_ROOT" 2>/dev/null)
  if [ -n "$resolved" ] && [ -n "$work_resolved" ]; then
    case "$resolved" in
      "$work_resolved"*) return 0 ;;
      *) echo "WARN: path '$path' ($context) resolves outside WORK_ROOT"; return 1 ;;
    esac
  fi
  return 0
}

# Validuj wip_item (pochází ze state.md, může být manipulován)
WIP_ITEM=$(grep 'wip_item:' "$WORK_ROOT/state.md" 2>/dev/null | awk '{print $2}')
if [ -n "$WIP_ITEM" ] && [ "$WIP_ITEM" != "null" ]; then
  validate_path "$WORK_ROOT/backlog/$WIP_ITEM.md" "wip_item" || {
    echo "STOP: invalid wip_item path"
    exit 1
  }
fi
```

## Nevyjednatelné zásady
1. **Config-first:** Každý běh začíná čtením `{WORK_ROOT}/config.md`. Hardcoded cesty/příkazy jsou bug.
2. **File-only orchestration:** Skills spolu komunikují jen přes soubory. Žádné „volání skillu ze skillu".
3. **WIP=1:** Implementace běží vždy jen pro jeden task najednou (viz `SPRINT.wip_limit`).
4. **State ownership:** `fabric-loop` vlastní `phase/step/history`. Skills nesmí svévolně přeskakovat kroky.
5. **Fail fast:** Chybí-li povinný vstup/výstup, zapiš `state.error` a skonči.

---

## Vstupy
Povinné:
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md` *(pokud chybí, bootstrap přes `fabric-init`)*
- `{WORK_ROOT}/vision.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/` (flat items)

---

## Partial State Guard

Po načtení state.md ověř povinná pole (`phase`, `step`, `sprint`). Chybějící → STOP + `state.error`.
Bash implementace viz `references/implementation-details.md` sekce "Partial State Guard".

---

## Bootstrap (první RUN)

> Detailní postup: `references/dispatch-recovery.md` sekce Bootstrap.

Přehled: Najdi config.md → 0=auto-init, 1=použij, >1=nejkratší cesta → ověř artefakty → chybí=fabric-init
4. `fabric.py run-start` + `fabric.py run-report --ensure-run-id`

---

## Hlavní lifecycle (deterministický)
### Kanonická sekvence (z config.md)
```
FÁZE 0: ORIENTACE
  vision → status → architect → process → gap → generate → intake → prio

FÁZE 1: PLÁNOVÁNÍ
  design → sprint → analyze

FÁZE 2: IMPLEMENTACE (WIP=1, per task)
  implement → test → review (→ případně rework loop)

FÁZE 3: UZAVŘENÍ
  close → docs → check → archive
```

### Kontrakt s `{WORK_ROOT}/config.md` (LIFECYCLE)
- Pokud config obsahuje YAML blok `LIFECYCLE`, musí odpovídat této tabulce „next step".
- Pokud se liší (drift) → **STOP** + intake item + `state.error` set
- Detekce: porovnání config LIFECYCLE steps vs kanonická sekvence (bash viz `references/dispatch-recovery.md` "Drift Detection")

---


## Okno běhu (loop window)
Na začátku běhu urč `MAX_LOOPS` a `MAX_TICKS_PER_LOOP` podle parametru `loop=<...>`

Dále urč `GOAL` (`goal=<...>` nebo `RUN.default_goal`, default `release`) a podle `RUN.*`:

- pokud parametr **není**: `MAX_LOOPS = 1`
- pokud `loop=<N>`: `MAX_LOOPS = clamp(N, 1–50)`
- pokud `loop=auto`: `MAX_LOOPS = RUN.auto_max_loops` (default `100`)

Chování je vždy stejné: idle tick se provede, a pokud je práce, sprint začne. Rozdíl je **jen v MAX_LOOPS** — kolik sprintů maximálně proběhne.

`MAX_TICKS_PER_LOOP` je safety cap proti nekonečným smyčkám, ale **nesmí být tak nízký, aby usekl reálnou práci**.

Použij tento deterministický výpočet (bez heuristik):
- `BASE = RUN.max_ticks_per_loop` (default `25`)
- `EST = len(LIFECYCLE.steps) + (SPRINT.max_tasks * 3 * (1 + SPRINT.max_rework_iters))`
  - `3` je implement → test → review pro 1 task
  - rework iterace přidává další cyklus implement/test/review
- `AUTO_MIN = 2 * EST` (**100% rezerva**)
- pokud `loop=auto`: `MAX_TICKS_PER_LOOP = clamp(max(BASE, AUTO_MIN), 25..1000)`
- pokud `loop=<N>`: `MAX_TICKS_PER_LOOP = clamp(BASE, 1..1000)`

Pak proveď nejvýše `MAX_LOOPS` loopů. Každý loop obsahuje 1+ ticků (dispatchů) až do loop boundary.

> **POVINNÉ: PŘED prvním tickem přečti `references/tick-algorithm.md`** (obsahuje přesné CLI příkazy pro contract-check, tick --completed, run-report, audit). Bez toho budeš hádat CLI syntax a chybovat. Dále: `references/dispatch-recovery.md` (dispatch, crash recovery), `references/metadata.md` (§12 metadata).

## Výstup orchestrátoru
Na konci každého RUN cyklu:
- `state.md` je aktualizovaný a konzistentní
- `{WORK_ROOT}/reports/run-{run_id}.md` existuje s `schema: fabric.report.v1` frontmatter (kind: run-report)
- per-tick audit reporty mají `schema: fabric.audit.v1` frontmatter (kind: audit-{step})
- pokud došlo k chybě, existuje intake item s reprodukovatelným popisem

---

## K10 — Concrete Example & Anti-patterns

### Example: Tick #3 — Dispatch fabric-implement, Check Exit

```
Loop iteration #3:
  Loop boundary check: MAX_LOOPS=auto (100), current loop=3
  Idle state check: state.step != idle → proceed

  Tick #3.1 — State read:
    phase=implementation, step=implement, sprint=2, wip_item=b015
    Work status check: pending intake=0, backlog=1 (b015 status=IN_PROGRESS)
    Exit condition? goal=release, tier_max=T3 → work remains

  Tick #3.2 — Dispatch fabric-implement:
    DISPATCH: skills/fabric-implement/SKILL.md
    WIP=1, task=b015 checked, branch=feat/b015 exists
    Preconditions PASS

  Tick #3.3 — Skill execution:
    RUNNING: fabric-implement (timeout=${SKILL_TIMEOUT}s)
    Result: PASS, report created, status→IN_REVIEW, rework_count=0
    Duration: 142s (within timeout)

  Tick #3.4 — Output validation:
    Report exists: reports/implement-b015-2026-03-07-run42.md ✓
    Backlog updated: status=IN_REVIEW ✓
    Branch: feat/b015, 1 commit ✓
    Next step: dispatch fabric-test

  Current state AFTER tick #3:
    step: test (advanced by dispatcher)
    wip_item: b015 (stays)
    wip_branch: feat/b015 (stays)
    completed_step: implement (recorded)
```

### Anti-patterns (FORBIDDEN detection & prevention)

```bash
# A1: Dispatch same skill twice WITHOUT checking result
# DETECTION: Dispatcher runs fabric-implement, but DOES NOT read report
# FIX: After dispatch, MUST read {WORK_ROOT}/reports/implement-*.md
#      and validate status field before next dispatch
IMPL_REPORT=$(ls -t "{WORK_ROOT}"/reports/implement-${WIP_ITEM}-*.md 2>/dev/null | head -1)
if [ -z "$IMPL_REPORT" ]; then
  echo "STOP: implement report missing — cannot advance state"
  exit 1
fi

# A2: Not checking exit condition for loop=auto
# DETECTION: Loop continues despite no pending work
# FIX: Before each tick, call `fabric.py work-status` and respect result
WORK_STATUS=$(python skills/fabric-init/tools/fabric.py work-status --json-out /tmp/ws.json)
if grep -q '"status": "none"' /tmp/ws.json; then
  echo "No work remaining (goal=$GOAL) — LOOP BOUNDARY"
  exit 0  # OK, not error
fi

# A3: Modifying state.md directly instead of via state-patch
# DETECTION: Grep for `phase:` or `step:` edits in loop code
# FIX: Use ONLY `fabric.py state-patch --fields-json '{...}'`
# WRONG:
  # sed -i 's/step: implement/step: test/' state.md
# RIGHT:
  # python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"step":"test"}'
```

---

## Self-check

Před návratem (po posledním tiku RUN cyklu):
- `state.md` je konzistentní: `step` odpovídá poslednímu dispatchnutému skillu, `error` je null (nebo vyplněný s popisem)
- `state.last_completed` odpovídá poslednímu úspěšně dokončenému kroku
- run report existuje v `{WORK_ROOT}/reports/run-{run_id}.md`
- žádný infinite loop: počet tiků ≤ `MAX_LOOPS × steps_per_loop` (typicky ≤ 50)
- po-dispatch kontrakt splněn pro každý dispatchnutý krok (minimální výstupy ověřeny)
- pokud došlo k REDESIGN → backlog item je BLOCKED a WIP resetován
- pokud `AUDIT=1` → pro každý dispatchnutý krok existuje audit report `reports/audit-{step}-*.md`
- countery (`test_fail_count`, `rework_count`, `autofix_count`) odpovídají skutečným počtům
- cross-sprint prio invariant: carry-over tasks mají stale prio → WARNING

> **Detailní bash skripty pro counter cross-check, autofix verification a prio staleness check:** viz `references/implementation-details.md`

Pokud ne → FAIL + zapiš `state.error` s detailním popisem a STOP.

## Concurrency

**Single-instance only** — jeden orchestrátor pro daný `{WORK_ROOT}`. Concurrent = race conditions + data corruption.

> **Detailní implementace (concurrency detection, crash recovery, state diagrams):** viz `references/implementation-details.md`

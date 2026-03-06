---
name: fabric-loop
description: "Orchestrates the full Fabric lifecycle as a file-driven state machine. Reads config.md + state.md, dispatches the next skill, validates outputs, advances state, and performs crash recovery. Single entrypoint for the agent via RUN."
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
- `loop=<N>` = maximální počet orchestrátor **loopů** v rámci tohoto spuštění.
  - 1 loop = opakuj orchestrátor ticků, dokud nenastane **loop boundary**:
    - `COMPLETED_STEP == "archive"` (sprint uzavřen), nebo
    - `state.step == "idle"` (není práce), nebo
    - STOP/CRITICAL (např. `state.error`, kontrakt breach).
  - Default: `loop=1`.
  - Limit: `N` omez na rozsah **1–50** (cokoliv mimo clampni na nejbližší mez).

- `loop=auto` = „běž, dokud je co dělat“:
  - opakuj loopy, dokud **existuje práce** (pending intake / backlog práce / WIP), a dokud nenastane STOP/CRITICAL,
  - jakmile dojde práce, nastav `state.step=idle` a skonči,
  - vždy s hard-capem `AUTO_MAX_LOOPS` (default `100`, lze přepsat v `config.md` jako `RUN.auto_max_loops`).

- `goal=<...>` = **done-condition / scope** pro `loop=auto` i pro work‑status.
  - Goal říká, které backlog items se počítají jako „zbývající práce“ (tier filter).
  - Goal se mapuje na `tier_max` přes `{WORK_ROOT}/config.md` (`RUN.goals`).
  - Pokud uživatel goal neuvede, použij `RUN.default_goal` (default `release`).
  - Přijímané hodnoty: `mvp|t1|release` (typicky) nebo přímo `T0|T1|T2|T3`.
  - Semantika: „hotovo“ = **žádný pending intake** a **žádná backlog práce / blokéry do `tier_max`**.

- `audit=<0|1>` = zapne **provozní audit** po každém ticku.
  - `audit=1` vytvoří audit report pro každý provedený skill a může loop zastavit při CRITICAL zjištění.
  - Default: `audit=0`.

### Parsování
V uživatelském triggeru (promptu) hledej tyto tokeny (case-insensitive). Pokud existuje více výskytů, vezmi **první**:

- `loop=<...>` → řídí počet loopů a `RUN_MODE`
- `goal=<...>` → řídí goal/tier scope (viz výše)
- `audit=<...>` → 0/1 (nebo jen `audit` jako synonymum pro `audit=1`)


- pokud je hodnota `auto` → `RUN_MODE=auto`
- jinak parsuj jako integer → `RUN_MODE=fixed`, `MAX_LOOPS=<N>`

**Stop dřív než vyčerpáš limit, pokud nastane STOP/CRITICAL** (např. `state.error`, kontrakt breach, missing config/commands). V režimu `loop=auto` skonči také tehdy, když se systém dostane do `state.step=idle`.

#### Explicitní parsovací kód (povinný)

```bash
# Parsuj parametry z user promptu (case-insensitive)
USER_PROMPT="$1"

# LOOP parameter
LOOP_RAW=$(echo "$USER_PROMPT" | grep -oiE 'loop=[a-z0-9]+' | head -1 | cut -d= -f2)
if [ -z "$LOOP_RAW" ]; then
  MAX_LOOPS=1; RUN_MODE="fixed"
elif echo "$LOOP_RAW" | grep -qiE '^auto$'; then
  MAX_LOOPS=100; RUN_MODE="auto"  # hard cap from config RUN.auto_max_loops
elif echo "$LOOP_RAW" | grep -qE '^[0-9]+$'; then
  MAX_LOOPS=$LOOP_RAW
  # Clamp to [1, 50]
  [ "$MAX_LOOPS" -lt 1 ] && MAX_LOOPS=1
  [ "$MAX_LOOPS" -gt 50 ] && MAX_LOOPS=50
  RUN_MODE="fixed"
else
  echo "WARN: invalid loop value '$LOOP_RAW', using default loop=1"
  MAX_LOOPS=1; RUN_MODE="fixed"
fi

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
`idle` je **sentinel step** znamenající: „momentálně není žádná akční práce“.  
Nejde o lifecycle krok; `idle` používá pouze `fabric-loop` jako **stop marker** a jako „sleep state“.

### Deterministická detekce práce (povinné pro auto)
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
Když `state.step == "idle"` na začátku spuštění v `loop=auto`:

1) zavolej `tick` bez `--completed`:

```bash
python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}
```

2) znovu načti `state.md`:
   - pokud je stále `idle` → zaloguj “still idle” a skonči (OK)
   - pokud `state.error != null` → STOP + ESCALATE
   - jinak pokračuj v loopu.

### Kdy nastavovat `idle` (auto)
V režimu `loop=auto` je `idle` nastavený deterministicky přes `tick`:
- po `prio` (auto guard): pokud není práce → `idle`
- po `archive` (auto guard): pokud není práce → `idle`



### Blocker escalation (deterministické)
> **Preferovaně:** v `loop=auto` tohle typicky udělá deterministicky `python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}`.
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
2. **File-only orchestration:** Skills spolu komunikují jen přes soubory. Žádné „volání skillu ze skillu“.
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

## Bootstrap (první RUN na projektu)
> Před tím, než začneš cokoliv dispatchovat, validuj framework (skills) a po bootstrapu validuj i workspace:
> 
> - Framework preflight:
>   ```bash
>   python skills/fabric-init/tools/validate_fabric.py
>   ```
> - Workspace preflight (po initu):
>   ```bash
>   python skills/fabric-init/tools/validate_fabric.py --workspace --runnable
>   ```
> Pokud validátor selže → **STOP** (bezpečnostní gate).



### 1) Najdi a načti config (discovery bez hardcoded rootů)
Cíl: nejdřív najít **jediný** `config.md`, který odpovídá Fabric formátu, a teprve pak z něj převzít `{WORK_ROOT}` a ostatní cesty.

1. Najdi kandidáty (deterministicky):
   - pokud je repo Git, zkus nejdřív tracked soubory:
     ```bash
     git ls-files | grep -E '(^|/)config\.md$'
     ```
     Pokud to vrátí 0 výsledků (config může být untracked), použij fallback:
     ```bash
     find . -maxdepth 6 -type f -name "config.md"
     ```
   - pokud Git není k dispozici, použij:
     ```bash
     find . -maxdepth 6 -type f -name "config.md"
     ```

2. Kandidáty **filtrovat podle obsahu** (musí platit obě):
   - obsahuje YAML blok s klíči `WORK_ROOT:` a `CODE_ROOT:`
   - obsahuje YAML blok `COMMANDS:` (aby to nebyl náhodný `config.md`)

3. Rozhodnutí:
   - **0 match** → pokus o **auto-bootstrap** (bez lidské práce):
     1) Předpokládej default `WORK_ROOT` dle šablony `skills/fabric-init/assets/config.template.md` (YAML klíč `WORK_ROOT`) a ověř, že tento adresář lze vytvořit.
     2) Načti a proveď `skills/fabric-init/SKILL.md` (ten vytvoří `{WORK_ROOT}/config.md` ze šablony).
     3) Po `fabric-init` znovu spusť discovery (kroky 1–4).
     4) Pokud ani poté config stále není validní → **STOP** a vytvoř `./bootstrap-missing-config.md`
        (uvedení kandidátů + jak vytvořit/doplnit config).
   - **1 match** → použij jako `CONFIG_PATH`.
   - **>1 match** → zvol deterministicky „nejkratší cesta, pak lexicograficky“ jako `CONFIG_PATH`,
     vytvoř `./bootstrap-multiple-configs.md` (se seznamem) a pokračuj.

4. Načti config z `CONFIG_PATH` a parsuj YAML bloky: paths (`WORK_ROOT`…), `COMMANDS`, `GIT`, `SPRINT`.

Po parsingu ověř invariant:
- soubor `{WORK_ROOT}/config.md` existuje (ostatní skills ho budou číst přes `{WORK_ROOT}`)

Pokud invariant neplatí → **STOP** + `./bootstrap-config-not-in-work-root.md` (popiš jak to opravit: přesuň config do work root nebo sjednoť `WORK_ROOT`).
   Pokud YAML nejde parsovat → **STOP** + `./bootstrap-invalid-config.md`.

> Dokud neznáš `WORK_ROOT`, **nezapisuj** do `{WORK_ROOT}/…` (bootstrap soubory piš do repo root `./bootstrap-*.md`).

### 2) Rozhodni, zda je potřeba init
Init je potřeba, pokud chybí některý z kritických artefaktů:

- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/vision.md`
- `{WORK_ROOT}/backlog.md`
- `{WORK_ROOT}/backlog/`
- `{WORK_ROOT}/templates/`
- `{WORK_ROOT}/intake/`
- `{WORK_ROOT}/intake/rejected/`
- `{WORK_ROOT}/reports/`
- `{WORK_ROOT}/sprints/`
- `{WORK_ROOT}/analyses/`
- `{WORK_ROOT}/archive/`
- `{VISIONS_ROOT}/`

Pokud něco chybí → spusť `fabric-init` (idempotentní) a po dokončení pokračuj znovu `RUN`.

Po bootstrapu (a před prvním dispatch krokem) spusť deterministicky:

```bash
python skills/fabric-init/tools/fabric.py run-start
```

Vytvoř také run report `{WORK_ROOT}/reports/run-{RUN_ID}.md` (doporučeno přes tool):

```bash
python skills/fabric-init/tools/fabric.py run-report --ensure-run-id
```

Do run reportu vyplň minimálně:
- `skill: fabric-loop`
- `run_id`
- Summary: proč běžíme (trigger), co je očekávaný výstup
- Inputs: `state.md`, `config.md`

Během běhu do reportu průběžně doplň:
- jaké kroky byly dispatchnuty
- odkazy na reporty jednotlivých skillů
- výsledný stav (`phase/step/wip_item`).



---

## Hlavní lifecycle (deterministický)
### Kanonická sekvence (z config.md)
```
FÁZE 0: ORIENTACE
  vision → status → architect → process → gap → generate → intake → prio

FÁZE 1: PLÁNOVÁNÍ
  sprint → analyze

FÁZE 2: IMPLEMENTACE (WIP=1, per task)
  implement → test → review (→ případně rework loop)

FÁZE 3: UZAVŘENÍ
  close → docs → check → archive
```

### Kontrakt s `{WORK_ROOT}/config.md` (LIFECYCLE)
- Pokud config obsahuje YAML blok `LIFECYCLE`, musí odpovídat této tabulce „next step“.
- Pokud se liší (drift):
  - vytvoř intake item `{WORK_ROOT}/intake/config-lifecycle-drift.md` dle `{WORK_ROOT}/templates/intake.md`
  - do intake přilož oba seznamy kroků (config vs loop) + doporučenou opravu
  - nastav `state.error` na vysvětlení a **STOP** (nepokračuj v běhu, dokud se drift nevyřeší)

> Cíl: zabránit tichému rozjetí, kdy config říká A a loop dělá B.

---


## Okno běhu (loop window)
Na začátku běhu urč `RUN_MODE`, `MAX_LOOPS` a `MAX_TICKS_PER_LOOP` podle parametru `loop=<...>`

Dále urč `GOAL` a připrav `GOAL_ARG`:
- `GOAL` = token `goal=<...>` nebo `RUN.default_goal` (default `release`)
- `GOAL_ARG` = prázdné, pokud `GOAL` je `release`/None; jinak `--goal "<GOAL>"`
 (viz sekce *Spuštění*) a podle `RUN.*` v `config.md`:

- pokud parametr **není**: `RUN_MODE=fixed`, `MAX_LOOPS = RUN.max_loops_default` (fallback `RUN.max_ticks_default`, default `1`)
- pokud `loop=<N>`: `RUN_MODE=fixed`, `MAX_LOOPS = clamp(N, RUN.max_loops_clamp)` (fallback `RUN.max_ticks_clamp`, default clamp `1–50`)
- pokud `loop=auto`: `RUN_MODE=auto`, `MAX_LOOPS = RUN.auto_max_loops` (default `100`)

`MAX_TICKS_PER_LOOP` je safety cap proti nekonečným smyčkám, ale **nesmí být tak nízký, aby usekl reálnou práci**.

Použij tento deterministický výpočet (bez heuristik):
- `BASE = RUN.max_ticks_per_loop` (default `25`)
- `EST = len(LIFECYCLE.steps) + (SPRINT.max_tasks * 3 * (1 + SPRINT.max_rework_iters))`
  - `3` je implement → test → review pro 1 task
  - rework iterace přidává další cyklus implement/test/review
- `AUTO_MIN = 2 * EST` (**100% rezerva**)
- pokud `RUN_MODE == auto`: `MAX_TICKS_PER_LOOP = clamp(max(BASE, AUTO_MIN), 25..1000)`
- pokud `RUN_MODE == fixed`: `MAX_TICKS_PER_LOOP = clamp(BASE, 1..1000)`

Pak proveď nejvýše `MAX_LOOPS` loopů. Každý loop obsahuje 1+ ticků (dispatchů) až do loop boundary.
### Tick algoritmus (deterministický)
V rámci každého loopu proveď nejvýše `MAX_TICKS_PER_LOOP` ticků. Pro každý tick:

1) Načti `{WORK_ROOT}/state.md`.
2) Pokud `state.error != null` → spusť crash recovery (sekce níže) a **STOP**.
3) Pokud `state.step == "idle"`:
   - pokud `RUN_MODE != auto` → zaloguj “idle (fixed)” a **STOP (OK)**.
   - pokud `RUN_MODE == auto` → proveď *idle tick* deterministicky (bez `--completed`):

     ```bash
     python skills/fabric-init/tools/fabric.py tick --run-mode auto {GOAL_ARG}
     ```

   - znovu načti `{WORK_ROOT}/state.md`:
     - pokud je stále `idle` → zaloguj “still idle” a **STOP (OK)**
     - pokud `state.error != null` → **STOP + ESCALATE**
     - jinak pokračuj.
4) Dispatchni skill pro aktuální `state.step` (podle tabulky „next step“ níže).
   - ulož si `COMPLETED_STEP = state.step` (budeš ho používat pro kontrakt + tick + run report)
5) Ověř kontrakt výstupů deterministicky:

   ```bash
   python skills/fabric-init/tools/fabric.py contract-check --step “<COMPLETED_STEP>”
   CONTRACT_EXIT=$?
   if [ $CONTRACT_EXIT -ne 0 ]; then
     echo “STOP: contract-check FAIL for step $COMPLETED_STEP (exit $CONTRACT_EXIT)”
     python skills/fabric-init/tools/fabric.py state-patch --fields-json “{\”error\”: \”STOP: contract-check FAIL — $COMPLETED_STEP\”}”
     # Vytvoř intake item
     python skills/fabric-init/tools/fabric.py intake-new --source “loop” --slug “contract-breach-$COMPLETED_STEP” \
       --title “Contract check failed for $COMPLETED_STEP”
     exit 1
   fi
   ```
6) Deterministicky posuň stav jedním příkazem (gating + next step + patch state):

   ```bash
   python skills/fabric-init/tools/fabric.py tick --completed "<COMPLETED_STEP>" --run-mode {RUN_MODE} {GOAL_ARG}
   ```

   - `tick` řeší všechny guardy:
     - po `test` čte poslední test report (vyžaduje `Result: PASS|FAIL|TIMEOUT`)
     - po `review` čte poslední review report (vyžaduje `verdict: CLEAN|REWORK|REDESIGN` nebo `Verdict:`)
     - po `analyze` kontroluje Task Queue — pokud je prázdná (0 tasks) → next step = `docs` (přeskoč implement)
     - po `close` rozhodne mezi `implement` vs `docs` podle sprint plánu
     - po `prio` a po `archive` v `RUN_MODE=auto` umí spadnout do `idle`
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
   RUN_ID=$(python skills/fabric-init/tools/fabric.py state-get --field run_id 2>/dev/null)
   STATE_GET_EXIT=$?
   if [ $STATE_GET_EXIT -ne 0 ]; then
     echo "WARN: state-get failed (exit $STATE_GET_EXIT), treating as null"
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
   NEXT_RUN_ID=$(python skills/fabric-init/tools/fabric.py state-get --field run_id 2>/dev/null)
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

### Dispatch pravidla
1. **Načti `{WORK_ROOT}/state.md`.**
2. Pokud `state.error != null` → spusť crash recovery (sekce níže).
3. Jinak podle `phase/step` vyber další skill:
   - když `step` je null/neznámý → začni `vision`
   - jinak pokračuj na „další“ podle tabulky níže

### Tabulka „next step“
| Aktuální step | Next step |
|--------------|-----------|
| vision | status |
| status | architect |
| architect | process |
| process | gap |
| gap | generate |
| generate | intake |
| intake | prio |
| prio | sprint |
| sprint | analyze |
| analyze | implement — **guard:** pokud Task Queue ve sprint plánu je prázdná (0 tasks po analýze) → přeskoč na `docs` (sprint bez implementačních položek). Vytvoř intake item `intake/loop-empty-task-queue-sprint-{N}.md`. |
| implement | test |
| test | pokud PASS → review; pokud FAIL → implement (test_fail_count++) |
| review | pokud CLEAN → close; pokud REWORK → implement; pokud REDESIGN → close (BLOCKED) |
| close | pokud existuje další READY task v Task Queue → implement; jinak docs |
| docs | check |
| check | archive |
| archive | vision *(nový cyklus / nový sprint)* — **ale v `loop=auto`:** `tick()` po archive provede work-status check → pokud není práce → `idle` (loop boundary) |

> `phase` je pomocná (orientation/planning/implementation/closing), ale **step** je zdroj pravdy pro dispatch.
>
> **Clarifikace post-archive v auto mode:** Po `archive` tick() rozhodne deterministicky: (a) pokud existuje práce (pending intake / backlog) → `step=vision` (nový sprint cyklus pokračuje), (b) pokud není práce → `step=idle` (loop boundary, orchestrátor skončí OK). Nikdy není stav, kdy archive přejde na vision a loop neví, jestli má pokračovat — `tick --run-mode auto` to řeší v jednom atomickém kroku.

**Poznámka (multi-task sprint / single-piece flow):** Fáze IMPLEMENTACE se opakuje **per task**. Po `review=CLEAN` jde orchestrátor na `close`, kde se task **merge-ne** (a WIP se resetuje). Teprve potom se vybere další READY task z `Task Queue`.

### Countery a limity (per task) — PERSISTED

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

#### Kdy a jak inkrementovat (explicitní kód)

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

Pokud override nastane, tick pokračuje s `REVIEW_VERDICT=REDESIGN` — tzn. backlog item → BLOCKED, WIP reset, next step = close (viz REDESIGN handling níže).

#### Kdy resetovat countery (explicitní)

Reset obou counterů na 0 nastává ve **dvou** situacích:
1. **Nový task**: Když fabric-loop vybere nový `wip_item` z Task Queue (tzn. změní se `state.wip_item`), přepíše `test_fail_count: 0`, `rework_count: 0` a `autofix_count: 0` v novém backlog itemu.
2. **Po úspěšném close**: Když `fabric-close` dokončí merge a gates PASS, fabric-loop resetuje countery v backlog itemu (nezávisle na tom, že task je DONE — pro audit trail).

Kdo provádí reset: **fabric-loop** (ne fabric-close, ne fabric-implement). Reset se provádí PŘED prvním dispatch na nový task, tzn. PŘED prvním implement tickem.

**Invocation point v tick algoritmu:** Counter operace se volají v kroku 6) MEZI `tick --completed` a dalším dispatch:
- Po `tick --completed "test"` → pokud next_step=implement (FAIL/TIMEOUT) → **inkrement** test_fail_count (kód níže)
- Po `tick --completed "review"` → pokud next_step=implement (REWORK) → **inkrement** rework_count (kód níže)
- Po `tick --completed "close"` → pokud next_step=implement (nový task) → **reset** obou counterů v novém wip_item (kód níže)
- Po `tick --completed "close"` → vždy → **reset** counterů v uzavřeném task (audit trail, kód níže)

#### Explicitní reset kód (povinný)

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

### Auto-fix scope (clarifikace)

Auto-fix (`lint_fix`, `format`) se spouští **max 1× per gate per skill run**. Across rework cycles se může spustit vícekrát — to je záměr: každý implement run je čistý pokus. Celkový počet auto-fix pokusů per task je bounded `max_rework_iters` (default 3). Auto-fix nikdy neopakuje po timeoutu.

### Verdict parsing (kanonický formát)

`tick()` parsuje verdikty z reportů takto (vždy z **nejnovějšího** reportu podle mtime):
> **Stale report guard:** Pokud existuje více reportů pro stejný step+wip_item (z předchozích runů/rework cyklů), `tick` MUSÍ parsovat NEJNOVĚJŠÍ (ls -t | head -1). Starší reporty nesmažou se (audit trail), ale nesmí ovlivnit aktuální verdikt.
- **test report:** Hledá řádek `Result: PASS` nebo `Result: FAIL` nebo `Result: TIMEOUT` (case-insensitive). Fallback: frontmatter `result:` YAML klíč. Pokud ani jedno → error.
  - `PASS` → next step = review
  - `FAIL` → next step = implement (+ counter increment)
  - `TIMEOUT` → hodnoť jako FAIL (next step = implement, counter increment), ALE: vytvoř intake item `intake/loop-test-timeout-{wip_item}.md` s doporučením identifikovat pomalé testy. V run reportu označ jako `TIMEOUT` (odlišně od FAIL pro root cause analýzu).
- **review report:** Hledá řádek `Verdict: CLEAN|REWORK|REDESIGN` (case-insensitive). Fallback: frontmatter `verdict:` YAML klíč. Pokud ani jedno → error.
  - Pokud review report obsahuje gate výsledek `TIMEOUT` (lint/format timeout): hodnoť jako REWORK (infrastrukturní problém, ne code quality). Vytvoř intake item pokud ještě neexistuje.
- Při error (unparseable report): `state.error = "unparseable {step} report"` + STOP.


---

## Před-dispatch a po-dispatch kontrakt
### Před spuštěním skillu
1. Zapiš do `state.md` (doporučeno deterministicky přes `fabric.py`):

```bash
python skills/fabric-init/tools/fabric.py state-patch --fields-json '{"step":"<step>","last_run":"{YYYY-MM-DD}","error":null}'
```

Pokud to z nějakého důvodu nejde, můžeš state upravit ručně — ale nesmíš rozbít YAML fence.

Nastav v `state.md`:
   - `step: <název kroku>`
   - `last_run: <ISO date/time>`
   - `error: null` (reset)
2. Pokud je to implement/test/review/close, ověř `wip_item` existuje (jinak je to bug → set error).

### Po dokončení skillu
1. Ověř očekávané výstupy existují (minimální kontrakt).

   **Preferuj deterministicky:**

   ```bash
   python skills/fabric-init/tools/fabric.py contract-check --step "<COMPLETED_STEP>"
   ```

   Pokud kontrakt neprojde, vytvoř intake item (kontrakt breach) a nastav `state.error`.

2. (Pokud chceš manuálně) minimální kontrakt je tato tabulka:

| Step | Povinný výstup |
|------|----------------|
| vision | `reports/vision-*.md` |
| status | `reports/status-*.md` |
| architect | `reports/architect-*.md` (+ volitelně intake items) |
| gap | `reports/gap-*.md` (+ intake items) |
| generate | `reports/generate-*.md` *(intake items 0..N jsou OK)* |
| intake | `reports/intake-*.md` + nové backlog itemy + update backlog.md |
| prio | `reports/prio-*.md` + update backlog.md + update prio ve backlog items |
| sprint | `sprints/sprint-{N}.md` + update sprint fields ve state |
| analyze | `analyses/*-analysis.md` (pro tasks ve sprintu) + update sprint Task Queue |
| implement | git branch + commit + update backlog item (branch/status) |
| test | `reports/test-*.md` |
| review | `reports/review-*.md` (+ update backlog item review_report) |
| close | `reports/close-*.md` + update backlog.md |
| docs | `reports/docs-*.md` |
| check | `reports/check-*.md` |
| archive | `reports/archive-*.md` + update archive/ |

2. Pokud kontrakt nesedí:
   - Zapiš `state.error` s přesným popisem.
   - Vytvoř intake item `intake/orchestrator-contract-breach-<step>.md`.
   - STOP.

3. Pokud OK:
   - nastav `last_completed: <step>`
   - posuň `step` na next step (viz tabulka)

---

## Crash recovery (když state.error != null)
Cíl: pokračovat bezpečně a idempotentně.

### Git state pre-flight (povinné — před KAŽDÝM dispatch)
Před dispatchem jakéhokoli skillu ověř konzistenci git stavu:
```bash
# Detekuj stale merge-in-progress
if git rev-parse --verify MERGE_HEAD >/dev/null 2>&1; then
  echo "WARN: stale merge-in-progress, aborting"; git merge --abort
fi
# Detekuj stale rebase-in-progress
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
  echo "WARN: stale rebase-in-progress, aborting"; git rebase --abort
fi
# Detekuj stale revert-in-progress
if git rev-parse --verify REVERT_HEAD >/dev/null 2>&1; then
  echo "WARN: stale revert-in-progress, aborting"; git revert --abort
fi
```
Pokud jakýkoli abort selže → `state.error = "git state inconsistent"` + STOP + intake item.

### Error kategorizace (rozlišení pro recovery)

`state.error` může mít dvě kategorie:
- **Intentional STOP** (prefix `BLOCKED_ONLY:` nebo `STOP:`): Orchestrátor záměrně zastavil (všechno BLOCKED, counter limit, config drift). Recovery: **NE-retry**. Pouze ESCALATE na uživatele.
- **Crash/failure** (vše ostatní): Neočekávaný problém. Recovery: retry postup níže.

**Kanonický pattern (regex):** Intentional error matchuje prefixy z `config.md ERROR_TAXONOMY.intentional_prefixes`:
```bash
# Trim whitespace před pattern match
STATE_ERROR_TRIMMED=$(echo "$STATE_ERROR" | sed 's/^[[:space:]]*//')
# Prefixy z config.md ERROR_TAXONOMY (source of truth):
INTENTIONAL_PATTERN="^(BLOCKED_ONLY:|STOP:|test_fail_count exceeded|rework_count exceeded|config_drift:)"
if echo "$STATE_ERROR_TRIMMED" | grep -qE "$INTENTIONAL_PATTERN"; then
  echo "Intentional STOP — no retry, ESCALATE"
else
  echo "Crash/failure — retry postup"
fi
```
> **Source of truth:** `config.md` sekce `ERROR_TAXONOMY.intentional_prefixes` definuje kanonický seznam. Tento regex MUSÍ odpovídat config registru. Jakýkoli nový intentional stop MUSÍ přidat prefix do config.md ERROR_TAXONOMY A aktualizovat tento regex.

### Obecný postup (pro crash/failure errors)
1. Přečti `state.error` + `step`
2. Pokud error je **intentional** (viz kategorizace výše) → ESCALATE bez retry
3. Zkontroluj, zda existuje výstup, který měl vzniknout
4. Pokud výstup existuje → error byl false alarm → vyčisti `error` a pokračuj dál
5. Pokud výstup neexistuje → rerun stejného step (idempotentně), max 1×
6. Pokud selže znovu → eskalace:
   - vytvoř evidence pack (ZIP) pro debug:

     ```bash
     python skills/fabric-init/tools/fabric.py evidence-pack --label "crash-<step>"
     ```

   - vytvoř intake item (doporučeno deterministicky přes `intake-new`) a přilož:
     - `state.error`
     - odkazy na relevantní reporty
     - odkaz na evidence ZIP
   - nech `state.error` vyplněné a **STOP**

### Speciál: review výsledky
Pokud `review` report říká `Verdict: REWORK`:
- `fabric-loop` nastaví next step = `implement`
- `fabric-implement` musí checkoutnout existující branch z backlog itemu (`branch:`) a opravit jen findings

Pokud `review` report říká `Verdict: CLEAN`:
- backlog item je označen jako `DONE` (provádí `fabric-review`)
- `fabric-loop` nastaví next step = `close` (merge WIP a reset WIP se děje až v `fabric-close`)

Pokud `review` report říká `Verdict: REDESIGN`:
- `fabric-loop` nastaví backlog item status = `BLOCKED` a zapíše důvod z review reportu
- `fabric-loop` resetuje WIP: `git checkout main`, `state.wip_item = null`, `state.wip_branch = null`
- Branch se **nesmaže** (zůstává jako reference pro budoucí redesign)
- `fabric-loop` nastaví next step = `close` — `fabric-close` přeskočí merge (WIP=null) a pokračuje na docs

**Explicitní přechod po REDESIGN close:**
Po close (s WIP=null, REDESIGN carry-over):
- `tick --completed close` zkontroluje Task Queue ve sprint plánu
- Pokud existuje další READY task → next step = `implement` (fabric-loop vybere nový task, resetuje countery, nastaví nový WIP)
- Pokud žádný READY task → next step = `docs` → pokračuje normálně docs→check→archive
- Toto je identické chování jako při normálním close (viz dispatch tabulka: "close → pokud existuje další READY task → implement; jinak docs")
- REDESIGN task se objeví jako carry-over v close sprint summary reportu


---

## Intake item deduplication (povinné)

Před vytvořením jakéhokoli intake itemu ověř, zda stejný (nebo ekvivalentní) item už neexistuje:

```bash
# Pattern: intake/{skill}-{slug}-*.md
INTAKE_PATTERN="{WORK_ROOT}/intake/{SKILL}-{SLUG}-*.md"
if ls $INTAKE_PATTERN 1>/dev/null 2>&1; then
  echo "SKIP: intake item already exists for $SKILL-$SLUG"
else
  # Vytvoř nový intake item
  python skills/fabric-init/tools/fabric.py intake-new --source "$SKILL" --slug "$SLUG" --title "$TITLE"
  INTAKE_EXIT=$?
  if [ $INTAKE_EXIT -ne 0 ]; then
    echo "WARN: intake-new failed (exit $INTAKE_EXIT) — logging to run report, continuing"
  fi
fi
```

**Pravidla:**
- Deduplication je na úrovni `{skill}-{slug}` (date/id se ignoruje).
- Pokud existující intake item má status `processed` nebo `rejected`, nový SE VYTVOŘÍ (opakující se problém po fixu).
- `intake-new` exit codes: 0 = úspěch, 1 = chyba (disk/permission), 2 = duplicitní (already exists). Exit 2 je OK (dedup guard v tool), exit 1 vyžaduje WARN log.
- Pokud existující intake item má status `new` nebo `pending`, nový se NEVYTVOŘÍ (čeká na zpracování).
- Toto platí pro VŠECHNY skilly — implement, test, review, close, loop, check.

---

## Inter-skill data flow (souborově)
- `fabric-generate` → `{WORK_ROOT}/intake/*.md` → `fabric-intake`
- `fabric-gap` → `{WORK_ROOT}/intake/*.md` → `fabric-intake`
- `fabric-architect` → `{WORK_ROOT}/intake/*.md` → `fabric-intake`
- `fabric-review` (systemic findings) → `{WORK_ROOT}/intake/*.md` → `fabric-intake`
- `fabric-check` → `{WORK_ROOT}/intake/*.md` → `fabric-intake`

- `fabric-intake` → `{WORK_ROOT}/backlog/*.md` + `{WORK_ROOT}/backlog.md` → `fabric-prio`
- `fabric-prio` → update `prio:` ve backlog items + seřazený `{WORK_ROOT}/backlog.md` → `fabric-sprint`
- `fabric-sprint` → `{WORK_ROOT}/sprints/sprint-{N}.md` → `fabric-analyze`
- `fabric-analyze` → `{WORK_ROOT}/analyses/*-analysis.md` + doplní `Task Queue` ve sprintu → `fabric-implement`
- `fabric-implement` → git branch + update backlog item (`branch/status`) → `fabric-test`
- `fabric-test` → `reports/test-*.md` → `fabric-review`
- `fabric-review` → `reports/review-*.md` + update backlog item (`review_report`) → `fabric-close`

- `fabric-close` → merge do main + update backlog statuses + `reports/close-*.md` → `fabric-docs`
- `fabric-docs` → update `{DOCS_ROOT}/` + `reports/docs-*.md` → `fabric-check`
- `fabric-check` → `reports/check-*.md` (+ intake items) → `fabric-archive`
- `fabric-archive` → snapshot do `archive/` + `reports/archive-*.md` → nový cyklus

---

## Výstup orchestrátoru
Na konci každého RUN cyklu:
- `state.md` je aktualizovaný a konzistentní
- `{WORK_ROOT}/reports/run-{run_id}.md` existuje (vytvořeno `fabric.py run-report`; timeline + odkazy na step reporty)
- existuje report pro daný step (pokud ho step generuje)
- pokud došlo k chybě, existuje intake item s reprodukovatelným popisem

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
- countery (`test_fail_count`, `rework_count`) v backlog itemu odpovídají skutečnému počtu FAIL/REWORK cyklů:
  ```bash
  # Counter cross-check (povinné pokud wip_item existuje)
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
- `autofix_count` v backlog itemu odpovídá skutečnému počtu auto-fix commitů:
  ```bash
  # Autofix counter cross-check (povinné pokud wip_item existuje)
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
- Cross-sprint prio invariant (při carry-over): pokud task přechází do dalšího sprintu, `prio` field je stale (nebyl re-kalkulován od posledního `fabric-prio`). Self-check zaloguje WARNING:
  ```bash
  # Cross-sprint prio staleness check (po close, pokud existují carry-over tasks)
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

Pokud ne → FAIL + zapiš `state.error` s detailním popisem a STOP.

## Concurrency (single-instance assumption)

Fabric-loop předpokládá **single-instance** operaci — v jednu chvíli smí běžet **nejvýše jeden** orchestrátor pro daný `{WORK_ROOT}`. Concurrent přístup není podporován a způsobí:
- race conditions na `state.md` (dva loopy přepisují step/wip)
- dvojitý merge do main (data corruption)
- counter inkonsistence (test_fail_count / rework_count)

**Detekce (best-effort):** Na začátku RUN zkontroluj `{WORK_ROOT}/logs/protocol.jsonl` — pokud poslední záznam je `event: start` pro `fabric-loop` BEZ odpovídajícího `event: end` a `last_tick_at` je < 10 minut → zaloguj WARNING „possible concurrent instance" do run reportu. Toto NENÍ lock — pouze upozornění.

**Prevence:** Leží na uživateli / CI — nespouštět dva RUN cykly současně.

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
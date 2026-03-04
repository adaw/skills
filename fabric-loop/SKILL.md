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
  vision → status → architect → gap → generate → intake → prio

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
   python skills/fabric-init/tools/fabric.py contract-check --step "<COMPLETED_STEP>"
   ```

   Pokud kontrakt neprojde → **STOP + ESCALATE** (viz „Crash recovery“).
6) Deterministicky posuň stav jedním příkazem (gating + next step + patch state):

   ```bash
   python skills/fabric-init/tools/fabric.py tick --completed "<COMPLETED_STEP>" --run-mode {RUN_MODE} {GOAL_ARG}
   ```

   - `tick` řeší všechny guardy:
     - po `test` čte poslední test report (vyžaduje `Result: PASS|FAIL`)
     - po `review` čte poslední review report (vyžaduje `verdict: CLEAN|REWORK|REDESIGN` nebo `Verdict:`)
     - po `close` rozhodne mezi `implement` vs `docs` podle sprint plánu
     - po `prio` a po `archive` v `RUN_MODE=auto` umí spadnout do `idle`
      - po `archive` incrementuje `state.sprint` a tím uzavírá loop
   - `tick` patchne `state.md` (`step/phase/last_completed/last_run/last_tick_at`).
   - pokud chybí důkazy nebo je kontrakt porušen → nastaví `state.error` a vrátí non‑zero → **STOP + ESCALATE**.

   Mapování `step → phase`:
   - **orientation:** vision, status, architect, gap, generate, intake, prio
   - **planning:** sprint, analyze
   - **implementation:** implement, test, review
   - **closing:** close, docs, check, archive
   - **idle:** idle
7) Zapiš odkaz na hlavní run report do `{WORK_ROOT}/reports/run-{run_id}.md` (append-only).

   Doporučeno deterministicky:

   ```bash
   python skills/fabric-init/tools/fabric.py run-report \
     --ensure-run-id \
     --completed "<COMPLETED_STEP>" \
     --status "OK" \
     --note "<1-line-summary>"
   ```

8) Pokud `AUDIT=1`: proveď **audit provedeného skillu** (po každém ticku).

Cíl auditu: ověřit, že se stalo to, co se mělo stát, že výstupy jsou konzistentní, a že nevznikl drift.

Deterministické minimum (vždy):
```bash
python skills/fabric-init/tools/fabric.py reports-validate --strict
```

Pak vytvoř audit report (1 soubor na tick), např.:
- `{WORK_ROOT}/reports/audit-{COMPLETED_STEP}-{YYYY-MM-DD}-{run_id}.md`

Doporučený postup:
1) načti poslední `contract-check` JSON (nebo ho zavolej znovu pro `<COMPLETED_STEP>`),
2) načti poslední report daného kroku (`fabric.py report-latest --kind "<COMPLETED_STEP>"`),
3) napiš krátký audit: **PASS/FAIL**, důkazy, rizika, návrhy (a případné intake itemy).

**Stop pravidlo:** pokud audit zjistí CRITICAL problém (bezpečnost, porušení decision/spec/vision, rozbitý state/protocol, nebo deterministické validace failují) → nastav `state.error` a **STOP**.



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
| architect | gap |
| gap | generate |
| generate | intake |
| intake | prio |
| prio | sprint |
| sprint | analyze |
| analyze | implement |
| implement | test |
| test | pokud FAIL → implement; pokud PASS → review |
| review | pokud REWORK → implement; pokud CLEAN → close |
| close | pokud existuje další READY task v Task Queue → implement; jinak docs |
| docs | check |
| check | archive |
| archive | vision *(nový cyklus / nový sprint)* |

> `phase` je pomocná (orientation/planning/implementation/closing), ale **step** je zdroj pravdy pro dispatch.

**Poznámka (multi-task sprint / single-piece flow):** Fáze IMPLEMENTACE se opakuje **per task**. Po `review=CLEAN` jde orchestrátor na `close`, kde se task **merge-ne** (a WIP se resetuje). Teprve potom se vybere další READY task z `Task Queue`.


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

### Obecný postup
1. Přečti `state.error` + `step`
2. Zkontroluj, zda existuje výstup, který měl vzniknout
3. Pokud výstup existuje → error byl false alarm → vyčisti `error` a pokračuj dál
4. Pokud výstup neexistuje → rerun stejného step (idempotentně), max 1×
5. Pokud selže znovu → eskalace:
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
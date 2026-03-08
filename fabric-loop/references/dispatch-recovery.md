# Dispatch, Bootstrap & Recovery — Detailed Reference

This document contains bootstrap procedures, dispatch rules, the next-step table, contracts, crash recovery procedures, and data flow from fabric-loop. See SKILL.md for the main orchestration logic.

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
   - **>1 match** → zvol deterministicky „nejkratší cesta, pak lexicograficky" jako `CONFIG_PATH`,
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

## Drift Detection

Porovnej config LIFECYCLE vs kanonickou sekvenci. Drift = STOP.

```bash
# State drift detection: compare config LIFECYCLE vs hardcoded canonical
CANONICAL="vision status architect process gap generate intake prio sprint analyze implement test review close docs check archive"
CONFIG_STEPS=$(grep -A 50 'LIFECYCLE:' "{WORK_ROOT}/config.md" | grep -oP '^\s+-\s+\K[a-z]+' | tr '\n' ' ' | sed 's/ $//')
if [ -n "$CONFIG_STEPS" ] && [ "$CONFIG_STEPS" != "$CANONICAL" ]; then
  echo "STOP: LIFECYCLE drift detected"
  echo "  Config:    $CONFIG_STEPS"
  echo "  Canonical: $CANONICAL"
  python skills/fabric-init/tools/fabric.py state-patch \
    --fields-json '{"error":"LIFECYCLE drift — config vs canonical mismatch"}'
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "loop" --slug "config-lifecycle-drift" \
    --title "LIFECYCLE drift: config steps differ from canonical sequence"
  exit 1
fi
```

---

## Timeout handling

Každý dispatchnutý skill musí běžet v rámci `SKILL_TIMEOUT` sekund (default 600, z `RUN.skill_timeout` v config.md).

```bash
# Timeout wrapper for dispatched skill
timeout ${SKILL_TIMEOUT} <skill_command>
SKILL_EXIT=$?

if [ $SKILL_EXIT -eq 124 ]; then
  echo "ERROR: Skill timed out after ${SKILL_TIMEOUT}s"
  python skills/fabric-init/tools/protocol_log.py \
    --work-root "{WORK_ROOT}" --skill "loop" --event error \
    --status ERROR --message "Skill ${CURRENT_STEP} timed out after ${SKILL_TIMEOUT}s"
  python skills/fabric-init/tools/fabric.py state-patch \
    --fields-json "{\"error\":\"timeout: ${CURRENT_STEP} exceeded ${SKILL_TIMEOUT}s\"}"
  # Create intake item for investigation
  python skills/fabric-init/tools/fabric.py intake-new \
    --source "loop" --slug "timeout-${CURRENT_STEP}" \
    --title "Skill ${CURRENT_STEP} timed out (${SKILL_TIMEOUT}s)"
  exit 1
fi
```

---

## Dispatch pravidla
1. **Načti `{WORK_ROOT}/state.md`.**
2. Pokud `state.error != null` → spusť crash recovery (sekce níže).
3. Jinak podle `phase/step` vyber další skill:
   - když `step` je null/neznámý → začni `vision`
   - jinak pokračuj na „další" podle tabulky níže

---

## Tabulka „next step"
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
> **Clarifikace post-archive:** Po `archive` tick() rozhodne deterministicky: (a) pokud existuje práce (pending intake / backlog) → `step=vision` (nový sprint cyklus pokračuje), (b) pokud není práce → `step=idle` (loop boundary, orchestrátor skončí OK). Nikdy není stav, kdy archive přejde na vision a loop neví, jestli má pokračovat — `tick --run-mode auto` to řeší v jednom atomickém kroku.

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

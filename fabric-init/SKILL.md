---
name: fabric-init
description: "Bootstrap WORK_ROOT into clean, idempotent Fabric runtime: directory structure, templates, state.md, vision.md, backlog.md. Single-command start point enabling loop to run without human intervention."
---

# FABRIC-INIT — Bootstrap (idempotent)

## Účel

`fabric-init` připraví (nebo opraví) runtime strukturu ve `{WORK_ROOT}/` tak, aby `fabric-loop` mohl běžet **bez lidského zásahu**.


## Protokol (povinné)

Na začátku a na konci tohoto skillu zapiš události do protokolu:

- START:
  - `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-init" --event start`
- END (OK/WARN/ERROR):
  - `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-init" --event end --status OK --report "{WORK_ROOT}/reports/init-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** kvůli chybě (např. chybí config/templates), loguj `event=error` a napiš krátký důvod do `--message`.

Vytvoří skeleton (`state.md`, `vision.md`, `backlog.md`, adresáře, templates) pokud neexistují. Pokud existují, přeskočí (idempotent).

---


## FAST PATH (doporučeno) — mechanika skriptem, LLM jen rozhoduje

Neplýtvej tokeny na “mkdir/cp/počty souborů”. Tohle je deterministická práce.

1) Zajisti workspace skeleton + templates + state/backlog:

```bash
python skills/fabric-init/tools/fabric.py bootstrap --create-vision-stub --out-json "{WORK_ROOT}/reports/bootstrap-{YYYY-MM-DD}.json"
```

2) Validuj workspace (gate):

```bash
python skills/fabric-init/tools/validate_fabric.py --workspace
```

2.05) Enforc vision.md content (P1 gate — warn-only):

```bash
# --- Vision.md content enforcement (P1 fix) ---
VISION_FILE="{WORK_ROOT}/vision.md"
if [ -f "$VISION_FILE" ]; then
  VISION_LINES=$(wc -l < "$VISION_FILE")
  if [ "$VISION_LINES" -lt 10 ]; then
    echo "WARN: vision.md exists but appears to be a stub ($VISION_LINES lines)"
    echo "ACTION: Fill in vision.md with project principles, goals, and non-goals"
    echo "IMPACT: fabric-architect and fabric-intake depend on vision.md content"
  fi
  # Principle count validation (fabric-architect expects ≥3 principles)
  PRINCIPLE_COUNT=$(grep -ciE '^\s*[-*]\s*(princip|principle|zásada)|^#+.*princip' "$VISION_FILE" 2>/dev/null || echo 0)
  if [ "$PRINCIPLE_COUNT" -lt 3 ]; then
    echo "WARN: vision.md has $PRINCIPLE_COUNT principles (fabric-architect expects ≥3)"
    echo "ACTION: Add project principles as bullet points (e.g., '- Principle: Everything is Async')"
  fi
else
  echo "WARN: vision.md not found — bootstrap should have created a stub"
fi
```

> **Note:** This is a WARN gate, not a STOP. Init completes, but the user must fill in `vision.md` before downstream skills (`fabric-architect`, `fabric-intake`) can run effectively.

2.1) Vygeneruj governance indexy (deterministicky):

```bash
python skills/fabric-init/tools/fabric.py governance-index
```

3) Vygeneruj krátký init report:
- přečti `{WORK_ROOT}/reports/bootstrap-{YYYY-MM-DD}.json`
- zapiš `{WORK_ROOT}/reports/init-{YYYY-MM-DD}.md` (co bylo vytvořeno, co chybí, co je risk)

> Pokud FAST PATH uspěje, pokračuj na krok “0.1 Normalizuj config” jen tehdy, když `COMMANDS.*` jsou `TBD` nebo neodpovídají realitě.

---

## Input Validation (K7 — path traversal ochrana)

```bash
# validate_path: odmítne cesty obsahující ".." pro bezpečnost
validate_path() {
  local path="$1"
  local context="$2"
  if echo "$path" | grep -qE '(\.\./|/\.\.)'; then
    echo "STOP: path traversal detected in $context: '$path'"
    return 1
  fi
  return 0
}

# Validuj WORK_ROOT z config (hlavní vstup initu)
if [ -n "$WORK_ROOT" ]; then
  validate_path "$WORK_ROOT" "WORK_ROOT" || exit 1
fi

# Validuj TEMPLATES_ROOT
if [ -n "$TEMPLATES_ROOT" ]; then
  validate_path "$TEMPLATES_ROOT" "TEMPLATES_ROOT" || exit 1
fi
```

## 0) Předpoklady

1. Musíš mít k dispozici Fabric `config.md`.
   - Pokud tě spustil `fabric-loop`, config už je vybraný a je v `{WORK_ROOT}/config.md`.
   - Pokud `WORK_ROOT` ještě neznáš, udělej discovery stejně jako `fabric-loop` (git ls-files / find) a najdi správný `config.md`.

2. Musíš mít právo zápisu do `{WORK_ROOT}/`.

3. Vše zapisuj v UTF-8.

```bash
# --- Preconditions bash validation ---
# P1: Skills root must be accessible
if [ ! -d "skills/fabric-init" ]; then
  echo "STOP: skills/fabric-init not found — fabric skills directory missing"
  exit 1
fi

# P2: fabric.py tool must exist
if [ ! -f "skills/fabric-init/tools/fabric.py" ]; then
  echo "STOP: fabric.py not found — run git pull or check skills installation"
  exit 1
fi

# P3: config template must exist for bootstrap
if [ ! -f "skills/fabric-init/assets/config.template.md" ]; then
  echo "STOP: config.template.md not found — cannot bootstrap without template"
  exit 1
fi

# P4: validate_fabric.py must exist
if [ ! -f "skills/fabric-init/tools/validate_fabric.py" ]; then
  echo "STOP: validate_fabric.py not found — cannot validate workspace"
  exit 1
fi
```

Pokud config nejde najít nebo YAML nejde parsovat → **STOP** a vytvoř `./bootstrap-missing-or-invalid-config.md` (popiš co chybí a jak to opravit).

---


## 0.1) Normalizuj config (autodetect `COMMANDS`)

**Detail:** Viz `references/config-normalization.md` pro detailní autodetekci COMMANDS dle jazyka, fallback strategie a evidence.


## 1) Konfigurace (config.md) — bootstrap a kontrola (povinné)

`{WORK_ROOT}/config.md` je **source-of-truth** pro cesty, taxonomii, příkazy a quality gates.

### 1.1 Pokud config chybí (nový projekt)

Pokud `{WORK_ROOT}/config.md` **neexistuje**:

1) Vytvoř `{WORK_ROOT}/` adresář (pokud chybí).
2) Zkopíruj default config šablonu:
   - zdroj: `skills/fabric-init/assets/config.template.md`
   - cíl: `{WORK_ROOT}/config.md`
   - idempotence: pokud cílový soubor existuje, nepřepisuj
3) Vytvoř intake item `{WORK_ROOT}/intake/bootstrap-config-required.md` (pokud runtime templates ještě nejsou, použij zdrojovou šablonu `skills/fabric-init/assets/templates/intake.md`; po kroku 3 se runtime templates doplní) se shrnutím:
   - že byl vytvořen default config
   - co MUSÍ člověk/agent doplnit (např. `COMMANDS.test`, `CODE_ROOT`, integrace, CI)
4) Pokud v configu zůstalo `TBD` v povinných polích (zejména `COMMANDS.test`) → **STOP** (bez test commandu nelze bezpečně běžet autonomně).

### 1.2 Pokud config existuje

- Načti ho a ověř, že obsahuje YAML blok s klíči minimálně: `WORK_ROOT`, `SKILLS_ROOT`, `TEMPLATES_ROOT`, `COMMANDS.test`.
- Pokud je config neparsovatelný → vytvoř intake `bootstrap-config-parse-error.md` a **STOP**.


---

## 2) Vytvoř runtime strukturu (idempotentně)

Vytvoř adresáře (pokud neexistují):

```bash
mkdir -p "{WORK_ROOT}/backlog"
mkdir -p "{WORK_ROOT}/backlog/done"
mkdir -p "{WORK_ROOT}/intake"
mkdir -p "{WORK_ROOT}/intake/done"
mkdir -p "{WORK_ROOT}/intake/rejected"
mkdir -p "{WORK_ROOT}/sprints"
mkdir -p "{WORK_ROOT}/reports"
mkdir -p "{WORK_ROOT}/logs"
mkdir -p "{WORK_ROOT}/analyses"
mkdir -p "{WORK_ROOT}/templates"
mkdir -p "{WORK_ROOT}/decisions"
mkdir -p "{WORK_ROOT}/specs"
mkdir -p "{WORK_ROOT}/reviews"

mkdir -p "{VISIONS_ROOT}"             # Sub-vize (rozšíření core vision.md)

mkdir -p "{WORK_ROOT}/archive"
mkdir -p "{WORK_ROOT}/archive/backlog"
mkdir -p "{WORK_ROOT}/archive/sprints"
mkdir -p "{WORK_ROOT}/archive/reports"
mkdir -p "{WORK_ROOT}/archive/analyses"
mkdir -p "{WORK_ROOT}/archive/visions"
mkdir -p "{WORK_ROOT}/archive/quarantine"
```

---

## 3) Zajisti templates

### 3.1 Source-of-truth (skills) vs runtime (workspace)

- **Source-of-truth defaults** (součást distribuce): `{CANON_TEMPLATES_ROOT}` z `{WORK_ROOT}/config.md`  
  (fallback, pokud klíč chybí: `skills/fabric-init/assets/templates/`)
- **Runtime templates** (workspace, které skills používají): `{WORK_ROOT}/templates/`  
  (alias `{TEMPLATES_ROOT}` z config.md; typicky `{WORK_ROOT}/templates/`)

> Cíl: Workspace musí mít kompletní runtime templates. Default šablony se kopírují ze skills pouze tehdy, když runtime soubor chybí.

### 3.2 Postup (idempotentní)

Požadované soubory ber z `{WORK_ROOT}/config.md` → YAML klíč `TEMPLATES_REQUIRED:` (source-of-truth).

1) Načti `TEMPLATES_REQUIRED` (list názvů souborů). Pokud chybí, použij default list:
   - `adr.md`, `audit-report.md`, `close-report.md`, `epic.md`, `intake.md`, `migration-report.md`,
     `review-summary.md`, `sprint-plan.md`, `state.md`, `status-report.md`, `spec.md`, `story.md`, `task.md`, `report.md`
2) Ověř existenci **source-of-truth** šablon v `{CANON_TEMPLATES_ROOT}`:
   - Pro každý `t` ověř existenci `{CANON_TEMPLATES_ROOT}/{t}`.
   - Pokud některá chybí:
     - vytvoř intake item `{WORK_ROOT}/intake/bootstrap-missing-canon-template-{t}.md` dle `{WORK_ROOT}/templates/intake.md`
     - zapiš do init reportu **CRITICAL**
     - **STOP** (bez canonical defaults nelze bootstrapovat spolehlivě)
3) Zajisti existenci runtime adresáře `{WORK_ROOT}/templates/` (pokud chybí, vytvoř).
4) Zajisti runtime templates (kopíruj jen chybějící):
   - Pro každý `t`:
     - Pokud `{WORK_ROOT}/templates/{t}` neexistuje → zkopíruj ze `{CANON_TEMPLATES_ROOT}/{t}`
     - Pokud existuje:
       - **nepřepisuj**
       - pokud se liší obsah (hash), zapiš do init reportu **WARNING: template drift** (ale pokračuj)
5) Po kopii znovu ověř, že `{WORK_ROOT}/templates/{t}` existuje pro všechny required `t`.
   - Pokud stále něco chybí → **STOP**.

## 4) Vytvoř/oprava state.md

### 4.1 Sprint autodetect

- Pokud existují `sprints/sprint-*.md`, vezmi nejvyšší N a nastav `sprint = N` (aktuální).
- Pokud žádný sprint neexistuje → `sprint = 1`.

### 4.2 state.md (pokud chybí)

`state.md` je **markdown** soubor s jediným autoritativním YAML blokem (viz `{WORK_ROOT}/templates/state.md`).

1) Pokud `{WORK_ROOT}/state.md` neexistuje:
- vytvoř ho **kopií** `{WORK_ROOT}/templates/state.md`
- pak uprav YAML blok (uvnitř ```yaml) na:

```yaml
schema: <SCHEMA.state from {WORK_ROOT}/config.md>
phase: orientation
step: vision
sprint: <N>                 # z autodetectu (sekce 3.1), jinak 1
wip_item: null
wip_branch: null
last_completed: null
last_run: null
error: null

# Optional sprint metadata (set by fabric-sprint)
sprint_started: null
sprint_ends: null
sprint_goal: null
```

**Nezapisuj** žádný non‑YAML text dovnitř YAML bloku (jinak se nedá parsovat).

2) Pokud `{WORK_ROOT}/state.md` existuje:
- ověř, že obsahuje ` ```yaml ` blok a že jde parsovat
- doplň chybějící klíče s `null`
- **neměň** `phase/step` pokud jsou validní (ownership má fabric-loop)

Pokud `state.md` existuje:
- doplň chybějící klíče s `null`
- **neměň** `phase/step` pokud jsou validní

---

## 5) Vize (vision.md)

> **DŮLEŽITÉ:** `vision.md` se NIKDY automaticky negeneruje ani nesyntezuje.
> Vize je autorský dokument — píše ji člověk (nebo člověk + agent ručně).
> `fabric-init` pouze ověří, že existuje.

Pokud `{WORK_ROOT}/vision.md` existuje → nechej být. **Nesahej na obsah.**

Pokud neexistuje:
- Vytvoř minimální placeholder a zapiš WARNING do init reportu:

```markdown
# Vize projektu

> PLACEHOLDER — tento dokument musí být napsán ručně.
> Viz fabric-vision skill pro quality gates.
```

- Vytvoř intake item `{WORK_ROOT}/intake/vision-missing.md` s `raw_priority: 9`
  (vize je prerekvizita pro celý lifecycle).

---

## 6) Backlog index (backlog.md)

Pokud `{WORK_ROOT}/backlog.md` neexistuje, vytvoř:

```markdown
# Backlog Index

| ID | Title | Type | Status | Tier | Effort | PRIO |
|----|-------|------|--------|------|--------|------|
```

Pokud backlog itemy existují v `{WORK_ROOT}/backlog/*.md`, ale index je prázdný:
- přegeneruj index z YAML frontmatter (id/title/type/status/tier/effort/prio)

---

## 7) Výstup initu

Vytvoř report `{WORK_ROOT}/reports/init-{YYYY-MM-DD}.md`:

- co bylo vytvořeno
- co bylo přeskočeno (idempotence)
- warnings (chybějící templates, missing config COMMANDS)

---

## K10 — Concrete Example & Anti-patterns

### Example: Init LLMem Workspace — First Run

```
Input: WORK_ROOT=/home/user/projects/llmem (empty directory)
FAST PATH execution:

Step 1 - Bootstrap workspace skeleton:
  python skills/fabric-init/tools/fabric.py bootstrap --create-vision-stub \
    --out-json "{WORK_ROOT}/reports/bootstrap-2026-03-07.json"
  Result: config.md, state.md, backlog.md, templates/ created

Step 2 - Validate workspace:
  python skills/fabric-init/tools/validate_fabric.py --workspace
  Result: PASS (all directories exist, templates found)

Step 3 - Enforce vision.md:
  wc -l {WORK_ROOT}/vision.md
  Result: 10 lines (stub only, WARN)
  Action: Create intake item "vision-missing" with raw_priority=9

Step 4 - Generate indexes:
  python skills/fabric-init/tools/fabric.py governance-index
  Result: DONE, INDEX.md created for decisions/ and specs/

Output structure created:
  {WORK_ROOT}/
  ├── config.md (default values, COMMANDS.test=TBD — WARN)
  ├── state.md (phase=orientation, sprint=1)
  ├── vision.md (placeholder)
  ├── backlog.md (empty index)
  ├── templates/ (14 runtime templates copied)
  ├── intake/ (vision-missing item created)
  └── reports/init-2026-03-07.md (execution evidence)
```

### Anti-patterns (FORBIDDEN detection & prevention)

```bash
# A1: Config Overwrite — NESMÍ přepsat existující config.md
# DETECTION: Test existence before copy
if [ -f "{WORK_ROOT}/config.md" ]; then
  echo "STOP: config.md already exists — do not overwrite"
  exit 1
fi

# A2: Vision Auto-generate — NESMÍ generovat obsah vision.md
# DETECTION: Grep for real content (not placeholder)
VISION_CONTENT=$(grep -cv '^#\|^>\|^$\|placeholder' "{WORK_ROOT}/vision.md" 2>/dev/null || echo 0)
if [ "$VISION_CONTENT" -gt 5 ]; then
  echo "WARN: vision.md appears to have auto-generated content"
  exit 1  # STOP — vision is author-only
fi

# A3: State Overwrite — NESMÍ resetovat phase/step pokud validní
# DETECTION: Read current state before patching
CURRENT_PHASE=$(grep '^phase:' "{WORK_ROOT}/state.md" 2>/dev/null | awk '{print $2}')
if [ -n "$CURRENT_PHASE" ] && [ "$CURRENT_PHASE" != "orientation" ]; then
  echo "WARN: state.md has phase=$CURRENT_PHASE (existing run) — do not reset"
  # Only patch missing keys, NEVER overwrite phase/step
fi
```

---

## Anti-patterns (ZAKÁZÁNO)

- **A1: Config Overwrite** — NESMÍ přepsat existující `config.md` vlastním obsahem. Detection: `test -f {WORK_ROOT}/config.md`. Fix: Pokud existuje, pouze validuj; nepřepisuj.
- **A2: Vision Auto-generate** — NESMÍ automaticky generovat obsah `vision.md`. Vision je autorský dokument. Detection: Zkontroluj, že vision.md má jen placeholder pokud byl vytvořen initem. Fix: Vytvoř jen stub, ne obsah.
- **A3: State Overwrite** — NESMÍ přepsat `phase/step` v existujícím `state.md` pokud jsou validní. Detection: `grep 'phase:' state.md | grep -vE 'orientation|planning|implementation|closing'`. Fix: Pouze doplň chybějící klíče.

---

## Self-check

Před návratem ověř:
- `{WORK_ROOT}/state.md` existuje a má parsovatelný YAML blok
- `{WORK_ROOT}/vision.md` existuje (i placeholder)
- `{WORK_ROOT}/backlog.md` existuje
- Všechny povinné adresáře existují: `backlog/`, `intake/`, `reports/`, `sprints/`, `analyses/`, `templates/`, `decisions/`, `specs/`, `reviews/`, `logs/`, `archive/`
- `{VISIONS_ROOT}/` existuje
- Všechny `TEMPLATES_REQUIRED` soubory existují v `{WORK_ROOT}/templates/`
- **Templates have valid YAML frontmatter with correct schema field** — Ověř, že každý template v `{WORK_ROOT}/templates/` má `schema:` v YAML bloku
- `COMMANDS.test` není `TBD` (pokud je → STOP, nelze bezpečně pokračovat)
- `COMMANDS.lint` a `COMMANDS.format_check` nejsou `TBD` (mohou být `""` = vypnuto)
- Init report existuje v `{WORK_ROOT}/reports/init-{YYYY-MM-DD}.md`
- `validate_fabric.py --workspace` PASS (nebo warnings only)

Pokud něco chybí → zapiš do init reportu jako CRITICAL + vytvoř intake item.

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
depends_on: []
feeds_into: [fabric-vision, fabric-architect, fabric-check, fabric-doctor, fabric-hotfix, fabric-intake, fabric-status]
phase: orientation
lifecycle_step: init
touches_state: true
touches_git: false
estimated_ticks: 1
idempotent: true
fail_mode: fail-closed
```

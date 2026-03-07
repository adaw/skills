---
name: fabric-sprint
description: "Create sprint plan from prioritized backlog by selecting top candidates respecting WIP=1 flow and constraints. Writes sprint-N.md with task queue, updates state.md with goal/dates, but does not implement code. Clear handoff to analyze."
---

<!-- built from: builder-template -->

# SPRINT — Plánování sprintu

---

## §1 — Účel

Vybrat nejlepší kandidáty z backlogu a vytvořit sprint plán (`sprints/sprint-{N}.md`) tak, aby:
- byl konzistentní s vizí,
- respektoval WIP=1 (single-piece flow),
- dal se bez ambiguity převést na konkrétní implementační tasky (`fabric-analyze` doplní `Task Queue`).

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-sprint" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-sprint" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/sprint-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "fabric-sprint" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř:

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

# --- Precondition 3: Backlog index existuje a je prioritizovaný ---
if [ ! -f "{WORK_ROOT}/backlog.md" ]; then
  echo "STOP: {WORK_ROOT}/backlog.md not found — run fabric-prio first"
  exit 1
fi

# --- Precondition 4: Templates existují ---
if [ ! -f "{WORK_ROOT}/templates/sprint-plan.md" ]; then
  echo "WARN: sprint-plan.md template not found"
fi

# --- Precondition 5: Vision existuje (for goal alignment) ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "WARN: {WORK_ROOT}/vision.md not found — sprint goal may not align with vision"
fi
```

**Dependency chain:** `fabric-prio` → [fabric-sprint] → `fabric-analyze`

**Git Safety (K4):** This skill does NOT perform git operations. K4 is N/A.

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (SPRINT pravidla + taxonomie)
- `{WORK_ROOT}/state.md` (aktuální sprint N)
- `{WORK_ROOT}/backlog.md` (prioritizovaný index)
- `{WORK_ROOT}/templates/sprint-plan.md` (kanonická šablona)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/vision.md` (pro zarovnání cílu sprintu)
- `{WORK_ROOT}/backlog/*.md` (detaily pro top kandidáty)

---

## §5 — Výstupy

### Primární (vždy)
- Sprint plan: `{WORK_ROOT}/sprints/sprint-{N}.md` (schema: `fabric.report.v1`, kind: sprint-plan)
- Report: `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/fabric-sprint-{slug}.md` (schema: `fabric.intake_item.v1`) — pokud jsou problémy

**State updates (pouze):**
- `sprint_started: <YYYY-MM-DD>`
- `sprint_ends: <YYYY-MM-DD>`
- `sprint_goal: "<goal>"`

---

## §6 — Deterministic FAST PATH

Než začneš vybírat položky do sprintu, vezmi deterministický backlog snapshot:

```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

Použij ho jako zdroj pravdy pro výběr top-PRIO položek.

---

## §7 — Postup (JÁDRO SKILLU)

Detailní postup je v `references/workflow.md`. Zde shrnutí klíčových kroků:

**7.1) Načti konfiguraci** — přečti `SPRINT.max_days`, `SPRINT.max_tasks`, `SPRINT.wip_limit` z config.md.

**7.2) Načti state a zjisti sprint N** — přečti `{WORK_ROOT}/state.md` → `active_sprint = N`. Ověř, že N je číslo (K2 fix).

**7.3) Načti backlog kandidáty** — vyfiltruj status NOT IN `DONE`, preferuj `READY` a `DESIGN`. Blockované items jen pro blocker tasks.

**7.4) Effort Estimation Algorithm** — vypočítej effort (XS/S/M/L/XL) podle FILES, TESTS, COMPLEXITY. Viz `references/workflow.md` sekce Effort Estimation.

**7.5) Vyber Sprint Targets** — max `SPRINT.max_tasks` položek, se zaměřením na fokus. Každý target musí mít effort, status, AC checkboxy.

**7.6) Dependency Graph & Ordering** — sestav tabulku depencí, topologicky seřaď, identifikuj critical path.

**7.7) Risk Assessment** — vyhodnoť HIGH/MEDIUM/LOW rizika per target. Pokud >2 HIGH items → zvýš WIP limit nebo sníž počet.

**7.8) Anti-Pattern Detection** — detekuj skryté rizika: module concentration, developer concentration, long critical path, příliš mnoho DESIGN items. Viz `references/workflow.md`.

**7.9) Pre-Sprint Gate (BLOCKING Validation)** — ověř kapacitu (≤90% utilization), žádné cyklické deps, všechny effort estimates, Definition of Done kompletní.

**7.10) Definition of Done (povinné)** — CHECKLIST formát, ne proza. Viz `references/workflow.md` pro template.

**7.11) Capacity Planning** — zkontroluj, že TOTAL_EFFORT ≤ SPRINT_CAPACITY. Cíl: 80-90% utilization.

**7.12) Rollover Tracking** — vezmi items z předchozího sprintu, co nejsou DONE. Analyzuj proč (underestimate, blocked, spec change). Napiš WARNINGy.

**7.13) Vytvoř sprint plán** — `{WORK_ROOT}/sprints/sprint-{N}.md` dle šablony. Vyplň: title, goal, start/end, Sprint Targets tabulka, Task Queue.

**7.14) Update state metadata** — nastav jen: `sprint_started`, `sprint_ends`, `sprint_goal`. Nesahej na `phase` nebo `step`.

**7.15) Vytvoř sprint report** — `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md` se summary, risks, analysis.

---

## §8 — Quality Gates

Skill nemá quality gates (je deterministický plán, ne kód). Ale ověř:

- **Gate: Schema validation** — Sprint plan má validní YAML frontmatter se schematem `fabric.report.v1`
- **Gate: Completeness** — Sprint plan má všechny povinné sekce (Sprint Targets, Task Queue, Definition of Done, Capacity Plan)

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/sprint-{N}-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: sprint
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# Sprint {N} Report — {YYYY-MM-DD}

## Souhrn
{1–3 věty: kolik targetů, jaký je cíl, jakou kapacitu máme}

## Sprint Targets vybrané
| Priority | ID | Type | Title | Effort |
|----------|----|----|-------|--------|
| 1 | T-XXX | Task | ... | S |

## Rizika a Mitigace
{Tabulka: Task, Risk Level, Mitigation}

## Rollover z předchozího sprintu
{Pokud existují carry-over items, seznam s důvody}

## Capacity Analysis
{Tabulka: Dev, Availability, Max Hours, Assigned, Headroom}

## Intake items vytvořené
{Seznam nebo "žádné"}

## Warnings
{Seznam nebo "žádné"}
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Sprint plan existuje: `{WORK_ROOT}/sprints/sprint-{N}.md`
- [ ] Sprint plan má validní YAML frontmatter se schematem `fabric.report.v1`
- [ ] Report existuje: `{WORK_ROOT}/reports/sprint-{YYYY-MM-DD}.md`
- [ ] Protocol log má START a END záznam s `skill: fabric-sprint`

### Quality checks (BLOCKING)
- [ ] **Sprint plán má povinné sekce**: Sprint Targets + Task Queue + Effort Capacity + Definition of Done
- [ ] **Každý target ID odpovídá existujícímu** `{WORK_ROOT}/backlog/{id}.md`
- [ ] **Effort sanity**: Suma effort estimates ≤ team capacity (z config.md TEAM_CAPACITY_POINTS)
- [ ] **Task Queue je seřazená** dle dependencies a risk (topological order)
- [ ] **Circular dependencies**: Task Queue neobsahuje A→B→A cykly
- [ ] **State metadata nastavena** (3 pole): `sprint_started`, `sprint_ends`, `sprint_goal`

### Invarianty
- [ ] Backlog.md NENÍ modifikován (sprint jen odkazuje)
- [ ] Backlog items si zachovávají status (ne prematurně READY)
- [ ] Žádný soubor mimo `{WORK_ROOT}/sprints/`, `{WORK_ROOT}/reports/`, `{WORK_ROOT}/state.md` nebyl modifikován
- [ ] Protocol log má START i END záznam

Pokud **ANY CRITICAL check FAIL** → **FAIL + vytvoř intake item `intake/sprint-plan-invalid-{date}.md`** + EXIT 1.

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí prereq soubor | STOP + jasná zpráva co chybí |
| FAST PATH | fabric.py selže | WARN + pokračuj manuálně |
| Effort Estimation | Nelze spočítat | WARN + use default S |
| Sprint Selection | Circular deps | STOP + intake item |
| Gate: Capacity | Utilization >90% | WARN + rebalance or STOP |
| Definition of Done | Neúplná | STOP + intake item |
| Self-check | Check FAIL | Report WARN + intake item |

Obecné pravidlo: Skill je fail-open vůči VOLITELNÝM vstupům (chybí → pokračuj s WARNING) a fail-fast vůči POVINNÝM vstupům (chybí → STOP).

---

## §12 — Metadata

```yaml
phase: planning
step: sprint_selection

may_modify_state: true         # jen SPRINT METADATA (started, ends, goal)
may_modify_backlog: false      # backlog je read-only
may_modify_code: false
may_create_intake: true

depends_on: [fabric-prio]
feeds_into: [fabric-analyze]
```

---

## Downstream Contract

**fabric-analyze** (next skill) reads sprint plan fields:
- `sprint_number` (int)
- `start_date`, `end_date` (ISO date strings)
- `sprint_targets[]` — table s columns: id, type, status, effort, title
- `definition_of_done[]` — checklist
- `task_queue[]` — ordered list (Order, ID, Type, Status, Estimate)
- `capacity_plan` — tabulka developer availability

---

## Poznámky pro autory

- **K2 Fix**: Sprint selection counter (max_tasks enforcement) v `references/workflow.md`
- **K7 Fix**: Path traversal guard v `references/workflow.md`
- **Příklady**: Konkrétní vyplněný sprint plán v `references/examples.md`
- **Detailní procedury**: Všechny kroky 7.1-7.15 v `references/workflow.md`

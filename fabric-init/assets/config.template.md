# Projektová konfigurace (runbook)

> Tento soubor je **jediný zdroj pravdy** pro runtime konfiguraci Fabricu.
> Obsahuje **DATA** (cesty, taxonomie, příkazy, quality gates), ne procedurální instrukce — ty jsou v `skills/`.
>
> **Pravidlo:** Každý skill MUSÍ načíst tento soubor jako první a nesmí hardcodovat cesty ani příkazy.

---

## Projekt

| Klíč | Hodnota |
|------|---------|
| Název | *(vyplní konkrétní projekt)* |
| Popis | *(vyplní konkrétní projekt)* |
| Jazyk | *(např. Python 3.12+, TypeScript, Go)* |
| Komunikace | *(jazyk skill textů — čeština, angličtina...)* |

---

## Cesty

```yaml
WORK_ROOT: fabric/                      # Runtime workspace (state, backlog, reporty, sprinty)
SKILLS_ROOT: skills/                    # Distribuované skills (portable)
CODE_ROOT: ./                       # Zdrojový kód
TEST_ROOT: tests/                       # Testy
DOCS_ROOT: docs/                        # Dokumentace
CONFIG_ROOT: config/                    # Runtime konfigurace projektu (mimo Fabric workspace, pokud existuje)
ANALYSES_ROOT: fabric/analyses/         # Výstupy analýz (task/solution design) – musí existovat
VISIONS_ROOT: fabric/visions/           # Sub-vize a rozšíření core vision.md
DECISIONS_ROOT: fabric/decisions/       # ADR / governance decisions (workspace)
SPECS_ROOT: fabric/specs/               # Technical specs (workspace)
REVIEWS_ROOT: fabric/reviews/           # Curated human/AI reviews (workspace)
TEMPLATES_ROOT: fabric/templates/       # Runtime šablony (workspace; vytváří bootstrap pokud chybí)
LOGS_ROOT: fabric/logs/                 # Protokol + debug (jsonl + md)

# Source-of-truth defaults (součást distribuce skills; bootstrap z nich kopíruje do workspace)
CANON_TEMPLATES_ROOT: skills/fabric-init/assets/templates/
CANON_VALIDATOR: skills/fabric-init/tools/validate_fabric.py
CANON_PROTOCOL_LOGGER: skills/fabric-init/tools/protocol_log.py

# Protokolové logy (machine + human)
PROTOCOL_LOG_JSONL: fabric/logs/protocol.jsonl
PROTOCOL_LOG_MD: fabric/logs/protocol.md
```

---

## Kontrakty (schema, enumerace, lifecycle, šablony)

> Tohle je **strojově čitelné API** mezi skills.
> Pokud se změní kontrakty tady, MUSÍ se upravit templates + skills zároveň.
> `fabric-check` a `fabric/tools/validate_fabric.py` tyto kontrakty ověřují.

```yaml
SCHEMA:
  backlog_item: fabric.backlog_item.v1
  intake_item: fabric.intake_item.v1
  sprint_plan: fabric.sprint_plan.v1
  state: fabric.state.v1
  reports: fabric.report.v1
  adr: fabric.adr.v1
  spec: fabric.spec.v1

ENUMS:
  statuses: [IDEA, DESIGN, READY, IN_PROGRESS, IN_REVIEW, BLOCKED, DONE]
  tiers: [T0, T1, T2, T3]
  efforts: [XS, S, M, L, XL, TBD]

  adr_statuses: [proposed, accepted, deprecated, superseded, rejected]
  spec_statuses: [draft, active, deprecated, superseded]

  # Typy backlog položek v {WORK_ROOT}/backlog/
  types: [Initiative, Epic, Story, Task, Bug, Chore, Spike]

  # Typy, které smí být v Sprint Task Queue (implementovatelné jednotky)
  task_types: [Task, Bug, Chore, Spike]

TEMPLATES_REQUIRED:
  - adr.md
  - audit-report.md
  - close-report.md
  - epic.md
  - intake.md
  - migration-report.md
  - review-summary.md
  - sprint-plan.md
  - state.md
  - status-report.md
  - spec.md
  - story.md
  - task.md
  - report.md
  - test-report.md

LIFECYCLE:
  orientation: [vision, status, architect, gap, generate, intake, prio]
  planning: [sprint, analyze]
  implementation: [implement, test, review]
  closing: [close, docs, check, archive]

RUN:
  # Fabric-loop execution window (user-triggered). Default behavior is deterministic.
  # Users can optionally add: `loop=<N>` (loops) or `loop=auto` to the fabric-loop prompt.
  max_loops_default: 1      # when no loop=... is provided
  max_loops_clamp: [1, 50]  # clamp for loop=<N>
  auto_max_loops: 100       # hard cap for loop=auto to prevent infinite loops
  max_ticks_per_loop: 25    # safety cap inside a single loop (auto-mode may raise this based on sprint size + rework limits)
  idle_step: idle           # sentinel step meaning "no actionable work"

  # Optional goal-aware stopping condition (used by fabric-loop and deterministic tooling)
  # goal maps -> tier_max, and work-status/tick can scope what counts as "remaining work".
  default_goal: release
  goals:
    mvp:
      tier_max: T0
    t1:
      tier_max: T1
    release:
      tier_max: null

# Deterministic IO contracts. Used by `fabric.py contract-check` and recommended in `fabric-loop`.
# Keep these conservative: existence checks only.
CONTRACTS:
  outputs:
    vision: ["reports/vision-*.md"]
    status: ["reports/status-*.md"]
    architect: ["reports/architect-*.md"]
    gap: ["reports/gap-*.md"]
    generate: ["reports/generate-*.md"]
    intake: ["reports/intake-*.md"]
    prio: ["reports/prio-*.md", "backlog.md"]
    sprint: ["sprints/sprint-*.md", "reports/sprint-*.md"]
    analyze: ["reports/analyze-*.md"]
    implement: ["reports/implement-*.md"]
    test: ["reports/test-*.md"]
    review: ["reports/review-*.md"]
    close: ["reports/close-*.md"]
    docs: ["reports/docs-*.md"]
    check: ["reports/check-*.md"]
    archive: ["reports/archive-*.md"]

QUALITY:
  # bootstrap = dovolí lint/format vypnout (""), ale nesmí být TBD.
  # strict = lint/format musí být nakonfigurované a běžet (nesmí být "" ani TBD).
  mode: bootstrap  # bootstrap | strict

GOVERNANCE:
  # Governance thresholds used by fabric-check / deterministic tooling.
  decisions:
    stale_proposed_days: 14
  specs:
    stale_draft_days: 30
  reviews:
    enabled: true

SAFETY:
  # Hard safety rules that the agent must never violate.
  forbid:
    - "git reset --hard"   # on shared branches (main). Use revert commits instead.
    - "git push --force"
    - "git push -f"
    - "git rebase"         # on published branches
    - "rm -rf"
    - "git clean -f"
  require_revert_on_main: true

```



**Portabilita:**
- Skills používají **výhradně** proměnné z tohoto YAML bloku.
- Hardcoded `fabric/`, `goden/`, `tests/`, `docs/` v skills je bug (výjimka: explicitní příklad, který MUSÍ být označen „PŘÍKLAD” a nesmí být normativní).

---

## Runtime příkazy

> Skills NESMÍ hardcodovat `pytest`, `ruff`, `jest`, atd.  
> Všechny příkazy se berou odsud.

**Semantika hodnot:**
- `TBD` = není nastaveno (konfigurační chyba). Skills mají vytvořit intake item a v gating krocích **FAILnout** (nebezpečné pokračovat naslepo).
- `""` (prázdné) = **explicitně vypnuto** (povoleno jen pro volitelné příkazy).

**Povinné:**
- `COMMANDS.test` musí být vždy **neprázdné** a nesmí být `TBD`.

```yaml
COMMANDS:
  # Unit + integration test suite (povinné)
  test: "TBD"

  # E2E (volitelné)
  test_e2e: ""

  # Lint
  lint: ""

  # Format check
  format_check: ""

  # Auto-fix lint/format
  lint_fix: ""
  format: ""
```

---

## Git konvence

### Commit messages

```
feat: {popis}      # nová feature
fix: {popis}       # oprava bugu
refactor: {popis}  # refaktoring bez změny chování
test: {popis}      # nové/upravené testy
docs: {popis}      # dokumentace
chore: {popis}     # tooling, config
```

### Branch strategie (trunk-based)

```yaml
GIT:
  main_branch: "main"
  merge_method: "squash"          # squash merge do main
  feature_branch_pattern: "{id}-{slug}"   # např. t0-async-router-impl
  max_branch_age_days: 3
```

---

## Quality Gates

| Gate | Threshold | Akce při porušení |
|------|-----------|-------------------|
| Review CRITICAL findings | ≥ 1 | Block merge, rework |
| Review WARNING findings | ≥ 5 | Vytvořit intake items |
| Check CRITICAL findings | ≥ 1 | Block release |
| Rework iterace per task | > 3 | Eskalace do analyze |
| Lint errors | > 0 | Block merge *(jen pokud `COMMANDS.lint` není prázdné)* |
| Format diffs | > 0 | Block merge (auto-fixable) *(jen pokud `COMMANDS.format_check` není prázdné)* |

> Coverage gates jsou projektově specifické – pokud je chcete vynucovat, doplňte je sem.

---

## Sprint pravidla (machine-readable)

```yaml
SPRINT:
  wip_limit: 1                 # single-piece flow
  max_days: 5                  # agentní práce
  max_tasks: 10                # v task queue (po analýze)
  max_rework_iters: 3          # review→implement loop
  archive_min_age_days: 14     # jak staré DONE items mohou jít do archive snapshotu
```

---

## Backlog struktura

**FLAT struktura** — všechny backlog položky v jednom adresáři.  
Žádné `epics/`, `stories/`, `tasks/` podadresáře.

### Umístění

```
{WORK_ROOT}/backlog/         # Aktivní položky (flat)
{WORK_ROOT}/backlog/done/    # DONE položky po uzavření a archivaci (stále čitelné)
```

### Kanonické schema backlog itemu

Každý backlog item je soubor: `{WORK_ROOT}/backlog/{id}.md`

```markdown
---
id: t0-async-router
title: "Async Router"
type: Epic | Story | Task | Bug | Chore | Spike
tier: T0 | T1 | T2 | T3
status: IDEA | DESIGN | READY | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE
effort: TBD | XS | S | M | L | XL
created: 2026-02-28
updated: 2026-02-28         # volitelné, ale doporučené
source: manual | legacy | generate | gap | arch | review | check | intake
prio: 0                      # integer; počítá fabric-prio
depends_on: []               # volitelné; list backlog IDs
blocked_by: []               # volitelné; list backlog IDs
branch: null                 # volitelné; naplní fabric-implement (např. "t0-async-router-impl")
review_report: null          # volitelné; naplní fabric-review (např. "reports/review-2026-02-28.md")
merge_commit: null           # volitelné; naplní fabric-close (commit sha)
---

## Příkaz odemykující
Jedna věta: proč to existuje (hodnota/risiko/rychlost).

## Popis
...

## Acceptance Criteria
- [ ] ...

## Dotčené soubory
- `{CODE_ROOT}/...`
- `{TEST_ROOT}/...`
- `{DOCS_ROOT}/...`

## Poznámky
...
```

**Poznámka:** H1 (`# ...`) je volitelné. Kanonický název je `title:` ve frontmatter.


### Význam statusů

| Status | Význam | Kdo typicky mění |
|--------|--------|------------------|
| IDEA | Hrubý nápad, neimplementovatelné bez doplnění | intake/generate/gap |
| DESIGN | Potřebuje analýzu/rozhodnutí (chybí AC, otevřené otázky) | analyze |
| READY | Specifikace je dostatečná pro implementaci | analyze |
| IN_PROGRESS | Aktivně se implementuje (WIP=1) | implement |
| IN_REVIEW | Implementace hotová, čeká/řeší review | implement/review |
| DONE | Review prošlo a item je připraven na merge/uzavření | review/close |
| BLOCKED | Nelze pokračovat (dependency, env, external) | kdokoliv (s evidencí) |

> Poznámka: `DONE` v tomto workflow znamená „ready for merge/closure“. Samotný merge do `main` probíhá v `fabric-close`.


### Backlog index

`{WORK_ROOT}/backlog.md` je lightweight index (tabulka). Detail je v per-item souborech.

Minimální tabulka:

```markdown
# Backlog Index

| ID | Title | Type | Status | Tier | Effort | PRIO |
|----|-------|------|--------|------|--------|------|
| t0-async-router | Async Router | Epic | DESIGN | T0 | XL | 22 |
```

Index se regeneruje při `intake`, `prio`, `close`.

---

## Intake struktura

Intake items jsou surové vstupy (nápad, finding, gap). Každý intake item je 1 soubor v `{WORK_ROOT}/intake/`.

```
{WORK_ROOT}/intake/*.md
{WORK_ROOT}/intake/done/
{WORK_ROOT}/intake/rejected/
```

**Kanonické schema intake itemu** (viz `templates/intake.md`):

```markdown
---
id: INTAKE-2026-0001
title: "Přidat X"
source: manual | legacy | generate | gap | arch | review | check
date: 2026-02-28
created_by: "fabric"
initial_type: Epic | Story | Task | Bug | Chore | Spike
raw_priority: 1        # 1-10 (hrubý signál; finální PRIO dělá fabric-prio)
linked_vision_goal: "" # volitelné
---

## Popis
...

## Kontext
...

## Doporučená akce
...
```

---

## Sprint plán – kontrakt (NEPORUŠIT)

Sprint plán je soubor: `{WORK_ROOT}/sprints/sprint-{N}.md`

**Kanonická šablona:** `templates/sprint-plan.md`

Povinné sekce:
- `## Sprint Targets` – výběr backlog položek (může obsahovat epics/stories)
- `## Task Queue` – implementační fronta (pouze Task/Bug/Chore/Spike).  
  Tuto sekci může vytvořit/změnit `fabric-analyze` (rozpad, dependency ordering).

---

## Analýzy

`fabric-analyze` vytváří návrhy řešení pro konkrétní tasks:

- Umístění: `{ANALYSES_ROOT}/`
- Název: `{id}-analysis.md` (např. `t1-export-excel-analysis.md`)

---

## State.md formát

`{WORK_ROOT}/state.md` je kanonický zdroj pravdy o pozici v lifecycle.

```yaml
phase: orientation | planning | implementation | closing
step: idle | vision | status | architect | gap | generate | intake | prio | sprint | analyze | implement | test | review | close | docs | check | archive
sprint: 1
wip_item: null | "t0-async-router"
wip_branch: null | "t0-async-router-impl"
last_completed: null | "archive"
last_run: 2026-02-28
error: null | "popis chyby"

# Sprint metadata (set by fabric-sprint)
sprint_started: null
sprint_ends: null
sprint_goal: null
```

## History (volitelné)

Pod YAML blokem ve `state.md` může být append-only tabulka:

| Date | Step | Result | Note |
|------|------|--------|------|

`fabric-loop` ji může doplňovat jako audit trail.


### State ownership (neprůstřelné pravidlo)

- `fabric-loop` je jediný, kdo smí měnit: `phase`, `step`, `last_completed`, `last_run`, `error`, a `History`.
- `fabric-loop` může bezpečně resetovat `wip_item`/`wip_branch` při přechodu na další task (multi-task sprint).
- Skills smí měnit pouze:
  - `fabric-sprint`: `sprint_started`, `sprint_ends`, `sprint_goal`
  - `fabric-implement`: `wip_item`, `wip_branch`
  - `fabric-close`: může resetovat `wip_item` a `wip_branch` na `null` po uzavření sprintu
  - ostatní skills: NESMÍ měnit state (jen generují své artefakty)

---

## Lifecycle sekvence

```
FÁZE 0: ORIENTACE
  vision → status → architect → gap → generate → intake → prio

FÁZE 1: PLÁNOVÁNÍ
  sprint {N} → analyze

FÁZE 2: IMPLEMENTACE (per task, WIP=1)
  implement → test → review
  (rework loop: review → implement → test → review, max 3×)

FÁZE 3: UZAVŘENÍ
  close → docs → check → archive
```

---

## Soubory v {WORK_ROOT}/

| Soubor / adresář | Účel | Kdo zapisuje |
|------------------|------|-------------|
| `config.md` | Tento soubor | Manuálně (nebo init template) |
| `state.md` | Orchestrátor state | fabric-loop (+ sprint/implement dílčí pole) |
| `vision.md` | Vize projektu | fabric-init / manuálně |
| `backlog.md` | Backlog index | fabric-intake, fabric-prio, fabric-close |
| `backlog/*.md` | Backlog items | fabric-intake (+ implement/review/close doplňuje metadata) |
| `backlog/done/` | DONE items (po uzavření) | fabric-archive |
| `intake/*.md` | Surové vstupy | generate/gap/architect/review/check (+ manuálně) |
| `intake/done/` | Zpracované intake items | fabric-intake |
| `intake/rejected/` | Zamítnuté intake items (s důvodem) | fabric-intake |
| `sprints/*.md` | Sprint plány | fabric-sprint (+ analyze upravuje Task Queue) |
| `analyses/*.md` | Analýzy per task | fabric-analyze |
| `reports/*.md` | Reporty | všechny skills |
| `templates/*.md` | Šablony | fabric-init (kopie/validace) |
| `archive/` | Imutabilní snapshoty a provenance | fabric-archive (+ init) |

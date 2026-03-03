# Fabric Skills

Fabric je deterministický lifecycle framework pro LLM‑driven development. Poskytuje agentovi strukturovaný stavový automat, jasné kontrakty mezi kroky a nástroje pro mechanickou práci (IO, patchování, logování), aby se LLM mohl soustředit na přemýšlení, návrh a generování řešení. Framework je přenositelný přes adresář skills/ a vytváří si vlastní runtime workspace.

## Preflight (lokálně)
- Spust: `Načti a proveď skills/fabric-init/SKILL.md`


## Jediný entrypoint

Spuštění Fabricu začíná vždy tady:

- `skills/fabric-loop/SKILL.md`

> Pokud kopíruješ Fabric do jiného projektu, stačí zkopírovat **celý adresář `skills/`**.
> Workspace (`{WORK_ROOT}`, typicky `fabric/`) se vytvoří bootstrapem (`fabric-init`).

### Spuštění (minimální prompt)

- `Načti a proveď skills/fabric-loop/SKILL.md` *(default: 1 tick)*
- volitelně: `Načti a proveď skills/fabric-loop/SKILL.md loop=10` *(max 10 ticků v jednom spuštění)*
- volitelně: `Načti a proveď skills/fabric-loop/SKILL.md loop=auto` *(běž dokud je co dělat; hard-cap dle configu)*


## Protokolování (debug)

Každý skill má povinné START/END logování přes:

- `skills/fabric-init/tools/protocol_log.py`

Výstup:
- `{WORK_ROOT}/logs/protocol.jsonl` (machine)
- `{WORK_ROOT}/logs/protocol.md` (human)


## Deterministický toolset (šetří tokeny)

LLM má dělat rozhodování, ne “mkdir/cp/patch yaml”.

Pro opakovatelné mechanické operace používej:

- `skills/fabric-init/tools/fabric.py`

Typicky:
- `bootstrap` (skeleton + templates + state/backlog)
- `backlog-scan` / `intake-scan` (strojové snapshoty)
- `intake-new` (deterministická tvorba intake itemu z template)
- `apply` (plan → deterministický patch)
- `run` (COMMANDS.* s log capture)
- `gate-test` (COMMANDS.test + parsovatelný test report)
- `contract-check` (IO kontrakty pro step)
- `run-report` (run timeline report)
- `evidence-pack` (ZIP evidence pro debug/escalaci)

---

---

## Přehled (18 skills)

### Orientace (Fáze 0)

| Skill | Účel |
|-------|------|
| **fabric-init** | Bootstrap runtime {WORK_ROOT}/ (adresáře, templates, state, vision, backlog) |
| **fabric-vision** | Ověření a údržba zarovnání vize s reálnou prací |
| **fabric-status** | Holistický health snapshot projektu (metriky, trendy, rizika) |
| **fabric-architect** | Architektonický audit codebase (coupling, debt, patterns) |
| **fabric-gap** | Detekce mezer mezi vizí, backlogem a kódem |
| **fabric-generate** | Autonomní discovery práce z 6 úhlů (code health, testy, docs, perf, security, DX) |
| **fabric-intake** | Třídění a normalizace surových nápadů do backlogu |
| **fabric-prio** | Evidence-based prioritizace backlogu (PRIO vzorec) |

### Plánování (Fáze 1)

| Skill | Účel |
|-------|------|
| **fabric-sprint** | Sprint plánování s kapacitou, dekompozicí a dependency ordering |
| **fabric-analyze** | Hloubková pre-implementační analýza (impact, interface, testy, rizika) |

### Implementace (Fáze 2)

| Skill | Účel |
|-------|------|
| **fabric-implement** | Psaní production kódu s verify-first přístupem |
| **fabric-test** | Vícevrstvé testování, coverage delta, detekce regresí a flaky testů |
| **fabric-review** | Code review v 8 dimenzích (R1-R8) s auto-fix a evidence-based findings |

### Uzavření (Fáze 3)

| Skill | Účel |
|-------|------|
| **fabric-close** | Uzavření sprintu — merge, DoD ověření, velocity metriky, lessons learned |
| **fabric-docs** | Synchronizace dokumentace s kódem (drift detection, auto-update) |
| **fabric-check** | Komplexní audit konzistence (backlog, kód, testy, docs) |
| **fabric-archive** | Archivace dokončených artefaktů (append-only, checksums) |

### Orchestrace

| Skill | Účel |
|-------|------|
| **fabric-loop** | Lifecycle orchestrátor — automatická detekce stavu a dispatch skills |

## Technické specifikace

- **Jazyk:** Čeština v textu, angličtina ve frontmatter
- **Formát:** YAML frontmatter + Markdown body
- **Portabilita:** Žádná vendor-specific syntax, funguje s jakýmkoliv LLM
- **Cesty:** `{WORK_ROOT}`, `{CODE_ROOT}`, `{TEST_ROOT}` z config.md

## Použití

Každý skill čte `{WORK_ROOT}/config.md` jako první. Orchestrátor (`fabric-loop`) automaticky detekuje stav z `{WORK_ROOT}/state.md` a spouští příslušný skill.

---

*Vytvořeno: 2026-02-28*

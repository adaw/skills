# Fabric Templates — runtime šablony (workspace)

Tyto soubory jsou **runtime šablony** používané skill‑y při generování artefaktů v `{WORK_ROOT}`.

## Důležité: odkud se berou

- **Source-of-truth defaults** jsou součást distribuce: `skills/fabric-init/assets/templates/`
- Při bootstrapu (`fabric-init`) se tyto defaulty **zkopírují** do `{WORK_ROOT}/templates/` **jen pokud chybí**.
- Pokud runtime šablony upravíš, bootstrap je **nepřepíše** (záměrně) — drift je povolen, ale měl by být vědomý.
- Validátor (`skills/fabric-init/tools/validate_fabric.py`) kontroluje, že runtime templates obsahují minimálně `TEMPLATES_REQUIRED`.

---

## Seznam klíčových šablon

- `intake.md` — jeden intake item (idea/finding/gap) → později triage do backlogu
- `epic.md`, `story.md`, `task.md` — backlog itemy (hierarchie a metadata)
- `sprint-plan.md` — plán sprintu (WIP=1 + quality gates)
- `review-summary.md` — review výstup (R1–R8)
- `status-report.md` — health snapshot (stav runtime, CI, testy, rizika)
- `audit-report.md` — konzistenční audit / self-check
- `close-report.md` — sprint closure / velocity / merge evidence
- `migration-report.md` — migrace/transformace (pokud existuje)
- `state.md` — šablona pro `{WORK_ROOT}/state.md` (strojově čitelné YAML + lidský kontext)
- `adr.md` — Architecture Decision Record (rozhodnutí + trade-offs)
- `report.md` — **generická šablona reportu pro skill**, pokud pro daný skill neexistuje specializovaná šablona

---

## Pravidlo

Pokud skill generuje nový soubor, musí vycházet ze šablony:

- buď specializované (`status-report.md`, `close-report.md`…)
- nebo generické (`report.md`)

Cíl: žádná improvizace v hlavičkách, konzistentní metadata, snadná automatická validace a audit.

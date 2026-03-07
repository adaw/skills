---
name: fabric-hotfix
description: "Ad-hoc implementation outside sprint planning: analysis, code, tests, review, and merge in one dispatch. For urgent XS/S fixes and small features with full quality gates and fast-track lifecycle."
---
<!-- built from: builder-template -->

# HOTFIX — Ad-hoc implementace mimo sprint (fast-track)

---

## §1 — Účel

Rychlá implementace malých fixů a features **mimo sprint plánování**. Kompletní mini-lifecycle
v jednom dispatch: analýza → kód → testy → review → merge → report.

Bez tohoto skillu urgentní fixy buď blokují sprint (čekají na další cyklus),
nebo se dělají ad-hoc bez quality gates (regrese).

**Kdy použít:**
- XS/S effort (max 1 den práce)
- Urgentní bug fix nebo drobná feature
- Infrastrukturní vylepšení (tooling, config, DX)
- Cokoli co nestojí za celý sprint

**Kdy NEPOUŽÍT:**
- M/L/XL effort → plný sprint (fabric-sprint → fabric-implement)
- Architektonické změny → fabric-design → sprint
- Nová feature vyžadující specifikaci → fabric-intake → fabric-design → sprint

---

## §2 — Protokol (povinné — NEKRÁTIT)

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "hotfix" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "hotfix" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "hotfix" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

Hotfix NEMÁ sprint prereqs — celý smysl je obejít sprint planning. Ale potřebuje:

**5 povinných kontroly:**
1. Config existuje: `{WORK_ROOT}/config.md`
2. State existuje: `{WORK_ROOT}/state.md`
3. COMMANDS.test nakonfigurován (ověř v config.md)
4. Git working tree čistý (no uncommitted changes)
5. Effort guard: akceptuj jen effort z config.md `HOTFIX.max_effort` (default: XS,S; M+ → doporuč sprint)

# K6: Dependency enforcement — init must have run
if [ ! -f "{WORK_ROOT}/config.md" ] || [ ! -f "{WORK_ROOT}/state.md" ]; then
  echo "STOP: fabric-init must run first (config.md or state.md missing)"
  exit 1
fi
# K6: Checks 1-2 above enforce fabric-init dependency ✓

**Detail implementace viz:** `references/preconditions.md`

**Dependency chain:** `fabric-init → [tento skill] (bez dalších prereqs)`

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (COMMANDS, GIT, cesty)
- `{WORK_ROOT}/state.md` (aktuální stav — hotfix ho NESMÍ modifikovat kromě wip)
- Popis požadavku od uživatele (text — co má hotfix udělat)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/backlog/{id}.md` — pokud hotfix řeší existující backlog item
- `{WORK_ROOT}/decisions/` — pro governance cross-check
- `{WORK_ROOT}/specs/` — pro compliance check
- `dev/workflows/hotfix.md` — referenční kvalita starého workflow

---

## §5 — Výstupy

### Primární (vždy)
- Merge commit na main (squash merge hotfix branch)
- Report: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Backlog item: `{WORK_ROOT}/backlog/{id}.md` (nový nebo aktualizovaný → DONE)
- Intake items: `{WORK_ROOT}/intake/hotfix-{slug}.md` (pokud findings)
- Regenerovaný `{WORK_ROOT}/backlog.md` (po merge)

---

## §6 — Deterministic FAST PATH

```bash
# 1. Backlog index sync (pokud hotfix pracuje s backlogem)
python skills/fabric-init/tools/fabric.py backlog-index 2>/dev/null || true

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null || true

# 3. Zjisti hlavní branch
MAIN_BRANCH=$(grep 'main_branch:' "{WORK_ROOT}/config.md" | awk '{print $2}')
MAIN_BRANCH=${MAIN_BRANCH:-main}
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### State Validation (K1: State Machine)
Check current phase is compatible with this skill. Valid phases: `implementation`, `closing`.

### Path Traversal Guard (K7: Input Validation)
Reject any input containing `..` (path traversal attack prevention).

### Counter Initialization (K2)

```bash
MAX_RETRIES=${MAX_RETRIES:-3}
LINT_RETRY_COUNT=0
FORMAT_RETRY_COUNT=0

# K2: Numeric validation
if ! echo "$MAX_RETRIES" | grep -qE '^[0-9]+$'; then
  MAX_RETRIES=3
  echo "WARN: MAX_RETRIES not numeric, reset to default (3)"
fi
```

### H1: Analýza požadavku
Pochop co hotfix má udělat, ověř effort, zkontroluj backlog.
**Detail:** `references/h1-analysis.md`

### H2: Implementace
Kód + minimálně 3 testy (happy/edge/error) na dedikované hotfix branch.
**Detail:** `references/h2-implementation.md`

### H3: Quality Gates
Spusť lint + testy (K2 guards: LINT_RETRY_COUNT, FORMAT_RETRY_COUNT numeric validation).
**Detail:** `references/h3-quality-gates.md`

### H4: Fast-track Review (self-review)
Quick review hotfix diff PŘED merge (R1–R4 dimenze: správnost, error handling, bezpečnost, testy).
**Detail:** `references/h4-review.md`

### H5: Commit + Merge
Commitni na hotfix branch, squash merge do main, post-merge test run POVINNÝ.
**Detail:** `references/h5-commit-merge.md`

### H6: Backlog + Docs Update
Aktualizuj backlog item na DONE, regeneruj index, updatuj docs pokud se týká.
**Detail:** `references/h6-backlog-docs.md`

### H7: Report
Hotfix report se souhrnem evidence (schema: fabric.report.v1).
**Detail:** `references/h7-report.md`

---

### K10: Inline Anti-patterns

- **A1: Hot-fixing M-effort tasks** → STOP, doporuč sprint místo hotfix
- **A2: Hotfix bez testů** → NESMÍ mergovat bez min. 3 testů (happy/edge/error)
- **A3: Force push na main** → ZAKÁZÁNO, vždy squash merge z hotfix branch
- **A4: Skip lint/format** → NESMÍ přeskočit; auto-fix max MAX_RETRIES pokusů

---

## §8 — Quality Gates

Four gates (detailed viz `references/quality-gates-summary.md`):
1. **Lint** — timeout 120s, auto-fix with K2 guards
2. **Format Check** — timeout 120s, auto-fix with K2 guards
3. **Tests (pre-merge)** — timeout 300s, MUST PASS
4. **Tests (post-merge)** — timeout 300s, MUST PASS (else revert)

---

## §9 — Report

Hotfix report path: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md`

Schema: `fabric.report.v1` with status, task_id, effort, merge_commit, evidence table, changed files.

**Template viz:** `references/h7-report.md`

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/hotfix-{YYYY-MM-DD}-{run_id}.md`
- [ ] Backlog item existuje a má `status: DONE`
- [ ] Merge commit existuje na main: `git log --oneline -1 | grep "${TASK_ID}"`

### Quality checks
- [ ] Post-merge tests PASS
- [ ] Hotfix branch smazaná (ne na lokálu, ne na remote)
- [ ] Backlog index regenerován
- [ ] Report má schema frontmatter se status
- [ ] Minimálně 3 testy byly napsány/aktualizovány (happy/edge/error)
- [ ] Self-review proběhl na 4 dimenze (R1–R4)

### Invarianty
- [ ] Hotfix nezměnil `state.md` (phase/step/sprint) — jen wip_item/wip_branch
- [ ] Protocol log obsahuje START i END záznam
- [ ] Žádný `git push --force` nebyl proveden
- [ ] Working tree je čistý po dokončení

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Config/state chybí | STOP + „run fabric-init first" |
| Preconditions | Effort > S | STOP + „use fabric-sprint" |
| Preconditions | Dirty working tree | STOP + „commit or stash first" |
| H2 Implementace | Testy stále failing | Oprav testy (max 3 iterace) → FAIL + intake item |
| H3 Quality Gates | Lint FAIL po auto-fix | Oprav manuálně → pokud stále FAIL → intake item |
| H3 Quality Gates | Tests TIMEOUT (124) | WARN + intake item pro slow tests |
| H4 Review | R1/R2/R3 finding | Oprav PŘED merge (nečekej) |
| H5 Merge | Merge conflict | Abort merge → intake item → manuální resolution |
| H5 Merge | Post-merge tests FAIL | `git revert --no-edit HEAD` → intake item |
| H5 Merge | Revert FAIL (conflict) | `git revert --abort` → CRITICAL → manuální intervence |

**Obecné pravidlo:** Hotfix je fail-fast — při jakémkoli problému raději STOP než riskovat regresi na main.

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: utility
step: hotfix

# Oprávnění
may_modify_state: false        # hotfix nesmí měnit phase/step/sprint
may_modify_backlog: true       # vytváří/aktualizuje backlog items
may_modify_code: true          # implementuje kód + testy
may_create_intake: true        # při failures

# Pořadí v pipeline
depends_on: [fabric-init]      # jen init — hotfix obchází sprint planning
feeds_into: [fabric-check]     # po hotfix je vhodné spustit check
```

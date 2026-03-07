---
name: fabric-checker
description: "Read-only audit of the entire fabric ecosystem. Scores each skill 0-100, runs extreme simulations, and evaluates work quality. Never modifies anything—only produces scoring report with findings for fabric-builder to fix."
tags: [fabric, audit, scoring, read-only, quality-gates]
depends_on: [fabric-builder]
feeds_into: [fabric-builder]
---

# FABRIC-CHECKER — Read-only Audit & Scoring

> **Tento skill NIKDY nic nemodifikuje.** Pouze čte, hodnotí a reportuje.
> Opravy, tvorbu a migraci skills provádí `fabric-builder`.
>
> Flow: **checker** → findings report → **builder fix** → **checker** → ověření

---

## Kdy spustit

- Po jakémkoli zásahu do fabric skills (ověření že nic není rozbité)
- Po `fabric-builder build/fix/migrate` (ověření výsledku)
- Před spuštěním sprintu (zdravotní kontrola)
- Kdykoli chceš vidět skóre a stav fabricu

## Parametry

```
fabric-checker                    # plný audit (default)
fabric-checker scope=quick        # jen scoring bez simulací
fabric-checker scope=deep         # scoring + simulace + work-quality
fabric-checker target=implement   # audit jen jednoho skillu
```

---

## Klasifikace skills (důležité — čti PŘED auditem)

### Tier 1: Orchestrátory (JINÁ pravidla)

Tyto skills ŘÍDÍ ostatní — mají vlastní logiku, kterou nelze vtěsnat do builder-template.
Audituj je na K1–K10, ale **NE na template compliance (Fáze 4)**.

| Skill | Proč je speciální |
|-------|-------------------|
| `fabric-loop` | State machine orchestrátor. Řídí step transitions, idle detection, blocker escalation. Celý skill JE postup — nemá §7 v běžném smyslu. |
| `fabric-init` | Bootstrap. Vytváří workspace od nuly. Nemá prereqs (je sám prereq všeho). |

### Tier 2: Builder-born skills (PLNÝ audit + template compliance)

Skills vytvořené přes `fabric-builder build`. Audituj na K1–K10 **A** na template compliance (Fáze 4).

Jak poznat builder-born skill:
- Má v SKILL.md komentář `<!-- built from: builder-template -->`

```
# Builder-born skills (doplňuj při vytváření nových):
# (zatím žádné — fabric-design bude první)
```

### Tier 3: Legacy skills (scoring K1–K10, BEZ template compliance)

Všechny ostatní existující skills. Vznikly PŘED builder-template.
Audituj na K1–K10, ale **NEPOROVNÁVEJ s template** — generovalo by to false positives.

### META: Checker a Builder jsou nedotknutelné

- `fabric-checker` NEAUDITUJE sám sebe ANI `fabric-builder`
- `fabric-builder` NEOPRAVUJE sám sebe ANI `fabric-checker`
- Opravy checker/builder se dělají VÝHRADNĚ manuálně (člověk + LLM v přímé konverzaci)

---

## FÁZE 0 — Inventura

### 0.1) Seznam všech fabric skills + klasifikace

```bash
for SKILL_FILE in skills/fabric-*/SKILL.md; do
  SKILL_DIR=$(dirname "$SKILL_FILE")
  SKILL_NAME=$(grep '^name:' "$SKILL_FILE" | head -1 | sed 's/name:\s*//')
  LINES=$(wc -l < "$SKILL_FILE")

  case "$SKILL_NAME" in
    fabric-loop|fabric-init)    TIER="T1-orchestrator" ;;
    fabric-checker|fabric-builder) TIER="SKIP-meta" ;;
    *)
      if grep -q 'built from: builder-template' "$SKILL_FILE" 2>/dev/null; then
        TIER="T2-builder-born"
      else
        TIER="T3-legacy"
      fi
      ;;
  esac

  echo "$TIER | $SKILL_NAME | $LINES lines | $SKILL_DIR"
done
```

### 0.2) Co auditujeme per tier

| Tier | K1–K10 Scoring | Simulace (F2) | Work Quality (F3) | Template Compliance (F4) |
|------|:-:|:-:|:-:|:-:|
| T1 orchestrátory | ANO | ANO | ADAPTOVANĚ* | NE |
| T2 builder-born | ANO | ANO | ANO | **ANO** |
| T3 legacy | ANO | ANO | ANO | NE |
| SKIP (checker + builder) | — | — | — | — |

*\* Pro orchestrátory: K10 se hodnotí jinak — „je logika kompletní a deterministická?" místo „má §7 šablony výstupu?"*

### 0.3) Podpůrné soubory pro audit

- `fabric/config.md` — konfigurace (čti CELÝ)
- `fabric/state.md` — aktuální stav
- `skills/fabric-builder/assets/builder-template.md` — kanonická šablona (pro Fázi 4)
- `fabric/reports/work-quality-analysis-*.md` — předchozí analýza kvality (pokud existuje)
- `dev/workflows/*.md` — historické workflow soubory (referenční kvalita, pokud existují)

---

## FÁZE 1 — Scoring Audit (10 kategorií × 10 bodů = 100)

**POVINNÉ: Přečti KAŽDÝ skill CELÝ (včetně řádků za 1000!). Přečti config.md CELÝ.**

### K1: Stavový stroj (10b)
- [ ] Skill správně čte state.md a respektuje aktuální phase/step
- [ ] Skill NEMODIFIKUJE state.md (pokud nemá `may_modify_state: true`)
- [ ] Přechody jsou explicitní a dokumentované
- [ ] Idle/error stavy jsou ošetřeny
- **0b** pokud skill ignoruje state.md nebo modifikuje bez oprávnění

### K2: Counter & Termination (10b)
- [ ] Všechny smyčky mají explicitní terminační podmínku
- [ ] Countery jsou: inicializované, numericky validované, persistované, omezené maximem
- [ ] Max iterací: loop ≤ 50, rework ≤ 5, autofix ≤ 3
- **0b** pokud existuje neomezená smyčka nebo counter bez validace

### K3: Error Handling (10b)
- [ ] Každý bash příkaz má error handling (|| fallback NEBO set -e)
- [ ] Failure v FAST PATH: WARN + manuální fallback
- [ ] Failure v Postupu: STOP + protocol error + intake item
- [ ] 3-level fallback chain pro destruktivní operace (merge, rebase)
- [ ] Timeout handling (exit code 124 detection)
- **0b** pokud skill může tiše selhat bez záznamu

### K4: Git Safety (10b)
- [ ] VŠECHNY proměnné v git příkazech jsou quotované: `"${var}"`
- [ ] Žádný `git push --force`
- [ ] Žádný `git reset --hard` na main (pouze na feature branch s PRE záchytným bodem)
- [ ] Merge conflict handling s abort chain
- [ ] Commit messages quotované
- **0b** pokud existuje unquoted proměnná v git příkazu

### K5: Contracts & Config (10b)
- [ ] Skill čte cesty z config.md (ne hardcoded)
- [ ] COMMANDS nejsou hardcoded
- [ ] Schema reference v outputech (frontmatter)
- [ ] Enum values odpovídají config.md ENUMS
- **0b** pokud skill má hardcoded cestu mimo config.md

### K6: Temporální kauzalita (10b)
- [ ] Preconditions mají bash kód (ne jen text)
- [ ] Prerequisite soubory jsou ověřeny PŘED prací
- [ ] Dependency chain je dokumentován
- [ ] STOP zpráva říká KTERÝ skill chybějící prereq vytváří
- **0b** pokud skill začne pracovat bez ověření prereqs

### K7: Input Validation (10b)
- [ ] User parametry jsou validované (regex, range, type)
- [ ] Path traversal prevence
- [ ] Numerické vstupy: `grep -qE '^[0-9]+$'` guard
- [ ] Timeout bounds (min/max z config.md)
- **0b** pokud skill přijímá raw user input bez validace

### K8: Audit & Governance (10b)
- [ ] Protokol START/END je přítomen a kompletní
- [ ] Report má schema frontmatter
- [ ] Report má status (PASS/WARN/FAIL)
- [ ] Intake items mají schema + source + raw_priority
- **0b** pokud chybí protokol logging

### K9: Self-Check (10b)
- [ ] Self-check sekce existuje
- [ ] Má ≥3 testovatelné položky
- [ ] Kontroluje EXISTENCI výstupů
- [ ] Kontroluje KVALITU výstupů
- [ ] Kontroluje INVARIANTY
- **0b** pokud self-check chybí nebo je triviální

### K10: Dokumentace & Work Quality (10b)
- [ ] Postup je KONKRÉTNÍ — ne vágní
- [ ] Obsahuje PŘÍKLADY nebo ŠABLONY výstupu
- [ ] Definuje MINIMUM akceptovatelného výstupu
- [ ] Definuje ANTI-PATTERNS
- [ ] Instrukce dostatečné pro JINÉHO LLM bez kontextu
- [ ] Pokud implementuje: min. test set (3: happy/edge/error)
- [ ] Pokud analyzuje: alternativy + pseudokód
- [ ] Pokud reviewuje: fix strategie per finding typ
- [ ] Deep quality checks (DQ1-DQ6) provedeny pokud scope=deep
- **0b** pokud postup obsahuje jen vágní „udělej X"

### Scoring pravidla

```
Per kategorie: 10 (vše OK) | 8 (1 minor) | 5 (podstatné mezery) | 3 (slabé) | 0 (chybí/kritické)

DOSAŽITELNÉ body:
  N/A kategorie se odečtou z maxima.
  Finální % = dosažené / dosažitelné × 100
```

### Výstupní formát Fáze 1

```md
## Souhrnná tabulka

| Skill | Tier | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 | K9 | K10 | Score | Max | % |
|-------|------|----|----|----|----|----|----|----|----|----|----|-------|-----|-----|

## Per-skill findings

### {skill_name} (Tier {X})
| Kat | Body | Nález | Evidence (řádek) | Priorita |
|-----|------|-------|-------------------|----------|
```

---

## FÁZE 2 — Extrémní simulace (3 typy)

> Spouštěj jen pokud `scope=deep` nebo default.

### S1: Formální invarianty

Pro každý skill ověř:

| ID | Invariant | Co hledat |
|----|-----------|-----------|
| I1 | Idempotence | Append bez dedup, counter increment bez guard |
| I2 | Monotonicity | Counter resetovaný na nižší hodnotu |
| I3 | Causality | Read artefaktu bez existence check |
| I4 | Isolation | Modifikace artefaktů jiných skills bez oprávnění |
| I5 | Convergence | Cyklické závislosti mezi skills |

### S2: Adversarial Fuzzing

| ID | Vektor | Co ověřit |
|----|--------|-----------|
| F1 | Shell injection | Quoting VŠECH proměnných v bash |
| F2 | Path traversal | Sanitizace dynamických cest |
| F3 | YAML bomb | Limity na parsování |
| F4 | Unicode | Git operace s non-ASCII |
| F5 | Race condition | Atomicita zápisů do state.md |
| F6 | Stale reference | Existence checks pro cross-references |

### S3: Temporální kauzalita (celý pipeline)

```
init → vision → gap → generate → intake → prio → sprint → analyze
  → implement → test → review → [rework?] → close → docs → check → archive
```

Pro každý přechod A → B: jaký artefakt A vytváří? Čte ho B? Co když chybí/corrupt?

### S4: Virtuální průchod fabric-loop (end-to-end simulace)

Spustí kompletní cyklus fabric-loop na reálných datech BEZ modifikace workspace.
Výstup: simulační log s tick-by-tick průběhem celého lifecycle.

**Příprava:**

```bash
# 1) Vytvoř dočasný adresář pro simulační výstupy
SIM="_sim"
mkdir -p "$SIM"

# 2) Inicializuj log
cat > "$SIM/run-log.md" << 'HEADER'
# Virtual Loop Simulation
## Parameters
HEADER
echo "- date: $(date -Iseconds)" >> "$SIM/run-log.md"
echo "- loop=auto, goal=release" >> "$SIM/run-log.md"
echo "" >> "$SIM/run-log.md"
echo "## Tick Log" >> "$SIM/run-log.md"
```

**Kritické nastavení bash (bez tohoto simulace PADNE):**

```bash
set -uo pipefail
# ⚠️  NEPOUŽÍVEJ set -e !
# Důvod: pytest, ruff, git a další externími nástroje vracejí
# nenulový exit code i při normálním provozu (např. ruff najde
# lint chyby → exit 1). S set -e by skript okamžitě skončil.
```

**Zachytávání výstupů externích příkazů:**

```bash
# ✅ SPRÁVNĚ — || true zabrání ukončení skriptu
TEST_OUTPUT=$(python3 -m pytest -q --tb=no 2>&1 || true)
LINT_OUTPUT=$(python3 -m ruff check . 2>&1 || true)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-git")
COMPILE=$(python3 -c "import src.llmem" 2>&1 || true)

# ❌ ŠPATNĚ — bez || true skript s pipefail skončí při prvním selhání
TEST_OUTPUT=$(python3 -m pytest -q --tb=no 2>&1)
```

**Struktura simulace:**

```
Preconditions (P1–P8) → Idle detection → Tick loop:
  vision → status → architect → process → gap → generate →
  intake → prio → sprint → analyze → implement → test →
  review → close → docs → check → archive → LOOP BOUNDARY
```

**Preconditions (musí projít VŠECHNY, jinak STOP):**

| ID | Co ověřit | Bash |
|----|-----------|------|
| P1 | config.md existuje | `[ -f "$WORK/config.md" ]` |
| P2 | WORK_ROOT existuje | `[ -d "$WORK" ]` |
| P3 | state.md existuje | `[ -f "$WORK/state.md" ]` |
| P4 | vision.md existuje | `[ -f "$WORK/vision.md" ]` |
| P5 | backlog/ neprázdný | `ls $WORK/backlog/*.md 2>/dev/null \| wc -l` |
| P6 | skills root existuje | `[ -d "skills/fabric-init" ]` |
| P7 | templates/ existují | `ls $WORK/templates/*.md 2>/dev/null \| wc -l` |
| P8 | intake/ existuje | `[ -d "$WORK/intake" ]` |

**Idle detection (auto mode):**

```bash
ACTIVE_ITEMS=$(for f in $WORK/backlog/*.md; do
  s=$(grep '^status:' "$f" 2>/dev/null | head -1 | awk '{print $2}')
  [ "$s" != "DONE" ] && [ "$s" != "BLOCKED" ] && echo "$f"
done | wc -l)
PENDING_INTAKE=$(ls $WORK/intake/*.md 2>/dev/null | wc -l)

if [ "$ACTIVE_ITEMS" -gt 0 ] || [ "$PENDING_INTAKE" -gt 0 ]; then
  # práce existuje → start orientation
else
  # idle → konec simulace
fi
```

**Tick loop — klíčová pravidla:**

1. MAX_TICKS=50 (guard proti nekonečné smyčce)
2. Každý tick: `SIM_TICK++`, loguj step+phase, proveď akci, posuň `SIM_STEP`
3. Archiv = loop boundary → break (jedna iterace celého cyklu)
4. Simulované reporty zapisuj POUZE do `$SIM/` (nikdy do `$WORK/reports/`)
5. Reálné příkazy (pytest, ruff) VŽDY s `|| true`

**Per-step akce (co každý tick ověřuje):**

| Step | Reálná data | Simulovaný výstup |
|------|-------------|-------------------|
| vision | čte vision.md + visions/*.md | $SIM/vision-report.md |
| status | spouští pytest, ruff, git log | $SIM/status-report.md |
| architect | počítá .py soubory, ADRs | $SIM/architect-report.md |
| process | hledá processes/process-map.md | $SIM/process-report.md |
| gap | porovnává vision sekce vs backlog | $SIM/gap-report.md |
| generate | (simulované — žádné nové items) | $SIM/generate-report.md |
| intake | čte intake/*.md, loguje tituly | $SIM/intake-report.md |
| prio | počítá READY/DESIGN/IDEA | $SIM/prio-report.md |
| sprint | vybírá kandidáty (DESIGN+Task/Bug) | $SIM/sprint-report.md |
| analyze | hledá T0→T1→T2 WIP kandidáta | $SIM/analyze-report.md |
| implement | import check (`python3 -c "import..."`) | $SIM/implement-report.md |
| test | spouští pytest -q --tb=short | $SIM/test-report.md |
| review | spouští ruff check + ruff format --check | $SIM/review-report.md |
| close | simuluje merge | $SIM/close-report.md |
| docs | hledá docs/ adresář | $SIM/docs-report.md |
| check | pytest + ruff + governance + templates | $SIM/check-report.md |
| archive | počítá reporty k archivaci | $SIM/archive-report.md |

**Očekávaný výstup (všechno OK = 17 ticků):**

```
PRECONDITIONS: P1–P8 PASS
IDLE DETECTION: work exists
Tick 1: vision ✅    Tick 10: analyze ✅
Tick 2: status ✅    Tick 11: implement ✅
Tick 3: architect ✅ Tick 12: test ✅
Tick 4: process ⚠️   Tick 13: review ✅
Tick 5: gap ✅       Tick 14: close ✅
Tick 6: generate ✅  Tick 15: docs ⚠️
Tick 7: intake ✅    Tick 16: check ✅
Tick 8: prio ✅      Tick 17: archive ✅
Tick 9: sprint ✅    → LOOP BOUNDARY
```

**Známé WARNy (nejsou chyby):**

- `process-map.md missing` — fabric-process ještě neběžel, vytvoří se při prvním reálném běhu
- `docs/ directory missing` — fabric-docs ho vytvoří
- Test failures se reportují ale neblokují (simulace je virtuální)
- Lint chyby se reportují ale neblokují

**Úklid po simulaci:**

```bash
rm -rf "$SIM"
```

**Anti-patterns:**

- ❌ Použít `set -e` — zabitje skript při prvním pytest FAIL
- ❌ Psát výstupy do reálného `$WORK/reports/` — simulace NESMÍ modifikovat workspace
- ❌ Použít `$()` na příkazy co mohou selhat bez `|| true`
- ❌ Zapomenout `2>&1` u externích příkazů — stderr by nebyl zachycen
- ❌ Cesty typu `$WORK/../fabric/` — pokud WORK=fabric, vede mimo workspace

---

## FÁZE 3 — Work Quality Audit

> Spouštěj jen pokud `scope=deep` nebo default.

### 3.1) Per-skill work quality check

| Kritérium | Otázka |
|-----------|--------|
| Konkrétnost | Jsou instrukce dostatečně konkrétní pro LLM bez kontextu? |
| Příklady | Obsahuje šablony/příklady výstupu? |
| Minimum | Je definované minimum akceptovatelného výstupu? |
| Anti-patterns | Jsou zakázané věci explicitní? |
| Test metodika | (impl) Min. 3 testy: happy/edge/error? |
| Coverage | (impl) Coverage target? |
| Analýza | (analyze) Alternativy + pseudokód? |
| Review | (review) Fix strategie per finding? |

### 3.2) Comparison delta (pokud existuje dev/workflows/)

Per skill: starý workflow vs nový fabric skill — ztráty a zisky.

### 3.3) Deep Quality Checks (scope=deep only)

Tyto kontroly jdou HLOUBĚJI než runtime gates (lint/test). Ověřují strukturální konzistenci kódu.

| ID | Check | Co ověřit | Jak | Severity |
|----|-------|-----------|-----|----------|
| DQ1 | API konzistence | Všechny endpointy v `api/routes/` mají odpovídající spec v `specs/` | Porovnej definované routes (`@app.get/post/put/delete`) vs LLMEM_API_V1 spec. Chybějící endpoint v spec = HIGH. | HIGH |
| DQ2 | Model field coverage | Každý Pydantic model v `models.py` má: type hints, Optional/default, docstring | Grep `class.*BaseModel` → pro každý: field count, docstring existence, Optional% | MEDIUM |
| DQ3 | Config schema validace | Všechny `LLMEM_*` env vars v `config.py` mají: default, description, type | Grep `Field(` / `env=` v config.py → ověř default + description | MEDIUM |
| DQ4 | Import konzistence | Žádné cirkulární importy, žádné wildcard importy | `grep -r "from .* import \*" src/` = FAIL. Pro circular: `python -c "import llmem"` exit code. | HIGH |
| DQ5 | Test-to-code mapping | Každý modul v `src/llmem/` má odpovídající test v `tests/` | Pro `src/llmem/{module}.py` hledej `tests/test_{module}.py`. Chybějící = MEDIUM. | MEDIUM |
| DQ6 | Error message quality | Chybové zprávy obsahují kontext (ne jen "Error occurred") | Grep `raise.*Error\|logging.error\|print.*error` → ověř, že message obsahuje proměnnou/kontext. | LOW |

**Postup pro DQ checks:**

```bash
# DQ1: API route vs spec check
ROUTES=$(grep -rn '@app\.\(get\|post\|put\|delete\)' {CODE_ROOT}/api/ 2>/dev/null | wc -l)
SPEC_ENDPOINTS=$(grep -c 'endpoint:' {WORK_ROOT}/specs/LLMEM_API_V1*.md 2>/dev/null || echo 0)
echo "DQ1: $ROUTES routes in code, $SPEC_ENDPOINTS in spec"
if [ "$ROUTES" -gt "$SPEC_ENDPOINTS" ]; then
  echo "WARN: code has more routes than spec documents ($ROUTES vs $SPEC_ENDPOINTS)"
fi

# DQ2: Model docstring coverage
MODELS=$(grep -c 'class.*BaseModel' {CODE_ROOT}/models.py 2>/dev/null || echo 0)
MODELS_WITH_DOC=$(grep -A1 'class.*BaseModel' {CODE_ROOT}/models.py 2>/dev/null | grep -c '"""' || echo 0)
echo "DQ2: $MODELS models, $MODELS_WITH_DOC with docstrings"

# DQ4: No wildcard imports
WILDCARDS=$(grep -rn 'from .* import \*' {CODE_ROOT}/ 2>/dev/null | grep -v __init__ | wc -l)
if [ "$WILDCARDS" -gt 0 ]; then
  echo "WARN: $WILDCARDS wildcard imports found (excluding __init__)"
fi

# DQ5: Test mapping
for SRC_FILE in {CODE_ROOT}/*.py {CODE_ROOT}/**/*.py; do
  [ -f "$SRC_FILE" ] || continue
  MODULE=$(basename "$SRC_FILE" .py)
  [ "$MODULE" = "__init__" ] && continue
  if [ ! -f "tests/test_${MODULE}.py" ]; then
    echo "DQ5: missing test file for $MODULE"
  fi
done
```

**Výstupní formát:**

```md
## Deep Quality Checks

| ID | Check | Stav | Detail |
|----|-------|------|--------|
| DQ1 | API konzistence | PASS/WARN | {routes} routes, {spec_endpoints} in spec |
| DQ2 | Model field coverage | PASS/WARN | {models} models, {with_doc} with docstrings |
| DQ3 | Config schema | PASS/WARN | {vars} env vars, {with_defaults} with defaults |
| DQ4 | Import konzistence | PASS/FAIL | {wildcards} wildcard imports |
| DQ5 | Test mapping | PASS/WARN | {missing} modules without tests |
| DQ6 | Error messages | PASS/WARN | {bare_errors} bare error messages |
```

**Anti-patterns:**
- ❌ Přeskočit DQ checks protože lint/test prošly
- ❌ Reportovat jen PASS/FAIL bez konkrétních čísel
- ✅ Vždy uvést konkrétní počty a identifikovat chybějící položky

---

## FÁZE 4 — Template Compliance (JEN pro Tier 2 builder-born skills)

> **PŘESKOČ pro T1, T3 a SKIP.** Tato fáze se týká POUZE T2 skills.

Přečti `skills/fabric-builder/assets/builder-template.md` a ověř:

- [ ] Tag `<!-- built from: builder-template -->` přítomen
- [ ] §1–§12 vyplněno nebo explicitně odstraněno s komentářem
- [ ] §2 Protokol je přesná kopie z template
- [ ] §7 Postup má: konkrétní instrukce, příklady, minima, anti-patterns
- [ ] §10 Self-check má ≥3 testovatelné položky
- [ ] §12 Metadata má phase, step, depends_on, feeds_into

**Compliance score:** `splněné / relevantní × 100`
- < 80 % → P1 finding
- < 50 % → P0 finding

---

## FÁZE 5 — Evolution Radar

### 5.1) Chybějící skills (porovnání s dev/workflows/)

| Starý workflow | Kritičnost | Doporučení |
|----------------|-----------|------------|

### 5.2) Skill interaction gaps

- Artefakty bez producenta nebo konzumenta
- Dva skills modifikující stejný soubor bez koordinace

### 5.3) Legacy migration radar

```md
| Skill | K10 score | Migrace priorita | Doporučený sprint |
|-------|-----------|-------------------|-------------------|
```

Seřaď podle K10 — nejnižší K10 = první kandidát na migraci přes `fabric-builder migrate`.

### 5.4) Top 5 doporučení pro builder

Na základě celého auditu — co by měl `fabric-builder fix` opravit jako první:

```md
1. {finding} — {skill} — {priorita} — {odhadovaný dopad}
```

---

## Výstup

### Report

`{WORK_ROOT}/reports/checker-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: checker
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
score_total: {X}
score_max: {Y}
score_pct: {Z}%
skills_audited: {N}
findings_total: {N}
findings_p0: {N}
findings_p1: {N}
---

# Fabric Checker Report — {YYYY-MM-DD}

## Executive Summary
{2–3 věty}

## Scoring ({score_pct}%)
{Tabulka z Fáze 1}

## Extrémní simulace
{Fáze 2}

## Work Quality
{Fáze 3}

## Template Compliance
{Fáze 4 — jen T2 skills, nebo "žádné T2 skills"}

## Evolution Radar
{Fáze 5}

## Findings pro fabric-builder
{Seřazený seznam findings s prioritou — builder čte tuto sekci}
```

### Intake items

Pro P0/P1 findings: `{WORK_ROOT}/intake/checker-{slug}.md` se `source: checker`.

---

## Self-check

- [ ] Report existuje: `{WORK_ROOT}/reports/checker-{YYYY-MM-DD}.md`
- [ ] Report má schema frontmatter se score
- [ ] KAŽDÝ skill přečten CELÝ (ne jen prvních 200 řádků)
- [ ] Scoring tabulka obsahuje VŠECHNY auditované skills
- [ ] Tier klasifikace je správná pro každý skill
- [ ] Template compliance POUZE pro T2 skills
- [ ] **Žádný soubor nebyl modifikován** (checker je read-only)
- [ ] Evolution radar má ≥3 doporučení
- [ ] Findings sekce je seřazená dle priority (pro builder)

---

## Protokol

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "checker" --event start

# ... read-only audit ...

python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "checker" --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/checker-{YYYY-MM-DD}.md"
```

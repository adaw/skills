---
name: fabric-checker
description: "Read-only audit of the entire fabric ecosystem. Scores each skill 0-100, runs extreme simulations, and evaluates work quality. Never modifies anything—only produces scoring report with findings for fabric-builder to fix."
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

## Klasifikace skills (čti PŘED auditem)

**T1 Orchestrátory** (`fabric-loop`, `fabric-init`): K1-K10 ano, template compliance NE.
**T2 Builder-born** (mají `<!-- built from: builder-template -->`): K1-K10 + template compliance.
**T3 Legacy** (vše ostatní): K1-K10 ano, template compliance NE.
**META** (`fabric-checker`, `fabric-builder`): Neauditují se navzájem — opravy jen manuálně.

---

## §3 — Preconditions (bash)

```bash
# K7: Path traversal guard
for VAR in "{WORK_ROOT}"; do
  if echo "$VAR" | grep -qE '\.\.'; then
    echo "STOP: Path traversal detected in '$VAR'"
    exit 1
  fi
done

# K6: skills/ directory must exist
if [ ! -d "skills/fabric-init" ]; then
  echo "STOP: skills/fabric-init not found — fabric framework not installed"
  exit 1
fi

# K7: Scope parameter validation (if provided)
if [ -n "$SCOPE" ] && ! echo "$SCOPE" | grep -qE '^(quick|deep|target)$'; then
  echo "STOP: Invalid scope='$SCOPE' — expected quick|deep|target"
  exit 1
fi
```

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

### 0.2) Audit scope per tier: T1=K1-K10+F2 (no F4), T2=K1-K10+F2+F3+**F4**, T3=K1-K10+F2+F3 (no F4), SKIP=checker+builder

### 0.3) Podpůrné soubory a nástroje

- `fabric/config.md`, `fabric/state.md` — konfigurace + stav (čti CELÝ)
- `skills/fabric-builder/assets/builder-template.md` — šablona (Fáze 4)
- `tools/fabric-score.sh` — deterministický K1-K10 scorer
- `tools/t10_config_stale_check.py` — config key stale read (T10)
- `tools/s4_symmetry_check.py` — depends_on ↔ feeds_into symetrie (S4)

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
- [ ] Postup je KONKRÉTNÍ — ne vágní (≥5 kroků s bash/pseudocode)
- [ ] Obsahuje ≥1 inline PŘÍKLAD s reálnými LLMem daty (task IDs, endpoints, file paths)
- [ ] Definuje MINIMUM akceptovatelného výstupu (explicitní acceptance criteria)
- [ ] Definuje ≥3 ANTI-PATTERNS s bash detection příkazy
- [ ] Instrukce dostatečné pro JINÉHO LLM bez kontextu (no implicit knowledge)
- [ ] Pokud implementuje: min. test set (3: happy/edge/error)
- [ ] Pokud analyzuje: alternativy + pseudokód
- [ ] Pokud reviewuje: fix strategie per finding typ
- [ ] Deep quality checks (DQ1-DQ6) provedeny pokud scope=deep
- **0b** pokud postup obsahuje jen vágní „udělej X"
- **Objektivní metriky:** example ≥10 řádků, anti-patterns ≥3 s bash `grep`/`ls` detection, acceptance criteria tabulka s ≥3 položkami

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
| I5 | Convergence | Cyklické závislosti — DFS cycle detection (viz `references/cycle-detection.md`) |

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

### S4: Virtuální průchod fabric-loop (end-to-end simulace) + Symetrické závislosti

Spustí kompletní cyklus fabric-loop na reálných datech BEZ modifikace workspace.
Výstup: simulační log s tick-by-tick průběhem celého lifecycle.

**Detaily viz:** `references/s4-virtual-loop-simulation.md`

**Povinné:** Spusť symetrii závislostí:

```bash
python skills/fabric-checker/tools/s4_symmetry_check.py --strict 2>/dev/null
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "P1 finding: dependency asymmetry detected"
  echo "dependency_asymmetry | HIGH | asymmetrické depends_on/feeds_into v fabric skills"
fi
```

Pokud `s4_symmetry_check.py` exit code ≠ 0 → zapiš P1 finding do reportu.

**Povinné:** Kauzální validace depends_on — ověř, že žádný skill nemá v depends_on skill, který běží PO něm v LIFECYCLE:

```bash
# Kauzální validace: depends_on musí být z dřívější fáze lifecycle
LIFECYCLE="vision status architect process gap generate intake prio design sprint analyze implement test review close docs check archive"
for SKILL_FILE in skills/fabric-*/SKILL.md; do
  SKILL_STEP=$(grep -m1 'step:\|lifecycle_step:' "$SKILL_FILE" | awk '{print $2}')
  SKILL_IDX=$(echo "$LIFECYCLE" | tr ' ' '\n' | grep -n "^${SKILL_STEP}$" | cut -d: -f1)
  [ -z "${SKILL_IDX}" ] && continue  # utility/meta — skip
  for DEP in $(grep 'depends_on:' "$SKILL_FILE" | sed 's/.*\[//;s/\].*//;s/,/ /g;s/fabric-//g'); do
    DEP_FILE="skills/fabric-${DEP}/SKILL.md"
    [ ! -f "${DEP_FILE}" ] && continue
    DEP_STEP=$(grep -m1 'step:\|lifecycle_step:' "${DEP_FILE}" | awk '{print $2}')
    DEP_IDX=$(echo "$LIFECYCLE" | tr ' ' '\n' | grep -n "^${DEP_STEP}$" | cut -d: -f1)
    [ -z "${DEP_IDX}" ] && continue
    if [ "${DEP_IDX}" -gt "${SKILL_IDX}" ]; then
      echo "P1: $(basename "$(dirname "$SKILL_FILE")") depends_on ${DEP} but ${DEP} runs AFTER in lifecycle (${DEP_IDX} > ${SKILL_IDX})"
    fi
  done
done
```

**Klíčové momenty a detaily simulace:** viz `references/s4-virtual-loop-simulation.md`

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

6 checklistů DQ1–DQ6 (API routes, model coverage, config schema, imports, test mapping, error messages).
**Detaily viz:** `references/dq-deep-quality-checks.md`

---

## K10 — Concrete Example & Anti-patterns

### Audit Execution Runner

Per-skill audit loop: read ENTIRE skill + references/ + config.md → score K1-K10 → record findings.
**Detailní pseudocode a scoring rules viz:** `references/audit-runner-pseudocode.md`

### Example: Checker Audit — fabric-implement Score 94%

```
Audit fabric-implement (T2 builder-born):

FÁZE 0: Tier classification → T2 (has builder-template tag)
FÁZE 1 Scoring:
  K1=10: reads phase (line 59), STOP on mismatch, no illegal state modification
  K2=10: rework_count max=3 enforced (line 89), loop counter with numeric guard
  K3=8: MINOR — git commit lacks conflict check (line 296), fallback chains present elsewhere
  K4=10: all vars quoted ("${WIP_BRANCH}"), no --force, no --hard
  K5=10: COMMANDS.test from config (line 59), schema present in report template
  K6=10: bash preconditions (lines 51–73), dependency chain: analyze→implement
  K7=9: MINOR — TASK_ID needs regex [a-z0-9-]+ guard (path traversal OK at line 66)
  K8=10: protocol START/END present (lines 25–37), schema=fabric.report.v1
  K9=10: 8 testable items, existence+quality+invariants covered
  K10=9: MINOR — regression check heuristic could reference specific pytest flags
  → Total: 96/100 = 96%

FÁZE 2 Invariants: PASS (I1-I5 all verified)
FÁZE 3 Work Quality: concrete §7 steps, LLMem examples, anti-patterns with bash
```

### Anti-patterns (FORBIDDEN detection & prevention)

```bash
# A1: Scoring WITHOUT reading references/
# FIX: MUST read skill's references/*.md before K10 score
if [ ! -d "skills/${SKILL}/references" ]; then
  echo "WARN: K10 assessment incomplete (no references/ directory)"
fi

# A2: K10 PASS when §7 vague (no anti-patterns documented)
# FIX: Require ≥3 anti-pattern blocks in §7
COUNT=$(grep -c 'Anti-pattern\|FORBIDDEN\|MUST NOT' "skills/${SKILL}/SKILL.md" || echo 0)
[ "$COUNT" -lt 3 ] && echo "WARN: K10 reduced — only $COUNT anti-patterns (need ≥3)"

# A3: Template compliance (FÁZE 4) on T3 legacy skills
# FIX: Skip FÁZE 4 for T3, only audit T2 builder-born
if ! grep -q 'built from: builder-template' "skills/${SKILL}/SKILL.md"; then
  echo "INFO: T3 legacy detected — skipping template compliance"
fi
```

---

## FÁZE 4 — Template Compliance (JEN pro Tier 2 builder-born skills)

> **PŘESKOČ pro T1, T3 a SKIP.** Tato fáze se týká POUZE T2 skills.

**Detaily viz:** `references/fase4-template-compliance.md`

Klíčové kontroly (na `skills/fabric-builder/assets/builder-template.md`):
- §2 Protokol = přesná kopie z template
- §7 Postup = konkrétní instrukce + příklady + minima + anti-patterns
- §10 Self-check = ≥3 testovatelné items
- §12 Metadata = phase, step, depends_on, feeds_into

**Scoring:** splněné / relevantní × 100
- < 80 % → P1 finding
- < 50 % → P0 finding

---

## FÁZE 5 — Evolution Radar

**Detaily viz:** `references/fase5-evolution-radar.md`

Syntéza nálezů z Fází 1–4:

1. **Chybějící skills**: Porovnání s `dev/workflows/` — co chybí
2. **Skill interaction gaps**: Artefakty bez producenta/konzumenta, cyklické dependency
3. **Legacy migration radar**: T3 skills seřazené dle K10 (nejnižší = URGENT)
4. **Top 5 doporučení pro builder**: Priority seznam findingů (P0 > P1 > P2, easy wins first)

---

## Výstup

### Report

`{WORK_ROOT}/reports/checker-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: checker
step: "checker"
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

## §12 — Metadata

```yaml
depends_on: [fabric-builder]  # builder (code generator) → checker (validator)
feeds_into: []
phase: meta
lifecycle_step: checker
touches_state: false
touches_git: false
idempotent: true
fail_mode: fail-closed
```

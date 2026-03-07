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

**Detaily viz:** `references/s4-virtual-loop-simulation.md`

Klíčové momenty:
- Preconditions (P1–P8): Ověř existenci kritických souborů
- Idle detection: Detekuj zda je práce (pokud ne, konec simulace)
- Tick loop: MAX_TICKS=50, каждый tick loguje step, reálné příkazy s `|| true`
- Výstupy POUZE do `$SIM/`, nikdy do reálného `$WORK/reports/`
- Expected output: 17 ticků (vision → archive → LOOP BOUNDARY)

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

**Detaily viz:** `references/dq-deep-quality-checks.md`

6 checklistů (DQ1–DQ6):
- **DQ1**: API routes vs spec (HIGH severity)
- **DQ2**: Model field coverage (docstrings, Optional defaults)
- **DQ3**: Config schema validation (env vars descriptions)
- **DQ4**: Import consistency (no circulars, no wildcards)
- **DQ5**: Test-to-code mapping (test files per module)
- **DQ6**: Error message quality (context-aware messages)

Runnable bash procedury v references/ — copy-paste a customize {CODE_ROOT}/{WORK_ROOT}.

---

## K10 — Concrete Example & Anti-patterns

### Audit Execution Runner (inline pseudocode)

```bash
# Per-skill audit loop (Fáze 1 core)
for SKILL_FILE in skills/fabric-*/SKILL.md; do
  SKILL_NAME=$(basename "$(dirname "$SKILL_FILE")")
  LINES=$(wc -l < "$SKILL_FILE")

  # 1. Read ENTIRE skill (including references/)
  # 2. Read config.md for cross-reference
  # 3. Score K1-K10 using checklists above
  # 4. Record findings with line numbers

  # Scoring rules:
  # - Counter without `grep -qE '^[0-9]+$'` → max K2=7
  # - Hardcoded threshold without config.md grep → max K5=7
  # - Phase WARN not STOP → max K1=6
  # - K4=N/A for non-git skills → Max=90
  # - §7 vague ("analyzuj") without detail → max K10=5

  echo "$SKILL_NAME | K1=$K1 K2=$K2 ... K10=$K10 | $TOTAL/$MAX = $PCT%"
done
```

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

# fabric-builder — Kanonická šablona pro fabric skills

> **Tento soubor není spustitelný skill.** Je to builder/šablona.
> Při vytváření nového skillu zkopíruj strukturu, nahraď placeholdery a odstraň komentáře.

---

# {SKILL_NAME} — {Jednořádkový popis účelu}

<!--
  KONVENCE POJMENOVÁNÍ:
  - Skill name:  fabric-{verb} (např. fabric-design, fabric-architect, fabric-e2e)
  - Report:      {WORK_ROOT}/reports/{skill_name_short}-{YYYY-MM-DD}[-{run_id}].md
  - Intake:      {WORK_ROOT}/intake/{skill_name_short}-{slug}.md
  - Analýzy:     {ANALYSES_ROOT}/{task_id}-{kind}.md
-->

---

## §1 — Účel

<!--
  CO TADY PATŘÍ:
  - 2–3 věty: proč tento skill existuje
  - Jakou hodnotu přináší do pipeline
  - Co se stane, když se přeskočí (risk)

  PŘÍKLAD (fabric-design):
  "Převést READY backlog item na implementační specifikaci: datový model,
  komponenty, API, integrace, config, testy, rizika. Bez DESIGNu implementátor
  pracuje z vágního popisu a výsledek bude nekonzistentní."
-->

{ÚČEL — 2–3 věty}

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.
Toto je mechanická povinnost — nemodifikuj, jen vyplň `{SKILL_NAME_SHORT}`.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "{SKILL_NAME_SHORT}" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "{SKILL_NAME_SHORT}" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/{SKILL_NAME_SHORT}-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "{SKILL_NAME_SHORT}" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

<!--
  CO TADY PATŘÍ:
  - Jaké soubory/artefakty MUSÍ existovat předtím, než skill začne
  - Jaký skill je musel vytvořit (dependency chain)
  - Bash kód pro ověření — pokud precondition FAIL → STOP s jasnou zprávou

  PŘÍKLAD (fabric-review):
  - backlog file musí existovat (vytvořil fabric-implement)
  - branch musí existovat (vytvořil fabric-implement)
  - test report musí existovat (vytvořil fabric-test)
-->

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

# --- Precondition 3: {SKILL-SPECIFIC} ---
# Přidej sem ověření specifická pro tento skill.
# Např. pro fabric-review:
#   LATEST_TEST_REPORT=$(ls -t {WORK_ROOT}/reports/test-*.md 2>/dev/null | head -1)
#   if [ -z "$LATEST_TEST_REPORT" ]; then
#     echo "STOP: no test report found — run fabric-test first"
#     exit 1
#   fi
```

**Dependency chain tohoto skillu:**
```
{PREREQUISITE_SKILL_1} → {PREREQUISITE_SKILL_2} → [tento skill]
```

---

## §4 — Vstupy

<!--
  CO TADY PATŘÍ:
  - Kompletní seznam souborů/adresářů, které skill čte
  - Rozděl na: POVINNÉ (skill selže bez nich) a VOLITELNÉ (obohacují výstup)
  - Používej {WORK_ROOT}, {CODE_ROOT}, {TEST_ROOT} atd. z config.md
-->

### Povinné
- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/state.md`
- {DALŠÍ POVINNÉ VSTUPY}

### Volitelné (obohacují výstup)
- {VOLITELNÉ VSTUPY}

---

## §5 — Výstupy

<!--
  CO TADY PATŘÍ:
  - Kompletní seznam artefaktů, které skill vytváří
  - Každý výstup: cesta + schema (pokud má frontmatter)
  - Rozděl na: PRIMÁRNÍ (vždy) a VEDLEJŠÍ (podmínečně)
-->

### Primární (vždy)
- Report: `{WORK_ROOT}/reports/{SKILL_NAME_SHORT}-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/{SKILL_NAME_SHORT}-{slug}.md` (schema: `fabric.intake_item.v1`)
- {DALŠÍ VEDLEJŠÍ VÝSTUPY}

---

## §6 — Deterministic FAST PATH

<!--
  CO TADY PATŘÍ:
  - Strojové kroky, které NEPLÝTVAJÍ tokeny
  - Bash skripty přes fabric.py / validate_fabric.py
  - Vždy PŘED hlavní LLM prací
  - Pokud skill nepotřebuje FAST PATH, odstraň tuto sekci

  MOTIVACE: LLM nemusí počítat řádky, parsovat YAML, regenerovat indexy.
  To dělá stroj. LLM rozhoduje, analyzuje, hodnotí.
-->

Než začneš analyzovat / hodnotit, proveď deterministické kroky:

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index

# 3. {SKILL-SPECIFIC FAST PATH}
# Např. pro fabric-prio:
#   python skills/fabric-init/tools/fabric.py backlog-scan \
#     --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

<!--
  ╔══════════════════════════════════════════════════════════════╗
  ║  TOTO JE NEJDŮLEŽITĚJŠÍ SEKCE CELÉHO SKILLU.               ║
  ║                                                              ║
  ║  Zde popisuješ JAK dělat kvalitní práci — ne orchestraci.  ║
  ║  LLM bez explicitních instrukcí udělá minimum.             ║
  ║                                                              ║
  ║  PRAVIDLA:                                                   ║
  ║  1. Buď KONKRÉTNÍ — „napiš 3 testy" ne „napiš testy"      ║
  ║  2. Dej PŘÍKLADY — šablony, pseudokód, ukázky              ║
  ║  3. Definuj MINIMUM — co je nejmenší akceptovatelný výstup  ║
  ║  4. Definuj ANTI-PATTERNS — co je zakázané                  ║
  ║  5. Dej HEURISTIKY — kdy co použít, jak se rozhodnout      ║
  ╚══════════════════════════════════════════════════════════════╝
-->

### 7.1) {Název kroku 1}

<!--
  Každý krok má:
  - CO udělat (1–2 věty)
  - JAK to udělat kvalitně (detailní instrukce)
  - MINIMUM akceptovatelného výstupu
  - PŘÍKLAD nebo ŠABLONA výstupu
  - ANTI-PATTERNS (co nedělat)
-->

**Co:** {1–2 věty co se v tomto kroku dělá}

**Jak (detailní instrukce):**
{KONKRÉTNÍ pokyny — čím detailnější, tím kvalitnější výstup LLM vyprodukuje}

**Minimum:**
{Co MUSÍ tento krok vyprodukovat minimálně}

**Anti-patterns (zakázáno):**
- {ANTI_PATTERN_1 — např. „Nepiš `pass` nebo `# TODO` do DONE kódu"}
- {ANTI_PATTERN_2}

**Šablona výstupu:**
```
{UKÁZKA formátu, který má krok vyprodukovat}
```

### 7.2) {Název kroku 2}

{...stejná struktura...}

### 7.N) {Název posledního kroku}

{...}

---

## §8 — Quality Gates (pokud skill má gates)

<!--
  CO TADY PATŘÍ:
  - Objektivní kontroly, které se spouští BĚHEM nebo PO práci
  - Bash příkazy (lint, test, format)
  - PASS/FAIL kritéria
  - Auto-fix logika (max 1× per gate)
  - Pokud skill nemá quality gates, odstraň tuto sekci

  PŘÍKLAD (fabric-implement):
    Gate 1: Lint      → COMMANDS.lint → if fail + lint_fix exists → auto-fix → retry 1×
    Gate 2: Format    → COMMANDS.format_check → if fail + format exists → auto-fix → retry 1×
    Gate 3: Tests     → COMMANDS.test → MUST PASS (no auto-fix)
-->

### Gate 1: {Název}
```bash
# Spuštění
{COMMANDS.xxx}
```
- PASS: {podmínka}
- FAIL: {akce — auto-fix? intake? STOP?}
- Auto-fix: max 1× → `{COMMANDS.xxx_fix}` → retry gate

### Gate 2: {Název}
{...}

---

## §9 — Report

<!--
  CO TADY PATŘÍ:
  - Přesný formát reportu
  - Schema frontmatter
  - Povinné sekce
  - Odkaz na template (pokud existuje)
-->

Vytvoř `{WORK_ROOT}/reports/{SKILL_NAME_SHORT}-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: {SKILL_NAME_SHORT}
step: "{SKILL_NAME_SHORT}"
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# {SKILL_NAME_SHORT} — Report {YYYY-MM-DD}

## Souhrn
{1–3 věty co skill udělal a s jakým výsledkem}

## Detaily
{Structured output — tabulky, findings, metriky}

## Intake items vytvořené
{Seznam nebo "žádné"}

## Warnings
{Seznam nebo "žádné"}
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

<!--
  CO TADY PATŘÍ:
  - Checklisty, které LLM MUSÍ ověřit na konci
  - Rozdělené na: EXISTENCE (soubory existují) a QUALITY (obsah je správný)
  - Každá položka: konkrétní, testovatelná, jednoznačná

  PRAVIDLO: Pokud self-check selže, skill NESMÍ reportovat OK.
  Místo toho:
  - reportuj WARN nebo ERROR
  - vytvoř intake item pro neopravenou položku
-->

### Existence checks
- [ ] Report existuje: `{WORK_ROOT}/reports/{SKILL_NAME_SHORT}-{YYYY-MM-DD}.md`
- [ ] {DALŠÍ EXISTENCE CHECKS}

### Quality checks
- [ ] Report obsahuje povinné sekce: Souhrn, Detaily, Warnings
- [ ] {SKILL-SPECIFICKÉ QUALITY CHECKS}
- [ ] Pro každé CRITICAL finding existuje intake item

### Invarianty
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován (pokud to skill explicitně nepředepisuje)
- [ ] Protocol log obsahuje START i END záznam

---

## §11 — Failure Handling

<!--
  CO TADY PATŘÍ:
  - Co dělat když skill selže v různých fázích
  - Recovery postup
  - Jak eskalovat (intake item? STOP? manuální intervence?)
-->

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí prereq soubor | STOP + jasná zpráva co chybí a který skill to má vytvořit |
| FAST PATH | fabric.py selže | WARN + pokračuj manuálně (LLM udělá strojovou práci) |
| Postup (§7) | Nelze dokončit krok | STOP + protocol error log + intake item s popisem |
| Quality Gate | Gate FAIL po auto-fixu | Report FAIL + intake item |
| Self-check | Check FAIL | Report WARN + intake item |

**Obecné pravidlo:** Skill je fail-open vůči VOLITELNÝM vstupům (chybí → pokračuj s WARNING)
a fail-fast vůči POVINNÝM vstupům (chybí → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

<!--
  CO TADY PATŘÍ:
  - Informace které fabric-loop potřebuje pro správné zařazení skillu
  - NEMODIFIKUJ state.md přímo (to dělá loop), pokud skill není explicitně oprávněn

  Vyplň a odkomentuj relevantní řádky:
-->

```yaml
# Zařazení v lifecycle
phase: {orientation|planning|implementation|closing|utility}
step: {název kroku v state machine — musí odpovídat fabric-loop}

# Oprávnění
may_modify_state: false        # true jen pro fabric-loop, fabric-init, fabric-sprint
may_modify_backlog: false      # true pro prio, intake, analyze, close, archive
may_modify_code: false         # true pro implement, (e2e, hotfix)
may_create_intake: true        # téměř všechny skills

# Pořadí v pipeline (pro fabric-loop)
depends_on: [{PREREQUISITE_SKILLS}]
feeds_into: [{SUBSEQUENT_SKILLS}]
```

---

# ═══════════════════════════════════════════════════════════════
# PŘÍLOHA A — Checklist pro autora nového skillu
# ═══════════════════════════════════════════════════════════════

<!--
  Než skill považuješ za hotový, projdi tento checklist:
-->

## A.1 Strukturální checklist

- [ ] Frontmatter má `name` a `description`
- [ ] `description` je 1 věta, začíná velkým, končí tečkou
- [ ] Všech 12 sekcí (§1–§12) je vyplněno nebo explicitně odstraněno s komentářem proč
- [ ] Protokol (§2) je copy-paste z template (jen `{SKILL_NAME_SHORT}` nahrazeno)
- [ ] Preconditions (§3) mají bash kód, ne jen text
- [ ] Vstupy (§4) odkazují na config.md proměnné, ne na hardcoded cesty
- [ ] Výstupy (§5) mají schema reference
- [ ] Self-check (§10) má alespoň 3 testovatelné položky
- [ ] Failure handling (§11) pokrývá všechny fáze
- [ ] Metadata (§12) mají vyplněné `phase`, `step`, `depends_on`, `feeds_into`

## A.2 Kvalitativní checklist (prevence degradace z work-quality-analysis)

- [ ] §7 (Postup) je KONKRÉTNÍ — žádné vágní „analyzuj" nebo „napiš testy"
- [ ] §7 obsahuje PŘÍKLADY nebo ŠABLONY výstupu pro každý krok
- [ ] §7 definuje MINIMUM akceptovatelného výstupu per krok
- [ ] §7 definuje ANTI-PATTERNS (co je zakázáno)
- [ ] Pokud skill produkuje kód: je definován minimální test set (3: happy/edge/error)?
- [ ] Pokud skill analyzuje: vyžaduje alternativy a pseudokód?
- [ ] Pokud skill reviewuje: má explicitní fix strategie per finding typ?
- [ ] Pokud skill testuje: má coverage target a regression tracking?
- [ ] Instrukce jsou dostatečně detailní, aby JINÝ LLM (bez kontextu) dokázal vyrobit kvalitní výstup?

## A.3 Integration checklist

- [ ] Skill je registrován v fabric-loop step mappingu
- [ ] fabric-loop zná PASS/FAIL/REWORK sémantiku reportu
- [ ] Downstream skill ví, že tento skill existuje (dependency chain)
- [ ] fabric-check validuje výstupy tohoto skillu (pokud relevantní)

---

# ═══════════════════════════════════════════════════════════════
# PŘÍLOHA B — Vzory z existujících skills (reference)
# ═══════════════════════════════════════════════════════════════

## B.1 Protokol vzor (identický všude)

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "{SKILL_NAME_SHORT}" \
  --event start

# ... práce ...

python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "{SKILL_NAME_SHORT}" \
  --event end \
  --status OK \
  --report "{WORK_ROOT}/reports/{SKILL_NAME_SHORT}-{YYYY-MM-DD}.md"
```

## B.2 FAST PATH vzor (backlog-scan + governance-index)

```bash
python skills/fabric-init/tools/fabric.py backlog-index
python skills/fabric-init/tools/fabric.py governance-index
python skills/fabric-init/tools/fabric.py backlog-scan \
  --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

## B.3 Precondition vzor (backlog file + branch existence)

```bash
WIP_ITEM=$(python skills/fabric-init/tools/fabric.py state-get --field wip_item 2>/dev/null)
WIP_BRANCH=$(python skills/fabric-init/tools/fabric.py state-get --field wip_branch 2>/dev/null)

if [ ! -f "{WORK_ROOT}/backlog/${WIP_ITEM}.md" ]; then
  echo "STOP: backlog file missing for wip_item=$WIP_ITEM"
  exit 1
fi

if ! git rev-parse --verify "${WIP_BRANCH}" >/dev/null 2>&1; then
  echo "STOP: branch ${WIP_BRANCH} does not exist"
  exit 1
fi
```

## B.4 Quality gate vzor (lint → auto-fix → retry)

```bash
# Gate: Lint
if [ -n "{COMMANDS.lint}" ] && [ "{COMMANDS.lint}" != "TBD" ]; then
  {COMMANDS.lint}
  if [ $? -ne 0 ] && [ -n "{COMMANDS.lint_fix}" ]; then
    echo "Auto-fixing lint..."
    {COMMANDS.lint_fix}
    {COMMANDS.lint}  # retry 1×
    if [ $? -ne 0 ]; then
      echo "FAIL: lint still failing after auto-fix"
      # → intake item + report FAIL
    fi
  fi
fi
```

## B.5 Intake item vzor

```md
---
schema: fabric.intake_item.v1
title: "{Akční popis}"
source: {skill_name}
initial_type: {Task|Bug|Chore|Spike}
raw_priority: {3-10}
created: {YYYY-MM-DD}
status: new
linked_vision_goal: "{goal, pokud je zřejmé}"
---

## Kontext
{Proč tento item existuje — evidence}

## Doporučená akce
{Co s tím udělat — konkrétně}
```

## B.6 Report frontmatter vzor

```md
---
schema: fabric.report.v1
kind: {skill_name_short}
step: "{skill_name_short}"
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
score: {0-100, pokud skill má scoring}
---
```

## B.7 Shell quoting vzor (povinný pro git operace)

```bash
# VŽDY quotuj proměnné v git operacích
git checkout "${branch_name}"
git merge --no-ff "${feature_branch}"
git branch -d "${branch_name}"
git push origin --delete "${branch_name}"
git commit -m "feat(${task_id}): ${title} (sprint ${sprint_number})"
```

## B.8 Numeric validation vzor (pro countery)

```bash
COUNTER=$(grep 'counter_name:' "{file}" | awk '{print $2}')
COUNTER=${COUNTER:-0}
if ! echo "$COUNTER" | grep -qE '^[0-9]+$'; then
  COUNTER=0
  echo "WARN: non-numeric counter, reset to 0"
fi
```

---

# ═══════════════════════════════════════════════════════════════
# PŘÍLOHA C — Pokročilé vzory (pro komplexnější skills)
# ═══════════════════════════════════════════════════════════════

<!--
  Tyto vzory se nevyskytují ve VŠECH skills, ale jsou kritické
  pro skills, které modifikují kód, mergují branch, nebo orchestrují
  batch operace. Použij je, když jsou relevantní.
-->

## C.1 Parameter Parsing (pro skills s parametry z user promptu)

```bash
# Parsuj parametry z uživatelského vstupu
# Pattern: klíč=hodnota, case-insensitive
RAW_INPUT="$1"  # nebo z user prompt

PARAM_A=$(echo "$RAW_INPUT" | grep -oiE 'param_a\s*=\s*[^ ]+' | head -1 | sed 's/.*=\s*//')
PARAM_B=$(echo "$RAW_INPUT" | grep -oiE 'param_b\s*=\s*[^ ]+' | head -1 | sed 's/.*=\s*//')

# Defaulty a validace
PARAM_A=${PARAM_A:-"default_value"}
if ! echo "$PARAM_A" | grep -qE '^[a-z0-9_-]+$'; then
  echo "WARN: invalid param_a='$PARAM_A', using default"
  PARAM_A="default_value"
fi
```

## C.2 3-Level Fallback Chain (pro destruktivní operace)

```bash
# Použij když operace může nechat systém v nekonzistentním stavu
# Typicky: git merge, git rebase, file transformace

PRE_STATE=$(git rev-parse HEAD)  # záchytný bod

# Pokus 1: normální operace
git merge --no-ff "${branch}" 2>/dev/null
if [ $? -ne 0 ]; then
  # Level 1: standardní abort
  git merge --abort 2>/dev/null

  # Level 2: cleanup
  if [ -n "$(git status --porcelain)" ]; then
    git checkout -- . 2>/dev/null
    git clean -fd 2>/dev/null
  fi

  # Level 3: hard reset na záchytný bod
  if [ -n "$(git status --porcelain)" ]; then
    echo "WARN: cleanup failed, resetting to pre-operation state"
    git reset --hard "$PRE_STATE"
  fi

  echo "FAIL: merge aborted, creating intake item"
  # → intake item s popisem konfliktu
fi
```

## C.3 Regression Detection (před/po auto-fix)

```bash
# Zachyť baseline PŘED auto-fixem
BASELINE_RESULT=$({COMMANDS.test} 2>&1; echo "EXIT:$?")
BASELINE_EXIT=$(echo "$BASELINE_RESULT" | grep -oP 'EXIT:\K\d+')
BASELINE_PASS=$(echo "$BASELINE_RESULT" | grep -c " passed")

# Proveď auto-fix
{COMMANDS.lint_fix}

# Změř AFTER
AFTER_RESULT=$({COMMANDS.test} 2>&1; echo "EXIT:$?")
AFTER_EXIT=$(echo "$AFTER_RESULT" | grep -oP 'EXIT:\K\d+')
AFTER_PASS=$(echo "$AFTER_RESULT" | grep -c " passed")

# Porovnej
if [ "$AFTER_EXIT" -ne 0 ] && [ "$BASELINE_EXIT" -eq 0 ]; then
  echo "REGRESSION: auto-fix broke tests ($BASELINE_PASS passed → $AFTER_PASS passed)"
  git checkout -- .  # revert auto-fix
  # → intake item pro manuální fix
fi
```

## C.4 Persisted Counter (idempotence guard across rework)

```bash
# Čti counter z backlog item frontmatter
ITEM_FILE="{WORK_ROOT}/backlog/${TASK_ID}.md"
AUTOFIX_COUNT=$(grep 'autofix_count:' "$ITEM_FILE" | awk '{print $2}')
AUTOFIX_COUNT=${AUTOFIX_COUNT:-0}
if ! echo "$AUTOFIX_COUNT" | grep -qE '^[0-9]+$'; then AUTOFIX_COUNT=0; fi

MAX_AUTOFIX=3  # z config.md

if [ "$AUTOFIX_COUNT" -ge "$MAX_AUTOFIX" ]; then
  echo "STOP: autofix limit reached ($AUTOFIX_COUNT/$MAX_AUTOFIX)"
  # → intake item, nepokračuj v auto-fixu
else
  # Proveď auto-fix
  AUTOFIX_COUNT=$((AUTOFIX_COUNT + 1))
  # Ulož zpět do frontmatter
  sed -i "s/autofix_count:.*/autofix_count: $AUTOFIX_COUNT/" "$ITEM_FILE"
fi
```

## C.5 Multi-Task Batch Processing

```bash
# Pro skills zpracovávající více tasků najednou (close, analyze)
# Pattern: iteruj přes Task Queue, per-task processing, append-only report

TASK_IDS=$(grep -E '^\|' "{SPRINT_FILE}" | grep -v '^|.*---' | awk -F'|' '{print $2}' | tr -d ' ')

REPORT="{WORK_ROOT}/reports/{SKILL}-{DATE}.md"
echo "---" > "$REPORT"
echo "schema: fabric.report.v1" >> "$REPORT"
echo "kind: {SKILL}" >> "$REPORT"
echo "step: {SKILL}" >> "$REPORT"
echo "---" >> "$REPORT"
echo "" >> "$REPORT"
echo "# {SKILL} Report" >> "$REPORT"
echo "" >> "$REPORT"
echo "| Task | Status | Notes |" >> "$REPORT"
echo "|------|--------|-------|" >> "$REPORT"

for TASK_ID in $TASK_IDS; do
  echo "Processing: $TASK_ID"

  # Per-task preconditions
  if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
    echo "| $TASK_ID | SKIP | backlog file missing |" >> "$REPORT"
    continue
  fi

  # Per-task processing...
  # ...

  # Append to report (idempotent — re-run appends, dedup later)
  echo "| $TASK_ID | DONE | merged OK |" >> "$REPORT"
done
```

## C.6 Baseline Test Before Work (VERIFY-FIRST)

```bash
# Spusť testy PŘED jakoukoli změnou kódu
# Pokud baseline FAIL → STOP (neopravuj cizí regrese)

echo "Running baseline tests..."
timeout 300 {COMMANDS.test} > /tmp/baseline-test.log 2>&1
BASELINE_EXIT=$?

if [ $BASELINE_EXIT -eq 124 ]; then
  echo "WARN: baseline test timeout (300s)"
  # → intake item pro slow tests
elif [ $BASELINE_EXIT -ne 0 ]; then
  echo "WARN: baseline tests failing BEFORE our changes"
  echo "Failing tests:"
  grep -E "FAILED|ERROR" /tmp/baseline-test.log | head -10
  # Rozhodnutí: pokračovat s WARNINGem nebo STOP?
  # → závisí na skill (implement: pokračuj, close: STOP)
fi
```

## C.7 Timeout Handling (exit code 124)

```bash
# timeout vrací exit code 124
timeout 300 {COMMANDS.test} 2>&1
EXIT_CODE=$?

case $EXIT_CODE in
  0)   echo "PASS" ;;
  124) echo "TIMEOUT: test suite exceeded 300s"
       # → intake item pro optimalizaci testů
       # → report WARN (ne FAIL — timeout ≠ assertion failure)
       ;;
  *)   echo "FAIL: exit code $EXIT_CODE"
       # → standardní FAIL handling
       ;;
esac
```

## C.8 Governance VERIFY-FIRST (ADR/SPEC cross-check)

```bash
# Před implementací ověř, že plánované změny neporušují governance

ANALYSIS="{ANALYSES_ROOT}/${TASK_ID}-analysis.md"

# Extrahuj referenced ADRs
ADRS=$(grep -oP 'ADR-\d+' "$ANALYSIS" | sort -u)
for ADR in $ADRS; do
  ADR_FILE="{WORK_ROOT}/decisions/${ADR}*.md"
  ADR_STATUS=$(grep 'status:' $ADR_FILE 2>/dev/null | awk '{print $2}')
  if [ "$ADR_STATUS" = "deprecated" ] || [ "$ADR_STATUS" = "superseded" ]; then
    echo "WARN: task references ${ADR} which is ${ADR_STATUS}"
    # → intake item pro aktualizaci analýzy
  fi
done

# Extrahuj referenced SPECs
SPECS=$(grep -oP 'SPEC-\d+' "$ANALYSIS" | sort -u)
for SPEC in $SPECS; do
  SPEC_FILE="{WORK_ROOT}/specs/${SPEC}*.md"
  if [ ! -f $SPEC_FILE ]; then
    echo "WARN: task references ${SPEC} which does not exist"
  fi
done
```

## C.9 Safe Revert Strategy (no force push)

```bash
# Na main branch NIKDY nepoužívej git reset --hard (ztratíš historii)
# Místo toho použij git revert

MERGE_COMMIT=$(git log --oneline -1 --format=%H)

git revert --no-edit "$MERGE_COMMIT" 2>/dev/null
if [ $? -ne 0 ]; then
  git revert --abort 2>/dev/null
  echo "FAIL: cannot auto-revert merge $MERGE_COMMIT"
  # → intake item pro manuální revert
  # → NEPOUŽÍVEJ git push --force
fi
```

## C.10 WIP Lifecycle (state.md management)

```bash
# Skills, které modifikují WIP stav (POUZE implement a close)
# Implement: SET wip_item + wip_branch
# Close: RESET wip_item + wip_branch

# SET (fabric-implement):
python skills/fabric-init/tools/fabric.py state-set \
  --field wip_item --value "${TASK_ID}"
python skills/fabric-init/tools/fabric.py state-set \
  --field wip_branch --value "wip/${TASK_ID}"

# RESET (fabric-close, po merge):
python skills/fabric-init/tools/fabric.py state-set \
  --field wip_item --value "null"
python skills/fabric-init/tools/fabric.py state-set \
  --field wip_branch --value "null"
```

## C.11 Handoff Validation Pattern (shared precondition)

Použij tento pattern v JAKÉMKOLI skillu, který čte výstup z předchozího skillu. Validuje, že upstream artefakt existuje a má správnou strukturu.

```bash
# Validate upstream artifact exists and has required schema
# Use in ANY skill that reads from a previous skill's output
validate_handoff() {
  local FILE="$1"
  local REQUIRED_SCHEMA="$2"
  local REQUIRED_SECTIONS="$3"  # comma-separated

  if [ ! -f "$FILE" ]; then
    echo "STOP: handoff artifact missing: $FILE"
    return 1
  fi

  if [ -n "$REQUIRED_SCHEMA" ]; then
    if ! grep -q "^schema: $REQUIRED_SCHEMA" "$FILE"; then
      echo "WARN: $FILE missing schema: $REQUIRED_SCHEMA"
    fi
  fi

  IFS=',' read -ra SECTIONS <<< "$REQUIRED_SECTIONS"
  for SECTION in "${SECTIONS[@]}"; do
    if ! grep -q "^## $SECTION" "$FILE"; then
      echo "WARN: $FILE missing section: $SECTION"
    fi
  done
  return 0
}

# Usage examples:
# validate_handoff "$ANALYSIS_FILE" "fabric.report.v1" "Constraints,Plan,Tests"
# validate_handoff "$TEST_REPORT" "fabric.report.v1" "Summary,Evidence"
# validate_handoff "$REVIEW_REPORT" "fabric.report.v1" "Verdict,Findings"

# Typické precondition pattern:
# 1. Načti cestu k upstream reportu
# 2. Zavolej validate_handoff s požadovaným schematem
# 3. Pokud selže → STOP s jasnou zprávou jaký skill to má vytvořit
ANALYSIS_FILE="{ANALYSES_ROOT}/${TASK_ID}-analysis.md"
if ! validate_handoff "$ANALYSIS_FILE" "fabric.report.v1" "Constraints,Plan"; then
  echo "STOP: analysis artifact not ready — run fabric-analyze first"
  exit 1
fi
```

**Výhody:**
- Fail-fast na chybějícím upstream artefaktu (ne na vágní chybě později)
- Explicitní seznam vyžadovaných sekcí (dokumentace kontraktu)
- Reusable vzor (eliminuje copy-paste v preconditions)

# Analyze Workflow — Detailní postup

> Tento soubor obsahuje detailní kroky §7 Postup z SKILL.md.
> Čti pomocí Read toolu při provádění analýzy.

---

## State Validation (K1: State Machine)

```bash
CURRENT_PHASE=$(grep 'phase:' "{WORK_ROOT}/state.md" | awk '{print $2}')
EXPECTED_PHASES="planning"
if ! echo "$EXPECTED_PHASES" | grep -qw "$CURRENT_PHASE"; then
  echo "STOP: Current phase '$CURRENT_PHASE' is not valid for fabric-analyze. Expected: $EXPECTED_PHASES"
  exit 1
fi
```

## Path Traversal Guard (K7: Input Validation)

```bash
validate_path() {
  local INPUT_PATH="$1"
  if echo "$INPUT_PATH" | grep -qE '\.\.'; then
    echo "STOP: path traversal detected in: $INPUT_PATH"
    exit 1
  fi
}
```

---

## 0) Deterministická příprava (rychlá)

```bash
python skills/fabric-init/tools/fabric.py backlog-index
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null
if [ $? -ne 0 ]; then
  echo "WARN: governance-index failed — continuing without governance data"
fi
```

**Governance index error handling (P2 fix):** Pokud governance index selže, analýza pokračuje s warningem.

---

## 1) Načti sprint plan a targety

- Najdi aktivní sprint v `state.md` a otevři `sprints/sprint-{N}.md`.
- Z tabulky `Sprint Targets` vezmi seznam targetů.
- Pokud `Task Queue` už existuje a není prázdná: doplň jen chybějící tasks.

---

## 2) Pro každý target vytvoř návrh tasks

**K2 Fix: Loop termination with numeric validation**
```bash
MAX_ANALYSIS_TASKS=${MAX_ANALYSIS_TASKS:-200}
ANALYSIS_COUNTER=0

if ! echo "$MAX_ANALYSIS_TASKS" | grep -qE '^[0-9]+$'; then
  MAX_ANALYSIS_TASKS=200
  echo "WARN: MAX_ANALYSIS_TASKS not numeric, reset to default (200)"
fi
```

**Size guard (P2 fix):**
```bash
for target in $TARGETS; do
  ANALYSIS_COUNTER=$((ANALYSIS_COUNTER + 1))

  if ! echo "$ANALYSIS_COUNTER" | grep -qE '^[0-9]+$'; then
    ANALYSIS_COUNTER=0
    echo "WARN: ANALYSIS_COUNTER corrupted, reset to 0"
  fi

  if [ "$ANALYSIS_COUNTER" -gt "$MAX_ANALYSIS_TASKS" ]; then
    echo "WARN: max analysis iterations ($ANALYSIS_COUNTER) reached — stopping"
    break
  fi

  FILE_SIZE=$(wc -c < "{WORK_ROOT}/backlog/${target}.md" 2>/dev/null || echo 0)
  MAX_SIZE=102400  # 100KB
  if [ "$FILE_SIZE" -gt "$MAX_SIZE" ]; then
    echo "WARN: backlog item ${target}.md exceeds ${MAX_SIZE} bytes — skipping"
    continue
  fi
done
```

Pro každý target:
1. Otevři backlog item `{WORK_ROOT}/backlog/{target}.md`
2. Urči typ (Epic/Story/Task/Bug/Chore/Spike)
3. Epic/Story → rozpadni na 3–12 tasks; Task/Bug/Chore/Spike → 1 task

Každý task musí mít: ID, Type, Status, Description, Estimate.

**Effort sanity check:**
```bash
TOUCHED_FILES=$(echo "{files_list}" | wc -w)
if [ "$EFFORT" = "S" ] && [ "$TOUCHED_FILES" -ge 5 ]; then
  echo "WARN: task $TASK_ID estimated S but touches $TOUCHED_FILES files — consider M or L"
fi
```

**Anti-patterns:**
- ❌ Vágní task popis ("implementuj feature X")
- ❌ Task bez testovatelných AC
- ❌ Estimate bez zdůvodnění
- ❌ Epic/Story v Task Queue bez rozkladu na Tasks

---

## 2.1) Procesní analýza per task (ABSOLUTNĚ POVINNÉ)

> KONTRAKT: KAŽDÝ task MUSÍ mít kompletní procesní analýzu se VŠEMI čtyřmi komponenty.

### A) Datový tok (§2.1A, POVINNÉ)

ASCII diagram s minimálně 3-5 kroky a error handling:
```
{INPUT} → [Krok1] → [Krok2] → [Krok3] → [OUTPUT]
          ↓ err      ↓ err      ↓ err      ↓ err
        status1    status2    status3    status4
```

Anti-pattern ❌: Vynechavat error paths.

### B) Dotčené moduly a závislosti (§2.1B, POVINNÉ)

```markdown
| Module | Type | Upstream deps | Downstream deps | Risk |
|--------|------|---------------|-----------------|------|
| src/llmem/{path} | MODIFY/CREATE | {modules} | {modules} | LOW/MEDIUM/HIGH |
```

Anti-pattern ❌: Vágní seznam ("api/, triage/").

### C) Message/Entity lifecycle (§2.1C, POVINNÉ pokud task mění entity)

Pokud task nemění lifecycle: `N/A — task nemění entity lifecycle.`

### D) Process-map cross-reference (§2.1D, POVINNÉ)

```bash
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
TOUCHED_FILES="{files_from_module_table}"

if [ ! -f "$PROCESS_MAP" ]; then
  echo "NOTE: process-map.md not found at $PROCESS_MAP"
  exit 0
fi

echo "=== AFFECTED PROCESSES FOR $TASK_ID ==="
for file in $TOUCHED_FILES; do
  MATCHES=$(grep -n "$file" "$PROCESS_MAP" 2>/dev/null | cut -d: -f1 || true)
  if [ -n "$MATCHES" ]; then
    while IFS= read -r line_num; do
      awk "NR < $line_num && /^##\s+|^###\s+/ {last=NR; header=\$0} \
           NR == $line_num {print header}" "$PROCESS_MAP" || true
    done <<< "$MATCHES"
  fi
done | sort -u > /tmp/affected_processes.txt

if [ -s /tmp/affected_processes.txt ]; then
  echo "Affected processes:"
  cat /tmp/affected_processes.txt
else
  echo "No documented processes found for touched files."
fi
```

Anti-patterns:
- ❌ Přeskočit procesní mapování ("je to jednoduchý task")
- ✅ ASCII diagram VŽDY, i kdyby měl jen 3 boxy
- ✅ Fail-open: chybí process-map → pokračuj, zaznamenáš do analýzy

---

## 3) Governance constraints per task

- Z `decisions/INDEX.md` a `specs/INDEX.md` vyber relevantní kontrakty.
- Pokud je konflikt: nevymýšlej workaround, vytvoř intake item `governance-clarification-{task_id}.md`.

---

## 4) Zapiš per-task analýzy

> **Detailní template:** Přečti `references/analysis-template.md` pomocí Read toolu.

Pro každý task vytvoř `{ANALYSES_ROOT}/{task_id}-analysis.md` podle analysis-template.
- Otevřené otázky → `status: DRAFT`, `Task Queue Status = DESIGN`
- Vše jasné + všechny povinné sekce → `status: READY`, `Task Queue Status = READY`

Contract enforcement: spusť validaci (viz analysis-template.md) PŘED nastavením READY.

**DŮLEŽITÉ: Synchronizace statusu** — aktualizuj VŠECHNA tři místa:
1. Per-task analýza (frontmatter `status:`)
2. Sprint plan Task Queue (sloupec `Status`)
3. Backlog item (frontmatter `status:`)

---

## 4.1) Cross-task analýza (VŽDY)

> KONTRAKT: Cross-task analýza VŽDY, i pro single task.

**Pro 1-2 tasks:**
```markdown
## Cross-task Analysis
N/A — Sprint contains {N} task(s) only.
- Impact on other backlog: verified
- Future dependency: {note}
```

**Pro ≥3 tasks:**

**B1) Sdílené patterny:**
- Používají ≥2 tasks stejný modul? → identifikuj POŘADÍ
- Zavádí ≥2 tasks nové modely? → ověř konzistenci
- Mění ≥2 tasks stejný ADR? → ověř interpretaci

**B2) Závislosti a konflikty:**

| Task A | Task B | Interaction | Resolution | Order |
|--------|--------|-------------|-----------|-------|
| {id} | {id} | shared_module/new_model/conflict_adrs/data_dependency | {solution} | A → B |

**B3) Optimální pořadí (scoring):**
```
For each position in queue:
  candidates = tasks with no unmet dependencies
  score: + (3 - effort) + (3 - risk)  (prefer simpler early)
  place highest-scored candidate
```

**B4) Zapiš do reportu** sekci Cross-task Analysis se: Shared Modules, Execution Order, Parallel Opportunities, Risk Mitigation.

**Anti-patterns:**
- ❌ Analyzovat tasks izolovaně
- ❌ Nechat pořadí náhodné
- ❌ Ignorovat shared module conflicts

---

## 5) Aktualizuj sprint plan deterministicky

```bash
python skills/fabric-init/tools/fabric.py plan-apply --plan "{WORK_ROOT}/sprints/sprint-{N}.md" --patch "{WORK_ROOT}/plans/analyze-{run_id}.yaml"
```

> **OWNERSHIP:** Sekce `## Task Queue` v sprint plánu je vlastněna výhradně `fabric-analyze`.

---

## 6) Vygeneruj analyze report

Shrň: kolik targetů, kolik tasks (READY vs DESIGN), jaké ADR/SPEC constraints, jaké clarifications do intake.

Ulož do `{WORK_ROOT}/reports/analyze-{YYYY-MM-DD}-{run_id}.md`:
```yaml
---
schema: fabric.report.v1
kind: analyze
run_id: "analyze-{YYYY-MM-DD}-{RUN_ID}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: PASS
---
```

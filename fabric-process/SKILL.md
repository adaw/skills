---
name: fabric-process
description: "Mapuje vnější procesy (user↔system interakce), vnitřní procesní řetězce (kauzální závislosti v kódu) a cross-mapping mezi nimi. Vytváří živou procesní mapu konzumovanou downstream skills."
---

# FABRIC-PROCESS — Business Process Mapping

<!-- built from: builder-template -->

---

## §1 — Účel

Vytvořit a udržovat **živou mapu business procesů** systému: jaké vnější interakce existují (kdo systém používá a jak),
jaké vnitřní řetězce běží (co se děje v kódu když se něco stane), a jak se tyto dvě vrstvy propojují.

Bez process mapy:
- Gap analysis nemá proti čemu validovat pokrytí (neví jaké procesy existují vs. chybí)
- Review neví, jestli změna v `scoring.py` rozbila recall pipeline
- Implement neví, jaké kauzální závislosti musí zachovat
- Nový člen týmu nemá přehled jak systém funguje jako celek

**Tři vrstvy process mapy:**
1. **Vnější procesy (external):** Actor → Trigger → Entry point → Response (user↔system, system↔system)
2. **Vnitřní procesy (internal):** Entry point → Validation → Service → Storage → Side effects → Response (kauzální řetězce)
3. **Cross-mapping:** Propojení vnější→vnitřní, identifikace orphanů (kód bez rozhraní, rozhraní bez kódu)

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "process" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "process" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "process" \
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

# --- Precondition 3: CODE_ROOT existuje a obsahuje Python soubory ---
CODE_ROOT=$(grep 'CODE_ROOT:' "{WORK_ROOT}/config.md" | awk '{print $2}' | tr -d '"')
if [ ! -d "${CODE_ROOT}" ]; then
  echo "STOP: CODE_ROOT '${CODE_ROOT}' not found"
  exit 1
fi

PYTHON_COUNT=$(find "${CODE_ROOT}" -name "*.py" -type f 2>/dev/null | wc -l)
if [ "$PYTHON_COUNT" -eq 0 ]; then
  echo "STOP: No Python files found in CODE_ROOT"
  exit 1
fi

# --- Precondition 4: Processes adresář (vytvoř pokud chybí) ---
mkdir -p "{WORK_ROOT}/fabric/processes"

# --- Precondition 5: Vision existuje (volitelné — warn) ---
if [ ! -f "{WORK_ROOT}/vision.md" ]; then
  echo "WARN: vision.md missing — process extraction will be codebase-only (no vision cross-reference)"
fi
```

**Dependency chain:**
```
fabric-init → fabric-architect → [fabric-process] → fabric-gap
```

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` — cesty, schémata, příkazy
- `{WORK_ROOT}/state.md` — aktuální fáze/krok
- `{CODE_ROOT}/` — zdrojový kód (Python soubory: routes, services, models, storage)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` — reference pro vnější procesy (plánované features)
- `{WORK_ROOT}/fabric/processes/process-map.md` — předchozí verze (pro delta detekci)
- `{DECISIONS_ROOT}/*.md` — ADR odkazující na procesy
- `{SPECS_ROOT}/*.md` — specifikace (zejména LLMEM_API_V1, LLMEM_RECALL_PIPELINE_V1)
- `{TEST_ROOT}/` — testovací soubory (pro validaci pokrytí procesů testy)
- `{WORK_ROOT}/intake/` — pending items se source=implement (korekční mechanismus)

---

## §5 — Výstupy

### Primární (vždy)
- `{WORK_ROOT}/fabric/processes/process-map.md` (schema: `fabric.process-map.v1`) — Master dokument
- Report: `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- `{WORK_ROOT}/fabric/processes/{process-id}.md` (schema: `fabric.process.v1`) — Individuální procesy (1 soubor per proces)
- Intake items: `{WORK_ROOT}/intake/process-{slug}.md` (schema: `fabric.intake_item.v1`) — pro nalezené orphany/gapy

---

## §6 — Deterministic FAST PATH

Než začneš analyzovat, proveď deterministické kroky:

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index

# 3. Route inventory (strojový sken)
echo "=== Route Inventory ==="
ROUTE_FILES=$(find "${CODE_ROOT}" -path "*/api/routes/*.py" -type f 2>/dev/null)
ROUTE_COUNT=0
for rf in $ROUTE_FILES; do
  COUNT=$(grep -cE '@router\.(get|post|put|delete|patch)' "$rf" 2>/dev/null || echo 0)
  ROUTE_COUNT=$((ROUTE_COUNT + COUNT))
  echo "  $rf: $COUNT routes"
done
echo "Total routes found: $ROUTE_COUNT"

# 4. Service inventory (strojový sken)
echo "=== Service Inventory ==="
grep -rn "^class.*Service" "${CODE_ROOT}" --include="*.py" 2>/dev/null | while read line; do
  echo "  $line"
done

# 5. CLI command inventory
echo "=== CLI Inventory ==="
grep -rn "def.*command\|@app.command\|@click.command\|add_parser" "${CODE_ROOT}" --include="*.py" 2>/dev/null | head -20

# 6. Model inventory
echo "=== Model Inventory ==="
grep -rn "^class.*BaseModel\|^class.*Base)\|^class.*Enum" "${CODE_ROOT}" --include="*.py" 2>/dev/null | while read line; do
  echo "  $line"
done

# 7. Předchozí process map (pokud existuje)
PREV_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if [ -f "$PREV_MAP" ]; then
  PREV_EXT=$(grep -c "^| ext-" "$PREV_MAP" 2>/dev/null || echo 0)
  PREV_INT=$(grep -c "^| int-" "$PREV_MAP" 2>/dev/null || echo 0)
  PREV_UPDATED=$(grep "^updated:" "$PREV_MAP" | cut -d' ' -f2)
  echo "Previous map: $PREV_EXT external, $PREV_INT internal (updated: $PREV_UPDATED)"
else
  echo "No previous process map found (first run)"
fi
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### 7.1) P1: Extract External Processes

**Co:** Identifikuj VŠECHNY vnější interakce — kdo systém používá, přes jaké rozhraní, s jakým výsledkem.

**Jak (detailní instrukce):**

1. **API Routes** — Pro každý soubor v `{CODE_ROOT}/api/routes/*.py`:
   - Najdi všechny dekorátory `@router.get|post|put|delete|patch`
   - Pro každý endpoint extrahuj: HTTP metodu, cestu, handler funkci, request/response modely
   - Identifikuj actora: kdo typicky volá tento endpoint? (agent, admin, monitoring, jiný systém)

2. **CLI Commands** — Hledej v `{CODE_ROOT}` CLI entry pointy:
   - Click commands (`@click.command`, `@app.command`)
   - Argparse (`add_parser`, `add_argument`)
   - Pro každý: název příkazu, argumenty, co dělá

3. **Event Handlers** — Hledej asynchronní handlery:
   - Background tasks (`asyncio.create_task`, `@app.on_event`)
   - Queue consumers (`await queue.get()`)
   - Webhooks, scheduled jobs

4. **System-to-System** — Hledej outbound volání:
   - HTTP klienti (`httpx`, `aiohttp`, `requests`)
   - Database connections (`qdrant_client`, `asyncpg`)
   - Message queues, pub/sub

Pro každý nalezený proces vyplň tabulku:

```
| Process ID | Kategorie | Actor(s) | Trigger | Entry Point | Response/Output | Status |
```

**Konvence Process ID:**
- Vnější: `ext-{doména}-{akce}` (např. `ext-capture-event`, `ext-cli-serve`, `ext-health-check`)
- Vnitřní: `int-{flow}-{popis}` (např. `int-capture-triage-store`, `int-recall-multi-layer`)
- Cross: `cross-{vnější}-to-{vnitřní}` (odkaz, ne samostatný process)

**Minimum:**
- Každý API route MUSÍ mít odpovídající external process
- Každý CLI command MUSÍ mít odpovídající external process
- Tabulka MUSÍ obsahovat: ID, Actor, Trigger, Entry Point, Status

**Anti-patterns:**
- NEZAPISUJ procesy, které neexistují v kódu (to jsou PLANNED, ne ACTIVE)
- NEVYNECHÁVEJ "nudné" endpointy (healthz, metrics) — ty jsou kritické pro operations
- NEPŘESKAKUJ system-to-system interakce (database, cache) — ty jsou vnitřní procesy

**Šablona:**

```markdown
## External Processes

### API Endpoints

| Process ID | Actor(s) | Trigger | Entry Point | Response | Status |
|---|---|---|---|---|---|
| ext-capture-event | agent, tool | Tool execution completes | POST /capture/event | CaptureResponse (event_id, stored_memories) | ACTIVE |
| ext-recall-query | agent | Before agent turn | POST /recall | RecallResponse (XML injection block) | ACTIVE |
| ext-health-check | monitoring | Health probe (periodic) | GET /healthz | HealthResponse (status, version) | ACTIVE |

### CLI Commands

| Process ID | Actor(s) | Trigger | Entry Point | Output | Status |
|---|---|---|---|---|---|
| ext-cli-serve | sysadmin | Manual start | `llmem serve` | HTTP server listening on :8080 | ACTIVE |
| ext-cli-capture | user, script | Manual/scripted | `llmem capture --text "..."` | Memory stored confirmation | ACTIVE |
```

---

### 7.2) P2: Trace Internal Process Chains

**Co:** Pro KAŽDÝ vnější proces (z P1) sleduj vnitřní call chain — co se děje od entry pointu po response.

**Jak (detailní instrukce):**

1. **Otevři handler funkci** z P1 entry pointu
2. **Sleduj volání** krok po kroku:
   - Handler → Service method → Helper/Utility → Storage → Return
3. **Pro každý krok zapiš:**
   - Soubor a funkce/metoda
   - Co se na vstupu přijímá a co se vrací
   - Jaké side effects nastávají (DB write, file append, queue push, log)
4. **Identifikuj KAUZÁLNÍ ZÁVISLOSTI:**
   - "Pokud se změní model `ObservationEvent.text` → `triage_event()` dostane jiný vstup → scoring se změní → jiné memories se uloží → recall vrátí jiné výsledky"
   - "Pokud se změní `combine_score()` → recall ranking se změní → injection block bude jiný → agent dostane jiný kontext"
5. **Zapiš contract_modules:** Které soubory MUSÍ zůstat konzistentní, aby proces fungoval

**Pro každý vnitřní proces vyplň ASCII call chain:**

```
Entry: POST /capture/event
  │
  ├─ 1. routes/capture.py::capture_event()
  │     Input: ObservationEventIn (validated by Pydantic)
  │     Calls: CaptureService.capture()
  │
  ├─ 2. services/capture_service.py::CaptureService.capture()
  │     ├─ Generate event_id (UUIDv7 from content_hash — D0002)
  │     ├─ LogManager.append(event) → JSONL (source of truth — D0003)
  │     ├─ prepare() → triage_event()
  │     │     ├─ patterns.detect_secrets() → sensitivity tagging
  │     │     ├─ score_importance() → MemoryTier (must_remember/nice_to_have/ignore)
  │     │     ├─ mask_pii() if non-secret item contains PII
  │     │     └─ return list[MemoryItem]
  │     └─ store(items) → Backend.upsert()
  │
  ├─ 3. storage/backends/{inmemory|qdrant}.py::upsert()
  │     Side effect: Qdrant collection updated (or dict in InMemory)
  │
  └─ Return: CaptureResponse(ok=True, stored_memories=[ids])

Contract modules: [routes/capture.py, services/capture_service.py, triage/heuristics.py, triage/patterns.py, storage/log_jsonl.py, storage/backends/]
Governance: D0001 (secrets), D0002 (IDs), D0003 (event-sourcing)
```

**Minimum:**
- KAŽDÝ vnější proces (ACTIVE) MUSÍ mít traced vnitřní chain
- Chain MUSÍ být ≥3 kroky hluboký (handler→service→storage minimum)
- Contract_modules MUSÍ být vyplněné (downstream skills je potřebují)
- Kauzální závislosti MUSÍ být explicitně popsané

**Anti-patterns:**
- NETRASUJ jen "šťastnou cestu" — zapiš i error paths (co se stane při 400, 500, timeout)
- NEPŘESKAKUJ side effects — JSONL append, queue push, cache invalidation jsou KRITICKÉ
- NEPIŠ vágní "calls service" — uveď PŘESNOU metodu a soubor
- NEHÁDEJ — pokud si nejsi jistý call chainem, přečti kód

**Šablona individuálního process souboru:**

```markdown
---
schema: fabric.process.v1
id: int-capture-triage-store
category: internal
actors: [agent, tool]
status: ACTIVE
entry_point: "CaptureService.capture()"
contract_modules: [services/capture_service.py, triage/heuristics.py, triage/patterns.py, storage/log_jsonl.py]
related_external: [ext-capture-event, ext-capture-batch, ext-cli-capture]
governance: [D0001, D0002, D0003]
---

## Summary
Single-event capture pipeline: validates input, triages importance, masks secrets/PII, stores to backend.

## Call Chain
[ASCII diagram as above]

## Causal Dependencies
- ObservationEvent.text → triage scoring → MemoryTier assignment → storage decision
- D0001 secrets policy → sensitivity tagging → recall filtering (allow_secrets gate)
- D0002 content_hash → deterministic event_id → idempotency (duplicate detection)

## Side Effects
- JSONL log: immutable append (source of truth for rebuild)
- Qdrant/InMemory: upsert (queryable by recall)

## Error Paths
- Invalid input → 400 (Pydantic validation)
- Backend unavailable → 500 but fail-open (log warning, event still in JSONL)
- Secret detected → tagged sensitivity=secret, stored but filtered on recall

## Test Coverage
- Unit: tests/test_capture_service.py
- Integration: tests/test_triage_and_recall.py
- E2E: tests/e2e/ (if present)
```

---

### 7.3) P3: Cross-Mapping & Orphan Detection

**Co:** Propoj vnější procesy s vnitřními řetězci. Najdi nesoulady — orphany.

**Jak (detailní instrukce):**

1. **Pro každý vnější proces** zapiš, které vnitřní řetězce spouští:
   ```
   ext-capture-event → [int-capture-triage-store, int-async-capture-worker]
   ext-recall-query → [int-recall-multi-layer]
   ext-health-check → [int-health-probe] (simple, no chain)
   ```

2. **Orphan detection — vnější bez vnitřního:**
   - Pokud vnější proces nemá žádný traced vnitřní řetězec → ORPHAN EXTERNAL
   - Akce: Zkontroluj jestli endpoint má implementaci. Pokud ne → intake item (source=process, type=Bug)

3. **Orphan detection — vnitřní bez vnějšího:**
   - Projdi `{CODE_ROOT}` a hledej public functions/classes, které NEJSOU volané z žádného traced chain
   - Zvlášť pozor na: utility moduly, helper funkce, deprecated kód
   - Pokud nalezneš kód bez vnějšího rozhraní → klasifikuj:
     - **INTERNAL_ONLY** (správně — interní helper, např. `score_importance()`)
     - **DEAD_CODE** (nikdo to nevolá → intake item, type=Chore)
     - **UNDOCUMENTED** (volá se, ale z kódu který není v žádném procesu → rozšíř process mapu)

4. **Vision cross-reference:**
   - Pokud existuje `vision.md`, porovnej:
     - Features z vize, které NEMAJÍ odpovídající vnější proces → PLANNED (ne orphan)
     - Vnější procesy, které NEJSOU ve vizi → buď operational (healthz) nebo drift

**Minimum:**
- Každý vnější ACTIVE proces MUSÍ mít ≥1 vnitřní řetězec
- Cross-mapping tabulka MUSÍ být kompletní
- Orphan lista MUSÍ rozlišovat DEAD_CODE / INTERNAL_ONLY / UNDOCUMENTED

**Šablona cross-mapping:**

```markdown
## Cross-Layer Mappings

| External Process | Internal Chain(s) | Verified |
|---|---|---|
| ext-capture-event | int-capture-triage-store, int-async-capture-worker | ✓ |
| ext-recall-query | int-recall-multi-layer | ✓ |
| ext-cli-serve | int-server-startup | ✓ |

## Orphan Detection

### External without implementation (CRITICAL)
- [ ] ext-cli-knowledge-add — documented in vision, no CLI code yet (→ PLANNED)

### Code without external interface
- InMemoryBackend.search_hybrid() — INTERNAL_ONLY (dev/test backend, correct)
- score_importance() — INTERNAL_ONLY (helper called from prepare(), correct)

### Unresolved
(žádné, nebo seznam s intake items)
```

---

### 7.4) P4: Validate Against Reality

**Co:** Ověř, že dokumentované procesy odpovídají reálnému chování kódu. Ne statická analýza — skutečné spuštění.

**Jak (detailní instrukce):**

1. **Spusť existující testy:**
   ```bash
   COMMANDS_TEST=$(grep 'test:' "{WORK_ROOT}/config.md" | head -1 | awk '{$1=""; print $0}' | xargs)
   if [ -n "$COMMANDS_TEST" ] && [ "$COMMANDS_TEST" != "TBD" ]; then
     timeout 300 $COMMANDS_TEST -x --tb=line -q 2>&1 | tail -20
     TEST_EXIT=$?
     echo "Test exit code: $TEST_EXIT"
   else
     echo "WARN: No test command configured — skip runtime validation"
   fi
   ```

2. **Ověř test pokrytí per proces:**
   - Pro každý vnitřní proces (contract_modules) zkontroluj, jestli existuje odpovídající test:
   ```bash
   for MODULE in ${CONTRACT_MODULES}; do
     TEST_FILE=$(echo "$MODULE" | sed 's|/|_|g' | sed 's|\.py$||')
     if find "${TEST_ROOT}" -name "*${TEST_FILE}*" -o -name "test_${TEST_FILE}*" 2>/dev/null | grep -q .; then
       echo "✓ Process module $MODULE has tests"
     else
       echo "⚠ Process module $MODULE — no matching test file found"
     fi
   done
   ```

3. **Stub detection** v contract modules:
   ```bash
   for MODULE in ${CONTRACT_MODULES}; do
     STUBS=$(grep -cnE '^\s*(pass|raise NotImplementedError|# TODO|# FIXME)' "${CODE_ROOT}/${MODULE}" 2>/dev/null || echo 0)
     if [ "$STUBS" -gt 0 ]; then
       echo "⚠ Process module $MODULE contains $STUBS stubs/TODOs"
     fi
   done
   ```

4. **Contract governance check:**
   - Pro každý proces s governance references (D0001, D0002, ...):
     - Ověř, že ADR stále existuje a je `accepted`
     - Pokud ADR je `deprecated` nebo `superseded` → intake item

**Minimum:**
- Testy MUSÍ projít (pokud existují) — pokud FAIL → report WARN
- Každý ACTIVE proces MUSÍ mít ≥1 test file pokrývající jeho contract_modules
- Žádný contract module nesmí být stub (pass/NotImplementedError)

**Anti-patterns:**
- NESPOUŠTĚJ testy pokud `COMMANDS.test` je `TBD` — jen zaloguj WARN
- NEBLOKUJ na test FAIL — report WARN a pokračuj (process mapping je analytický skill)
- NEPŘEDSTÍREJ test pokrytí — pokud test neexistuje, řekni to přímo

---

### 7.5) P5: Update Process Map + Generate Report

**Co:** Zapiš/aktualizuj master `process-map.md`, vytvoř individuální process soubory, generuj execution report.

**Jak (detailní instrukce):**

1. **Zapiš/aktualizuj `process-map.md`:**
   - Pokud existuje předchozí verze → aktualizuj (přidej nové, odstraň deprecated, aktualizuj timestamps)
   - Pokud neexistuje → vytvoř od nuly

   **Process map formát:**
   ```markdown
   ---
   schema: fabric.process-map.v1
   kind: process-map
   version: "1.0"
   created: {YYYY-MM-DD}
   updated: {YYYY-MM-DD}
   last_validated: {YYYY-MM-DD}
   validation_status: VALID
   external_count: {N}
   internal_count: {N}
   orphan_count: {N}
   ---

   # LLMem Process Map

   > Živá mapa business procesů. Aktualizuje `fabric-process` v orientační fázi.
   > Downstream skills: fabric-gap (coverage), fabric-review (chain validation),
   > fabric-check (freshness), fabric-analyze (affected processes).

   ## External Processes (vnější)

   {tabulky z P1 — per kategorie: API, CLI, System-to-System}

   ## Internal Processes (vnitřní)

   {per-process: ID, trigger, call chain, contract_modules, governance}

   ## Cross-Layer Mappings

   {tabulka z P3: external → internal chain(s)}

   ## Orphan Detection

   {orphan lista z P3 s klasifikací}

   ## Validation Notes

   - Last validated: {datum}
   - Test result: {PASS/FAIL/SKIP}
   - Stale threshold: 7 days
   ```

2. **Vytvoř individuální process soubory:**
   - Pro každý ACTIVE proces (vnější i vnitřní) vytvoř `{WORK_ROOT}/fabric/processes/{process-id}.md`
   - Použij schema `fabric.process.v1` (viz šablona v P2)
   - Pokud soubor existuje → aktualizuj (zachovej Discussion sekci)

3. **Vytvoř intake items pro nalezené problémy:**
   ```bash
   # Pro každý orphan/gap:
   python skills/fabric-init/tools/fabric.py intake-new \
     --source "process" \
     --slug "{type}-{process-id}" \
     --title "{Popis problému}"
   ```

4. **Generuj report** (viz §9)

**Minimum:**
- `process-map.md` MUSÍ existovat po dokončení
- Process map MUSÍ obsahovat VŠECHNY 4 sekce (External, Internal, Cross-Layer, Orphans)
- Počet external processes MUSÍ odpovídat počtu nalezených routes + CLI commands
- Report MUSÍ mít verdikt a metriky

**Anti-patterns:**
- NEPIŠ process mapu bez reálného skenování kódu — musí odrážet skutečnost
- NEMAZEJ Discussion sekce v individuálních process souborech (anotace od lidí)
- NEVYTVÁŘEJ intake items pro PLANNED features (ty nejsou orphany)

---

## §8 — Quality Gates

### Gate 1: Process Map Schema Validation
```bash
# Ověř YAML frontmatter
PROCESS_MAP="{WORK_ROOT}/fabric/processes/process-map.md"
if head -20 "$PROCESS_MAP" | grep -q "^schema: fabric.process-map.v1"; then
  echo "PASS: process-map schema valid"
else
  echo "FAIL: process-map missing or invalid schema"
fi
```
- PASS: Schema přítomné a parsovatelné
- FAIL: Vytvoř intake item + report FAIL

### Gate 2: Route Coverage
```bash
# Počet routes v kódu vs. počet external processes v mapě
CODE_ROUTES=$(grep -rE '@router\.(get|post|put|delete|patch)' "${CODE_ROOT}/api/routes/" --include="*.py" 2>/dev/null | wc -l)
MAP_EXTERNALS=$(grep -c "^| ext-" "$PROCESS_MAP" 2>/dev/null || echo 0)

if [ "$MAP_EXTERNALS" -ge "$CODE_ROUTES" ]; then
  echo "PASS: All $CODE_ROUTES routes documented ($MAP_EXTERNALS in map)"
else
  echo "WARN: $CODE_ROUTES routes in code but only $MAP_EXTERNALS in process map"
fi
```
- PASS: Všechny routes mají odpovídající external process
- WARN: Chybí → vytvoř intake item (nesmí blokovat)

### Gate 3: No Duplicate Process IDs
```bash
DUPES=$(grep "^id:" {WORK_ROOT}/fabric/processes/*.md 2>/dev/null | awk '{print $2}' | sort | uniq -d)
if [ -z "$DUPES" ]; then
  echo "PASS: No duplicate process IDs"
else
  echo "FAIL: Duplicate IDs: $DUPES"
fi
```
- PASS: Žádné duplikáty
- FAIL: Deduplikuj ručně + report FAIL

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: process
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
---

# process — Report {YYYY-MM-DD}

## Souhrn
{1–3 věty: kolik procesů nalezeno, kolik traced, kolik orphanů, verdikt}

## Metriky

| Metrika | Hodnota |
|---------|---------|
| External processes (ACTIVE) | {N} |
| Internal chains (traced) | {N} |
| Cross-mappings | {N} |
| Orphans (external unimplemented) | {N} |
| Orphans (dead code) | {N} |
| Orphans (undocumented) | {N} |
| Process files created/updated | {N} |
| Test validation | {PASS/FAIL/SKIP} |
| Contract modules total | {N} |
| Contract modules with tests | {N} |
| Contract modules with stubs | {N} |

## Detaily

### External Processes
{Kompaktní tabulka: ID | Entry Point | Status}

### Internal Chains
{Kompaktní tabulka: ID | Trigger | Contract Modules Count | Governance}

### Orphan Analysis
{Klasifikovaný seznam: CRITICAL (unimplemented) / WARN (dead code) / INFO (internal only)}

### Causal Dependencies (klíčové)
{Top 5 nejkritičtějších kauzálních řetězců — změny v těchto modulech mají největší dopad}

## Delta (vs. předchozí mapa)
{Pokud existovala předchozí process-map.md: co se změnilo (nové/odstraněné/modified procesy)}

## Intake items vytvořené
{Seznam nebo "žádné"}

## Warnings
{Seznam nebo "žádné"}
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Process map existuje: `{WORK_ROOT}/fabric/processes/process-map.md`
- [ ] Report existuje: `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md`
- [ ] Process map má validní YAML frontmatter (schema: fabric.process-map.v1)

### Quality checks
- [ ] Počet external processes ≥ počet API routes v kódu
- [ ] KAŽDÝ ACTIVE external process má ≥1 internal chain traced
- [ ] KAŽDÝ internal chain má vyplněné contract_modules (není prázdný seznam)
- [ ] Cross-mapping tabulka je kompletní (žádný external bez řádku)
- [ ] Orphan detection sekce existuje a rozlišuje DEAD_CODE / INTERNAL_ONLY / UNDOCUMENTED
- [ ] Report obsahuje povinné sekce: Souhrn, Metriky, Detaily, Warnings

### Invarianty
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován
- [ ] Protocol log obsahuje START i END záznam
- [ ] Žádný zdrojový kód nebyl modifikován (process je read-only analytický skill)

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Chybí config.md/state.md | STOP + jasná zpráva |
| Preconditions | CODE_ROOT neexistuje | STOP + zpráva |
| Preconditions | Žádné Python soubory | STOP + zpráva |
| FAST PATH | fabric.py selže | WARN + pokračuj manuálně |
| P1 (Extract) | Žádné routes nalezeny | WARN + pokračuj (systém může mít jen CLI) |
| P2 (Trace) | Call chain nelze sledovat (obfuskovaný kód) | Zapiš co jde, zbytek = WARN + intake item |
| P3 (Cross-map) | Příliš mnoho orphanů (>50% procesů) | Report WARN + intake item (systém potřebuje refactoring) |
| P4 (Validate) | Testy FAIL | Report WARN (ne FAIL — process mapping pokračuje) |
| P4 (Validate) | Test command TBD | SKIP validace, zaloguj WARN |
| P5 (Update) | YAML write error | STOP + protocol error log + intake item |
| Quality Gate | Duplicate process IDs | Deduplikuj + report WARN |
| Self-check | Missing sections in process-map | Report WARN + intake item |

**Obecné pravidlo:** Skill je **fail-open** vůči VOLITELNÝM vstupům (vision, specs, previous map)
a **fail-fast** vůči POVINNÝM vstupům (config, state, CODE_ROOT).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: orientation
step: process

# Oprávnění
may_modify_state: false
may_modify_backlog: false
may_modify_code: false
may_create_intake: true

# Pořadí v pipeline (pro fabric-loop)
depends_on: [fabric-architect]
feeds_into: [fabric-gap]

# Konzumenti process mapy (cross-reference)
consumed_by: [fabric-gap, fabric-analyze, fabric-review, fabric-check, fabric-implement, fabric-architect]
```

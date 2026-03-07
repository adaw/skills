---
name: fabric-process
description: "Map external processes (user-system interactions) and internal process chains (causal code dependencies) with cross-mapping. Produces live process map consumed by downstream skills for risk assessment and change impact analysis."
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

## Downstream Contract

**Kdo konzumuje výstupy fabric-process a jaká pole čte:** Viz `references/validation.md` — "Downstream Consumers" sekce.

Klíčově:
- **fabric-gap** → External Processes table (ID, Actor, Entry Point, Status)
- **fabric-analyze** → contract_modules[] field (affected processes context)
- **fabric-review** → contract_modules[] (test evidence requirements)
- **fabric-check** → updated timestamp (freshness validation)

**Contract fields in process-map.md:**
```yaml
schema: fabric.process-map.v1
version: "1.0"
created: YYYY-MM-DD
updated: YYYY-MM-DD
validation_status: VALID | STALE
external_count: int
internal_count: int
external_processes: [{id, actor, trigger, entry_point, output, status}]
internal_processes: [{id, trigger, call_chain, dependencies, side_effects}]
orphans: [{type, name, classification, action}]
```

---

## §2 — Protokol (povinné — NEKRÁTIT)

Na začátku a na konci tohoto skillu zapiš události do protokolu.

Detail bash commands: Viz `references/preconditions.md` — "Protocol Logging" sekce.

**Summary:**
- **START:** Log skill start with event=start
- **END (OK/WARN/ERROR):** Log completion with status + report path
- **ERROR:** Log critical errors immediately with brief reason

---

## §3 — Preconditions (temporální kauzalita)

Před spuštěním ověř tyto podmínky. Detailní checks a interpretace: Viz `references/preconditions.md`.

**Klíčové checks:**
- `{WORK_ROOT}/config.md` existuje (cesty, schémata)
- `{WORK_ROOT}/state.md` existuje (aktuální fáze)
- `{CODE_ROOT}` existuje a obsahuje Python soubory
- `{WORK_ROOT}/fabric/processes/` adresář vytvoř pokud chybí
- `vision.md` volitelně (WARN pokud chybí)

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
- `{SPECS_ROOT}/*.md` — specifikace
- `{TEST_ROOT}/` — testovací soubory (pro validaci pokrytí)
- `{WORK_ROOT}/intake/` — pending items (korekční mechanismus)

Viz `references/preconditions.md` pro detaily.

---

## §5 — Výstupy

### Primární (vždy)
- `{WORK_ROOT}/fabric/processes/process-map.md` (schema: `fabric.process-map.v1`) — Master dokument
- Report: `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)

### Vedlejší (podmínečně)
- `{WORK_ROOT}/fabric/processes/{process-id}.md` (schema: `fabric.process.v1`) — Individuální procesy
- Intake items: `{WORK_ROOT}/intake/process-{slug}.md` — pro orphany/gapy

Detaily v `references/preconditions.md` — "Output Artifacts" sekce.

---

## §6 — Deterministic FAST PATH

Než začneš analyzovat, proveď deterministické kroky:

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index

# 3-7. Automated scans: Route inventory, Service inventory, CLI commands, Models, Previous map delta
# Viz references/workflow.md — "FAST PATH Detection" sekce
```

Pokud `fabric.py` selže → WARN + pokračuj manuálně.

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

**Detailní bash scripts, state validation, path guards:** Viz `references/workflow.md`.

Skill se skládá z 5 fází:

### **P1: Extract External Processes**

**Co:** Identifikuj VŠECHNY vnější interakce — kdo systém používá, přes jaké rozhraní, s jakým výsledkem.

**Jak (shrnutí):**
1. **API Routes** — Najdi `@router.get|post|put|delete|patch` v `{CODE_ROOT}/api/routes/*.py`
2. **CLI Commands** — Najdi `@click.command`, `@app.command`, argparse entry points
3. **Event Handlers** — Background tasks, queue consumers, webhooks
4. **System-to-System** — HTTP klienti, database connections, message queues

Pro každý nalezený proces vyplň tabulku s: Process ID, Kategorie, Actor(s), Trigger, Entry Point, Response, Status.

**Konvence Process ID:** `ext-{doména}-{akce}` (např. `ext-capture-event`)

**Validace:** Počet external procesů MUSÍ odpovídat počtu nalezených routes + CLI commands (s 5% tolerancí).

Detaily + LLMem příklady: Viz `references/examples.md` — "P1: Complete LLMem External Processes Example" sekce.

Anti-patterns + bash detekce: Viz `references/workflow.md` — "P1: External Process Detection" sekce.

---

### **P2: Trace Internal Process Chains**

**Co:** Pro KAŽDÝ vnější proces (z P1) sleduj vnitřní call chain — co se děje od entry pointu po response.

**Jak (shrnutí):**
1. Otevři handler funkci z P1 entry pointu
2. Sleduj volání: Handler → Service method → Helper/Utility → Storage → Return
3. Pro každý krok zapiš soubor, funkci, vstup, výstup, side effects
4. Identifikuj kauzální závislosti (změny modelu → změna scoring → změna storage → změna recall)
5. Zapiš contract_modules — které soubory MUSÍ zůstat konzistentní

**Significant Process Threshold (WQ5):**
A process is SIGNIFICANT (requires detailed trace) if:
- API route or CLI command, OR
- Has ≥3 downstream function calls, OR
- Modifies persisted state, OR
- Critical to agent execution

Detaily + call chain ASCII diagramy: Viz `references/examples.md` — "P2: Internal Process Call Chain Example".

Individuální process file template (schéma v1.2): Viz `references/examples.md` — "P2: Individual Process File Template".

Orphan classification algorithm (WQ5): Viz `references/workflow.md` — "P2: Internal Chain Tracing".

---

### **P3: Cross-Mapping & Orphan Detection**

**Co:** Propoj vnější procesy s vnitřními řetězci. Najdi nesoulady — orphany.

**Jak (shrnutí):**
1. Pro každý vnější proces zapiš, které vnitřní řetězce spouští
2. Orphan detection — vnější bez vnitřního → ORPHAN EXTERNAL (intake item)
3. Orphan detection — vnitřní bez vnějšího → klasifikuj: DEAD_CODE / INTERNAL_ONLY / UNDOCUMENTED
4. Vision cross-reference (pokud existuje)

**Kategorie orphanů:**
- **DEAD_CODE:** Nikdo volá → Chore (remove/document)
- **INTERNAL_ONLY:** Jen testy → Correct, no action
- **UNDOCUMENTED:** Volá se, ale není v process-map → Task (extend map)
- **DOCUMENTED:** V procesu → no action

Detaily + deterministic classification bash: Viz `references/workflow.md` — "P2: Internal Chain Tracing" sekce.

Cross-mapping šablona: Viz `references/examples.md` — "P3: Cross-Layer Mapping Template".

---

### **P4: Validate Against Reality**

**Co:** Ověř, že dokumentované procesy odpovídají reálnému chování kódu. Ne statická analýza — skutečné spuštění.

**Jak (shrnutí):**
1. Spusť existující testy (pokud `COMMANDS.test` není TBD)
2. Ověř test pokrytí per proces (pro contract_modules)
3. Stub detection v contract modules (pass, NotImplementedError, TODO, FIXME)
4. Contract governance check (ADR refs stále valid)

Anti-patterns: Nespouštěj testy pokud TBD; neblokuj na test FAIL (report WARN); nepředstírej pokrytí.

Detaily + bash: Viz `references/workflow.md` — "P4: Runtime Validation" sekce.

---

### **P5: Update Process Map + Generate Report**

**Co:** Zapiš/aktualizuj master `process-map.md`, vytvoř individuální process soubory, generuj execution report.

**Jak (shrnutí):**
1. Zapiš/aktualizuj `process-map.md` — 4 sekce: External, Internal, Cross-Layer, Orphans
2. Vytvoř individuální process soubory (`{id}.md`) — 1 file per proces
3. Vytvoř intake items pro orphany/gapy
4. Generuj report s metrikami a verdictem

Process map šablona: Viz `references/examples.md` — "P5: Process Map Master Document Template".

Report šablona: Viz `references/validation.md` — "Report Schema" sekce.

---

## §8 — Quality Gates

### Gate 1: Process Map Schema Validation
- PASS: Schema `fabric.process-map.v1` přítomné a parsovatelné
- FAIL: Vytvoř intake item + report FAIL

### Gate 2: Route Coverage (WQ10 — BLOCKING if <80%)
- PASS: ≥80% routes dokumentovány
- FAIL: <80% coverage → intake items for missing routes + block report

### Gate 3: No Duplicate Process IDs
- PASS: Žádné duplikáty
- FAIL: Deduplikuj + report FAIL

Detaily + bash scripts: Viz `references/validation.md` — "Quality Gate" sekce.

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/process-{YYYY-MM-DD}.md` s schématem `fabric.report.v1`.

**Klíčové sekce:**
- Souhrn (1–3 věty)
- Metriky (tabulka: external count, internal count, orphans, test validation, contract modules, stubs)
- Detaily (external processes, internal chains, orphan analysis, causal dependencies)
- Delta (vs. předchozí mapa)
- Intake items vytvořené
- Warnings

Status logic (WQ10): FAIL pokud route coverage <80% OR mnoho orphanů; WARN pokud testy FAIL; OK ostatně.

Detaily + full template: Viz `references/validation.md` — "Report Schema" sekce.

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

### Invariants
- [ ] Žádný soubor mimo `{WORK_ROOT}/` nebyl modifikován
- [ ] Protocol log obsahuje START i END záznam
- [ ] Žádný zdrojový kód nebyl modifikován (process je read-only analytický skill)

Viz `references/validation.md` — "Self-Check Checklist" sekce.

---

## §11 — Failure Handling

**Obecné pravidlo:** Skill je **fail-open** vůči VOLITELNÝM vstupům (vision, specs, previous map)
a **fail-fast** vůči POVINNÝM vstupům (config, state, CODE_ROOT).

Detailní failure matrix (fáze, chyba, akce): Viz `references/validation.md` — "Failure Handling Matrix" sekce.

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

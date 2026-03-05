---
name: fabric-design
description: "Převést READY/DESIGN backlog item na implementační specifikaci: datový model, komponenty, API, integrace, konfigurace, testy, závislosti, rizika a alternativy. Most mezi ideou a implementací — bez něj LLM implementuje z vágního popisu."
---
<!-- built from: builder-template -->

# DESIGN — Implementační specifikace (deep design)

---

## §1 — Účel

Převést backlog item (Task/Bug/Epic) na **detailní implementační specifikaci**, ze které může
`fabric-implement` pracovat deterministicky a bez dalších otázek.

Design produkuje: datový model (Pydantic), API signatury, integrační flow, konfiguraci,
testovací strategii s konkrétními test cases, závislosti, rizika a alternativní přístupy.

**Bez tohoto skillu:** LLM implementuje z 1–2 vět backlog popisu → nekonzistentní architektura,
chybějící edge cases, žádné alternativy, ad-hoc rozhodnutí. Každý rework cyklus je dražší
než upfront design.

**Rozdíl od fabric-analyze:**
- `fabric-analyze` = taktická dekompozice (Sprint Targets → Task Queue)
- `fabric-design` = hluboká specifikace (1 backlog item → implementační plán)
- Analyze je ŠIROKÝ (celý sprint), design je HLUBOKÝ (jeden item)

---

## §2 — Protokol (povinné — NEKRÁTIT)

**START:**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "design" \
  --event start
```

**END (OK/WARN/ERROR):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "design" \
  --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md"
```

**ERROR (pokud STOP/CRITICAL):**
```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" \
  --skill "design" \
  --event error \
  --status ERROR \
  --message "{krátký důvod — max 1 věta}"
```

---

## §3 — Preconditions (temporální kauzalita)

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

# --- Precondition 3: Backlog item existuje ---
TASK_ID="${1:?STOP: task ID required — usage: fabric-design <TASK_ID>}"
SAFE_ID=$(echo "${TASK_ID}" | sed 's/[^a-zA-Z0-9_-]//g')
if [ "$SAFE_ID" != "${TASK_ID}" ]; then
  echo "WARN: task ID sanitized: '${TASK_ID}' → '$SAFE_ID'"
  TASK_ID="$SAFE_ID"
fi

if [ ! -f "{WORK_ROOT}/backlog/${TASK_ID}.md" ]; then
  echo "STOP: backlog file not found: backlog/${TASK_ID}.md — run fabric-intake first"
  exit 1
fi

# --- Precondition 4: Task status je DESIGN nebo READY ---
ITEM_STATUS=$(grep 'status:' "{WORK_ROOT}/backlog/${TASK_ID}.md" | head -1 | awk '{print $2}')
case "$ITEM_STATUS" in
  DESIGN|READY|IDEA) echo "Status: $ITEM_STATUS — OK for design" ;;
  IN_PROGRESS|IN_REVIEW|DONE)
    echo "STOP: task ${TASK_ID} has status ${ITEM_STATUS} — design phase already passed"
    exit 1
    ;;
  *) echo "WARN: unknown status '$ITEM_STATUS', proceeding" ;;
esac

# --- Precondition 5: Zdrojový kód existuje ---
if [ ! -d "{CODE_ROOT}" ]; then
  echo "WARN: {CODE_ROOT}/ not found — design will be theoretical (no code to inspect)"
fi

# --- Precondition 6: Governance artefakty ---
if [ ! -f "{WORK_ROOT}/decisions/INDEX.md" ]; then
  echo "WARN: decisions/INDEX.md not found — governance check will be skipped"
fi
```

**Dependency chain:**
```
fabric-init → fabric-intake → fabric-prio → [fabric-design] → fabric-analyze → fabric-implement
```

---

## §4 — Vstupy

### Povinné
- `{WORK_ROOT}/config.md` (COMMANDS, cesty, taxonomie)
- `{WORK_ROOT}/state.md`
- `{WORK_ROOT}/backlog/${TASK_ID}.md` (backlog item k rozpracování)
- `{CODE_ROOT}/` (zdrojový kód — pro pochopení existující architektury)
- `{TEST_ROOT}/` (existující testy — pro pochopení testing patterns)

### Volitelné (obohacují výstup)
- `{WORK_ROOT}/decisions/INDEX.md` + `{WORK_ROOT}/decisions/*.md` (governance constraints)
- `{WORK_ROOT}/specs/INDEX.md` + `{WORK_ROOT}/specs/*.md` (technické specifikace)
- `{ANALYSES_ROOT}/{TASK_ID}-analysis.md` (pokud analyze už proběhla — doplň, nepřepisuj)
- `{DOCS_ROOT}/` (dokumentace — API docs, README, architecture notes)
- `fabric/visions/` (vision alignment)

---

## §5 — Výstupy

### Primární (vždy)
- Design spec: `{ANALYSES_ROOT}/{TASK_ID}-design.md` (schema: `fabric.report.v1`, kind: `design`)
- Report: `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md` (schema: `fabric.report.v1`)
- Aktualizovaný backlog item: `status: READY` (pokud design kompletní)

### Vedlejší (podmínečně)
- Intake items: `{WORK_ROOT}/intake/design-{slug}.md` (pro blocker/clarification)
- ADR draft: `{WORK_ROOT}/decisions/ADR-NNN-draft.md` (pokud design vyžaduje nový architektonický rozhodnutí)
- Spec draft: `{WORK_ROOT}/specs/SPEC-NNN-draft.md` (pokud design definuje nový kontrakt)

---

## §6 — Deterministic FAST PATH

```bash
# 1. Backlog index sync
python skills/fabric-init/tools/fabric.py backlog-index 2>/dev/null || true

# 2. Governance index sync
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null || true

# 3. Zjisti project language + framework
PROJECT_LANG=$(grep 'Jazyk' "{WORK_ROOT}/config.md" | head -1 | sed 's/.*|\s*//' | tr -d ' |')
echo "Project language: ${PROJECT_LANG:-unknown}"
```

---

## §7 — Postup (JÁDRO SKILLU — zde žije kvalita práce)

### 7.1) D1: Pochop kontext (VERIFY-FIRST)

**Co:** Přečti backlog item, existující kód a governance — pochop CO se má udělat a PROČ.

**Jak (detailní instrukce):**
1. Přečti `{WORK_ROOT}/backlog/${TASK_ID}.md` — extrahuj:
   - Title, description, acceptance criteria (AC)
   - Effort estimate, dependencies, linked vision goal
2. Přečti relevantní zdrojový kód v `{CODE_ROOT}/`:
   - Identifikuj dotčené moduly/soubory (z AC nebo popisu)
   - Pochop existující architekturu: jaké třídy, jaké patterns, jaké konvence
   - Zjisti co UŽ existuje (abys nenavrhl duplicitu)
3. Přečti `{TEST_ROOT}/` — pochop testovací patterns:
   - Jaké fixtures se používají? Jaký test framework? Jaké konvence?
4. Governance cross-check:
   ```bash
   # Najdi relevantní ADR/SPEC
   grep -rl "${TASK_ID}\|$(grep 'title:' {WORK_ROOT}/backlog/${TASK_ID}.md | head -1 | sed 's/title:\s*//' | cut -d' ' -f1-3)" \
     "{WORK_ROOT}/decisions/" "{WORK_ROOT}/specs/" 2>/dev/null | head -10
   ```
   - Zapiš nalezené constraints do design spec

**Minimum:**
- Přečteny: backlog item + ≥3 relevantní zdrojové soubory + test patterns
- Identifikovány: dotčené moduly, existující patterns, governance constraints
- Pochopeno: CO se mění, PROČ, a KDE v kódu

**Anti-patterns (zakázáno):**
- Designovat bez přečtení existujícího kódu — výsledek bude nekonzistentní
- Ignorovat governance constraints — porušení ADR/spec = rework
- Předpokládat „to tam asi je" — OVĚŘ existenci ve zdrojáku

### 7.2) D2: Datový model

**Co:** Navrhni nové/upravené datové struktury (Pydantic modely, dataclasses, schemas).

**Jak (detailní instrukce):**
1. Identifikuj jaké datové entity design vyžaduje
2. Pro KAŽDOU entitu napiš:
   - Kompletní definici (fields, types, validators, defaults)
   - Relationship k existujícím entitám
   - Migration path (pokud upravuješ existující model)
3. Používej SKUTEČNÉ typy projektu (ne abstraktní)

**Minimum:**
- Každá nová/změněná entita má kompletní definici s typy
- Relationship diagram (textový) pokud > 2 entity
- Migration notes pokud se mění existující model

**Anti-patterns:**
- `field: Any` — specifikuj skutečný typ
- Model bez validátorů pro user-facing data
- Nová entita bez relationship k existujícím

**Šablona výstupu:**
```python
# Nový model
class {ModelName}(BaseModel):
    """Popis účelu modelu."""
    field_a: str                          # popis
    field_b: int = 0                      # popis s defaultem
    field_c: Optional[list[str]] = None   # volitelné pole

    @validator("field_a")
    def validate_field_a(cls, v):
        """Validační pravidlo."""
        if not v.strip():
            raise ValueError("field_a cannot be empty")
        return v

# Změna existujícího modelu
# Soubor: {CODE_ROOT}/{path}.py, třída: {ClassName}
# Přidat: field_new: type = default  # důvod přidání
# Změnit: field_existing: old_type → new_type  # důvod změny
```

### 7.3) D3: Komponenty a API

**Co:** Navrhni nové/upravené třídy, metody, endpointy.

**Jak (detailní instrukce):**
1. Pro KAŽDOU komponentu (třída, modul, service):
   - Soubor kde bude žít (existující nebo nový)
   - Klíčové metody: signatura + popis + return type
   - Error handling strategie
2. Pro KAŽDÝ endpoint (pokud relevantní):
   - HTTP method + path
   - Request/Response schema (odkaz na D2 modely)
   - Error responses (4xx, 5xx)
3. Pseudokód pro netriviální logiku:
   - Algoritmy, rozhodovací stromy, datové transformace
   - **PSEUDOKÓD JE POVINNÝ** pro jakoukoli logiku delší než 5 řádků

**Minimum:**
- Každá komponenta: soubor + třída + klíčové metody se signaturami
- Každý endpoint: method + path + request/response + errors
- Pseudokód pro netriviální logiku

**Anti-patterns:**
- `def process(data): ...` bez specifikace CO process dělá
- Endpoint bez error responses
- Logika popsaná jen slovně bez pseudokódu — LLM to neimplementuje správně

**Šablona výstupu:**
```python
# Soubor: {CODE_ROOT}/{path}.py

class {ClassName}:
    """Popis účelu."""

    def method_a(self, param1: Type1, param2: Type2) -> ReturnType:
        """Popis co metoda dělá.

        Args:
            param1: popis
            param2: popis

        Returns:
            popis návratové hodnoty

        Raises:
            ValueError: když param1 je neplatný
        """
        # Pseudokód:
        # 1. Validuj vstupy
        # 2. Načti existující data z {source}
        # 3. Transformuj: {popis transformace}
        # 4. Ulož výsledek do {target}
        # 5. Return {co}
        ...

# Endpoint (pokud relevantní):
# POST /api/v1/{resource}
# Request: {ModelName} (viz D2)
# Response 201: {ResponseModel}
# Response 400: {"detail": "validation error"}
# Response 404: {"detail": "not found"}
```

### 7.4) D4: Integrace a flow

**Co:** Popiš jak se nový kód napojí na existující systém.

**Jak (detailní instrukce):**
1. Identifikuj integrační body (jaké existující moduly/služby se volají)
2. Nakresli datový flow (ASCII diagram):
   - Odkud data přicházejí → co se s nimi děje → kam jdou
3. Identifikuj side effects (co se změní jinde v systému)

**Minimum:**
- Seznam integračních bodů (min. 1)
- ASCII flow diagram
- Side effects list

**Anti-patterns:**
- „Napojí se na existující systém" bez specifikace KAM a JAK
- Flow bez error paths
- Ignorování side effects (cache invalidation, event propagation)

**Šablona výstupu:**
```
Integrační flow:

  [{Input}] → [{New Component}] → [{Existing Component}]
       ↓              ↓                    ↓
   validate      transform           persist
       ↓              ↓                    ↓
   [400 error]   [side effect:       [success 201]
                  invalidate cache]

Integrační body:
1. {ExistingModule}.{method}() — volán z: {kde} — účel: {co}
2. {ExistingService}.{method}() — volán z: {kde} — účel: {co}

Side effects:
- {popis side effectu} — kdy nastane, jak ošetřit
```

### 7.5) D5: Konfigurace

**Co:** Specifikuj nové config klíče, env vars, feature flags.

**Jak (detailní instrukce):**
1. Identifikuj co potřebuje být konfigurovatelné (ne hardcoded)
2. Pro každý config klíč: název, typ, default, validace, popis
3. Ověř proti existující konfiguraci (nevytvářej duplicity)

**Minimum:**
- Seznam nových config klíčů (nebo „žádné nové")
- Každý klíč: název + typ + default + popis

**Šablona:**
```yaml
# Nové config klíče:
new_section:
  key_name: "default_value"    # Typ: str | Popis | Validace: non-empty
  timeout_ms: 5000             # Typ: int | Popis | Validace: 100-60000
```

### 7.6) D6: Testovací strategie

**Co:** Definuj KONKRÉTNÍ test cases — ne vágní „napiš testy".

**Jak (detailní instrukce):**
1. Pro KAŽDOU novou komponentu navrhni min. 3 testy:
   - **Happy path** — hlavní funkce funguje s validním vstupem
   - **Edge case** — hraniční vstupy (prázdný, null, maximum, unicode)
   - **Error handling** — neplatný vstup, síťová chyba, timeout
2. Pro integrační testy: definuj fixtures a setup
3. Odhadni coverage dopad

**Minimum:**
- Min. 3 test cases per nová komponenta (happy/edge/error)
- Každý test case: název + co testuje + vstup + očekávaný výstup
- Coverage odhad (kolik % nových řádků bude pokryto)

**Anti-patterns:**
- `test_it_works()` — co přesně testuje?
- Jeden test pro celý feature — nedostatečné
- Testy bez edge cases — happy path nestačí
- „Napsat testy" bez specifikace JAKÉ — LLM napíše minimum

**Šablona výstupu:**
```python
# Test cases pro {ComponentName}:

# 1. test_{component}_happy_path
#    Vstup: {konkrétní validní vstup}
#    Očekávaný výstup: {konkrétní výstup}
#    Ověřuje: hlavní funkce funguje

# 2. test_{component}_empty_input
#    Vstup: None / "" / []
#    Očekávaný výstup: ValueError / default hodnota
#    Ověřuje: edge case handling

# 3. test_{component}_error_handling
#    Vstup: {neplatný vstup}
#    Očekávaný výstup: {specifická výjimka}
#    Ověřuje: error path

# 4. test_{component}_integration
#    Setup: {fixture popis}
#    Vstup: {reálný scénář}
#    Ověřuje: integrace s {dependent component}

# Coverage odhad: ~80% nových řádků
```

### 7.7) D7: Alternativy a rizika

**Co:** Popiš ALESPOŇ 2 alternativní přístupy a zdůvodni volbu. Identifikuj rizika.

**Jak (detailní instrukce):**
1. Pro každou netriviální designovou volbu:
   - Minimálně 2 alternativy (současný návrh + alespoň 1 jiný)
   - Pro/con každé alternativy
   - Zdůvodnění volby
2. Identifikuj rizika:
   - Co může selhat?
   - Jak velký dopad?
   - Jaká mitigace?

**Minimum:**
- ≥2 alternativy pro hlavní designovou volbu
- Pro/con tabulka
- ≥2 identifikovaná rizika s mitigací

**Anti-patterns:**
- Žádné alternativy — „je to jasné" → NENÍ, vždy existují alternativy
- Rizika bez mitigace — identifikovat nestačí
- „Nízké riziko" bez zdůvodnění PROČ je nízké

**Šablona výstupu:**
```md
### Alternativy

| # | Přístup | Pro | Con | Doporučení |
|---|---------|-----|-----|------------|
| A | {současný návrh} | {výhody} | {nevýhody} | **ZVOLEN** — důvod |
| B | {alternativa 1} | {výhody} | {nevýhody} | Odmítnuto — důvod |
| C | {alternativa 2} | {výhody} | {nevýhody} | Odmítnuto — důvod |

### Rizika

| # | Riziko | Dopad | Pravděpodobnost | Mitigace |
|---|--------|-------|-----------------|----------|
| 1 | {co může selhat} | {HIGH/MED/LOW} | {HIGH/MED/LOW} | {jak se tomu bránit} |
| 2 | {co může selhat} | {HIGH/MED/LOW} | {HIGH/MED/LOW} | {jak se tomu bránit} |
```

### 7.8) D8: Závislosti a pořadí

**Co:** Definuj co musí existovat PŘED implementací a v jakém pořadí implementovat.

**Jak:**
1. External dependencies (nové knihovny, services)
2. Internal dependencies (jiné tasks, existující kód)
3. Doporučené pořadí implementace (pokud design pokrývá víc souborů)

**Minimum:**
- Seznam závislostí (external + internal)
- Doporučené pořadí implementace

**Šablona:**
```md
### Závislosti
- External: {knihovny — buď konkrétní verze}
- Internal: {task_id} musí být DONE před tímto

### Pořadí implementace
1. {soubor/modul} — datový model (základ)
2. {soubor/modul} — core logika (závisí na 1)
3. {soubor/modul} — API/integrace (závisí na 1+2)
4. {soubor/modul} — testy (závisí na 1+2+3)
```

---

## §8 — Quality Gates

### Gate 1: Kompletnost design spec
- PASS: Všech 8 sekcí (D1–D8) vyplněno
- FAIL: Chybí sekce → doplň

### Gate 2: Pseudokód přítomen
- PASS: Každá netriviální logika má pseudokód
- FAIL: Logika popsaná jen slovně → přidej pseudokód

### Gate 3: Test cases konkrétní
- PASS: Min. 3 test cases per komponenta s vstupy a výstupy
- FAIL: Vágní „napiš testy" → specifikuj konkrétní cases

### Gate 4: Alternativy přítomny
- PASS: ≥2 alternativy pro hlavní volbu + pro/con
- FAIL: Žádné alternativy → přidej

### Gate 5: Governance alignment
- PASS: Žádný konflikt s accepted ADR / active spec
- FAIL: Konflikt → intake item + DESIGN status (ne READY)

---

## §9 — Report

Vytvoř `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: design
run_id: "{run_id}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {PASS|WARN|FAIL}
task_id: "{TASK_ID}"
design_spec: "{ANALYSES_ROOT}/{TASK_ID}-design.md"
---

# Design Report — {TASK_ID}

## Souhrn
{1–3 věty: co bylo designováno a s jakým výsledkem}

## Design spec
Path: `{ANALYSES_ROOT}/{TASK_ID}-design.md`
Kompletnost: {N}/8 sekcí (D1–D8)

## Governance
- ADR constraints: {seznam nebo "žádné"}
- SPEC constraints: {seznam nebo "žádné"}
- Konflikty: {seznam nebo "žádné"}

## Rizika
- {top 2 rizika ze sekce D7}

## Doporučený další krok
{fabric-analyze (pokud design je součást sprintu) nebo fabric-implement (pokud task je READY)}

## Intake items vytvořené
{Seznam nebo "žádné"}

## Warnings
{Seznam nebo "žádné"}
```

---

## §10 — Self-check (povinný — NEKRÁTIT)

### Existence checks
- [ ] Design spec existuje: `{ANALYSES_ROOT}/{TASK_ID}-design.md`
- [ ] Report existuje: `{WORK_ROOT}/reports/design-{TASK_ID}-{YYYY-MM-DD}.md`
- [ ] Backlog item aktualizován (status: READY pokud design kompletní)

### Quality checks
- [ ] Design spec má VŠECH 8 sekcí (D1–D8) — žádná vynechaná
- [ ] Datový model (D2) má kompletní definice s typy a validátory
- [ ] Pseudokód přítomen pro KAŽDOU netriviální logiku (D3)
- [ ] ≥3 test cases per nová komponenta (D6) — happy/edge/error
- [ ] ≥2 alternativy s pro/con tabulkou (D7)
- [ ] ≥2 rizika s mitigací (D7)
- [ ] ASCII flow diagram přítomen (D4)
- [ ] Governance constraints explicitně uvedeny (D1) — i pokud „žádné"

### Invarianty
- [ ] Design spec neobsahuje implementační kód — jen specifikaci
- [ ] Žádný soubor v `{CODE_ROOT}/` nebyl modifikován
- [ ] Protocol log obsahuje START i END záznam
- [ ] Backlog item nebyl smazán nebo přesunut

---

## §11 — Failure Handling

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Backlog item chybí | STOP + „run fabric-intake first" |
| Preconditions | Status IN_PROGRESS/DONE | STOP + „design phase already passed" |
| D1 Kontext | Zdrojový kód nenalezen | WARN + design bude teoretický (zapiš do reportu) |
| D1 Kontext | Governance index chybí | WARN + governance check skipped |
| D2 Datový model | Nejasné typy | Vytvoř intake item `design-clarification-{id}.md`, ponech DESIGN status |
| D3 Komponenty | Příliš komplexní pro 1 task | Navrhni rozpad na sub-tasks → intake item |
| D5 Config | Konflikt s existující config | Zapiš do design spec jako riziko |
| D7 Alternativy | Obě alternativy mají kritické nevýhody | Zapiš jako blocker → intake item, ponech DESIGN |
| Gate 5 | Governance konflikt | Intake item + ADR draft + DESIGN status |

**Obecné pravidlo:** Design je fail-open vůči VOLITELNÝM vstupům (chybí governance → pokračuj s WARNING)
a fail-fast vůči POVINNÝM (chybí backlog item → STOP).

---

## §12 — Metadata (pro fabric-loop orchestraci)

```yaml
# Zařazení v lifecycle
phase: planning
step: design

# Oprávnění
may_modify_state: false        # design nesmí měnit phase/step
may_modify_backlog: true       # aktualizuje status backlog itemu (DESIGN → READY)
may_modify_code: false         # design NIKDY nemodifikuje kód — jen specifikuje
may_create_intake: true        # při blockers/clarifications

# Pořadí v pipeline
depends_on: [fabric-intake, fabric-prio]
feeds_into: [fabric-analyze, fabric-implement]
```

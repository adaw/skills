---
name: fabric-builder
description: "Create, fix, and migrate fabric skills. Three modes: build creates new skills from template, fix applies checker findings, migrate converts legacy skills. Always uses builder-template.md as foundation, never modifies itself based on its own output."
---

# FABRIC-BUILDER — Build, Fix & Migrate Skills

> **Tento skill TVOŘÍ a MODIFIKUJE.** Je to protějšek `fabric-checker`.
>
> Flow: **checker** → findings report → **builder fix** → **checker** → ověření
>
> Builder NIKDY nehodnotí a neskóruje — to dělá checker.
> Builder VŽDY staví z `assets/builder-template.md`.

---

## Módy

```
fabric-builder build <name>           # Vytvořit nový skill
fabric-builder fix                    # Opravit findings z posledního checker reportu
fabric-builder migrate <name>         # Konvertovat legacy skill na builder-template
```

---

## Společné zdroje (čti VŽDY jako první)

1. `skills/fabric-builder/assets/builder-template.md` — kanonická šablona (POVINNÉ)
2. `fabric/config.md` — cesty, kontrakty, enumy
3. `fabric/reports/checker-*.md` — poslední checker report (pro `fix` a `migrate`)
4. `dev/workflows/*.md` — historické workflow soubory (referenční kvalita, pokud existují)
5. `fabric/reports/work-quality-analysis-*.md` — analýza kvality (pokud existuje)

---

## Progressive Disclosure — pravidlo 500 řádků (POVINNÉ)

Agent Skills specifikace doporučuje **max ~500 řádků** v SKILL.md. Delší skills riskují LLM truncation — agent přečte SKILL.md celý při aktivaci, ale s příliš dlouhým souborem ztratí kontext na konci.

**Řešení: SKILL.md + referenční soubory.** SKILL.md obsahuje §1–§12 strukturu (orchestrační vrstva), detailní obsah žije v `references/` souborech, které agent čte on-demand přes Read tool.

### Pravidla

1. **SKILL.md ≤ 500 řádků** — orchestrace, kontrakty, preconditions, self-check
2. **Detailní obsah → `references/`** — postupy, příklady, triage pravidla, šablony
3. **§7 Postup** v SKILL.md obsahuje přehled kroků (CO dělat) + `> Detaily viz references/<file>.md`
4. **Referenční soubory** jsou self-contained — mají vlastní nadpisy, příklady, anti-patterns
5. **K10 Fix příklady** a **rozsáhlé bash bloky** patří do `references/`

### Struktura složky

```
skills/fabric-{NAME}/
├── SKILL.md                    # ≤ 500 řádků: §1–§12 orchestrace
└── references/
    ├── workflow.md             # §7 detaily: kroky, logika, anti-patterns
    ├── examples.md             # K10: konkrétní příklady s reálnými daty
    └── {domain-specific}.md    # triage rules, dimensions, templates...
```

### Jak odkazovat z SKILL.md

V §7 Postup (nebo jiné sekci kde je potřeba):
```markdown
### 3) Triage pravidla

> **Detailní triage pravidla:** Přečti `references/triage-rules.md` pomocí Read toolu.
> Obsahuje: dedup logiku, vision alignment, type/tier/status heuristiky, anti-patterns.

Stručný přehled kroků:
1. Parse intake YAML
2. Deduplikace (deterministická, slug-based)
3. Vision alignment (povinné pro T0/T1)
4. Urči Type → Tier → Status
5. Vygeneruj backlog ID
6. Vytvoř backlog item ze šablony
7. Přesuň intake do done/rejected
```

### Kdy splitovat

- **Nový skill (build):** Pokud §7 přesáhne ~200 řádků → split od začátku
- **Migrace (migrate):** Pokud výsledný SKILL.md > 500 řádků → povinně split
- **Fix:** Pokud fix způsobí překročení 500 → split

### Validator

`validate_fabric.py` varuje při >500 řádků. Builder MUSÍ toto respektovat.

---

# MÓD 1: BUILD — Vytvoření nového skillu

## Kdy použít

Když potřebuješ nový fabric skill (např. fabric-design, fabric-e2e, fabric-hotfix).

## Parametry

```
fabric-builder build <name>
fabric-builder build <name> ref=<workflow>    # s referenčním starým workflow
```

- `<name>` — název nového skillu (bez prefixu `fabric-`), např. `design`
- `ref=<workflow>` — volitelně: starý workflow z `dev/workflows/` jako referenční zdroj kvality

## Postup

### B1) Připrav kontext

```bash
# K6: Template existence guard (MUST exist before build)
TEMPLATE="skills/fabric-builder/assets/builder-template.md"
if [ ! -f "$TEMPLATE" ]; then
  echo "STOP: builder-template.md not found at $TEMPLATE"
  python skills/fabric-init/tools/protocol_log.py \
    --work-root "{WORK_ROOT}" --skill "builder" --event error \
    --status ERROR --message "builder-template.md missing"
  exit 1
fi
```

1. Přečti `assets/builder-template.md` — toto je tvůj plán stavby
2. Přečti `fabric/config.md` — cesty, kontrakty, taxonomie
3. Pokud `ref=<workflow>`: přečti `dev/workflows/<workflow>.md` — extrahuj z něj:
   - Pracovní instrukce (JAK dělat kvalitní práci)
   - Příklady, šablony, minima
   - Anti-patterns
   - **Toto je ZLATO — staré workflows měly excelentní pracovní instrukce**
4. Přečti `fabric/reports/checker-*.md` (poslední) — podívej se do Evolution Radar,
   jestli checker navrhoval tento skill a s jakými doporučeními

### B2) Vytvoř adresář

```bash
# K3: Validate name + create directory with error handling
if [ -z "${NAME}" ] || ! echo "${NAME}" | grep -qE '^[a-z][a-z0-9-]*$'; then
  echo "STOP: Invalid skill name '${NAME}' — must be lowercase alphanumeric+hyphens"
  python skills/fabric-init/tools/protocol_log.py \
    --work-root "{WORK_ROOT}" --skill "builder" --event error \
    --status ERROR --message "Invalid skill name: ${NAME}"
  exit 1
fi
mkdir -p "skills/fabric-${NAME}"
```

### B3) Frontmatter (POVINNÉ — Claude Code Agent Skills spec)

```yaml
---
name: fabric-{name}
description: "{1-2 věty: CO skill dělá + KDY ho použít}"
---
<!-- built from: builder-template -->
```

> **Detailní frontmatter spec:** Přečti `references/frontmatter-spec.md` — obsahuje tabulku všech podporovaných atributů, pravidla pro fabric skills a anti-patterns.

### B4) Vyplň šablonu sekci po sekci

Zkopíruj strukturu z `assets/builder-template.md` a vyplň:

**§1 Účel:** 2–3 věty. Proč skill existuje, co se stane když se přeskočí.

**§2 Protokol:** Copy-paste z template, nahraď jen `{SKILL_NAME_SHORT}`.

**§3 Preconditions:** Identifikuj dependency chain:
- Který skill MUSÍ běžet před tímto? Jaké artefakty vytváří?
- Napiš bash kód pro ověření existence každého prereq artefaktu.
- STOP zpráva MUSÍ říct: „run fabric-{X} first".

**§4 Vstupy:** Rozděl na POVINNÉ a VOLITELNÉ. Používej config.md proměnné.

**§5 Výstupy:** Definuj report path, schema, intake items.

**§6 FAST PATH:** Identifikuj deterministické kroky (fabric.py tooling).

**§7 Postup — NEJDŮLEŽITĚJŠÍ SEKCE:**
```
╔══════════════════════════════════════════════════════════════╗
║  TADY ŽIJE KVALITA PRÁCE.                                   ║
║                                                              ║
║  Pro KAŽDÝ krok musíš definovat:                            ║
║  1. CO udělat (1–2 věty)                                    ║
║  2. JAK to udělat kvalitně (detailní instrukce)             ║
║  3. MINIMUM akceptovatelného výstupu                         ║
║  4. ANTI-PATTERNS (co je zakázáno)                           ║
║  5. ŠABLONA nebo PŘÍKLAD výstupu                            ║
║                                                              ║
║  Pokud máš referenční workflow (ref=):                      ║
║  → PŘENESNI z něj všechny pracovní instrukce               ║
║  → Pseudokód, ASCII diagramy, test metodiky                ║
║  → Scoring formule, severity mappings                       ║
║  → Fix strategie per finding typ                            ║
║                                                              ║
║  BEZ TĚCHTO DETAILŮ LLM UDĚLÁ MINIMUM.                     ║
╚══════════════════════════════════════════════════════════════╝
```

**§8 Quality Gates:** Pokud skill modifikuje kód — definuj gates (lint, test, format).

**§9 Report:** Formát s frontmatter, povinné sekce.

**§10 Self-check:** Min. 3 testovatelné položky. Existence + quality + invarianty.

**§11 Failure Handling:** Tabulka per fáze.

**§12 Metadata:** phase, step, depends_on, feeds_into, may_modify_*. Viz `references/metadata.md`.

### B5) Size check + progressive disclosure split

```bash
LINES=$(wc -l < "skills/fabric-${NAME}/SKILL.md")
if [ "$LINES" -gt 500 ]; then
  echo "WARN: SKILL.md has $LINES lines (limit 500) — splitting required"
fi
```

Pokud SKILL.md > 500 řádků:
1. Vytvoř `skills/fabric-${NAME}/references/` adresář
2. Přesuň §7 detaily → `references/workflow.md`
3. Přesuň K10 příklady → `references/examples.md`
4. Přesuň rozsáhlé bash bloky / tabulky → příslušný `references/*.md`
5. V SKILL.md nahraď přesunutý obsah odkazem: `> Detaily viz references/<file>.md`
6. Ověř že SKILL.md ≤ 500 řádků

### B6) Self-check buildu (POVINNÉ)

- [ ] Nový skill existuje: `skills/fabric-{NAME}/SKILL.md`
- [ ] Frontmatter: `name` ≤ 64 znaků, lowercase+hyphens, = dirname; `description` ≤ 1024 znaků, non-empty, 3. osoba
- [ ] Frontmatter: žádné nepodporované atributy (`title`/`type`/`schema`/`version`/`tags`/`depends_on`/`feeds_into`)
- [ ] `<!-- built from: builder-template -->` tag je ZA `---`, ne uvnitř
- [ ] Má všech 12 sekcí (§1–§12) nebo explicitní komentář proč chybí
- [ ] **SKILL.md ≤ 500 řádků** (pokud více → references/ split proběhl)
- [ ] §7 je KONKRÉTNÍ — žádné vágní „analyzuj" nebo „napiš testy"
- [ ] §7 má příklady/šablony pro KAŽDÝ krok (přímo nebo v references/)
- [ ] §3 má bash kód pro preconditions
- [ ] §10 má ≥3 testovatelné položky
- [ ] §12 depends_on/feeds_into symetrie: pokud tento skill má `feeds_into: [X]`, ověř že X má `depends_on: [tento_skill]` a naopak
- [ ] K10: ≥1 inline příklad s LLMem daty (≥10 řádků)
- [ ] K10: ≥3 anti-patterns s bash detection (`grep`/`ls` příkazy)
- [ ] Pokud ref= byl použit: klíčové pracovní instrukce z workflow jsou přeneseny

### B7) Doporučení po buildu

```
Nový skill vytvořen: skills/fabric-{NAME}/SKILL.md

Další krok:
  Spusť `fabric-checker target={NAME}` pro ověření kvality.
```

---

## K10 — Concrete Example & Anti-patterns

### Example: Build new skill "fabric-deploy" from template

```
Command: fabric-builder build deploy

B1) Prepare context:
  - Čti: assets/builder-template.md (13 sections)
  - Čti: fabric/config.md (lifecycle, enums, cesty)
  - Čti: dev/workflows/deployment-workflow.md (starý workflow, referenční kvalita)
  - Extrahuj z workflow: pre-prod validation steps, rollback strategy, smoke tests

B2) Create directory:
  mkdir -p skills/fabric-deploy

B3) Frontmatter:
  ---
  name: fabric-deploy
  description: "Execute fabric-approved deployment to prod with pre-flight checks, cloud API integration, smoke test validation, and automatic rollback on failure. Single entrypoint for unattended deployments."
  ---
  <!-- built from: builder-template -->

B4) Fill template sections:
  §1 Účel: 2 věty (why deploy skill, why needed)
  §2 Protokol: Copy template, set skill="deploy"
  §3 Preconditions: 6 bash checks (approval status, env vars, cloud creds)
  §4 Vstupy: deployment-plan.md, approval list, rollback snapshot
  §5 Výstupy: deployment-report.md + rollback-snapshot.md
  §6 FAST PATH: fabric.py deploy-pre-flight + cloud API validate
  §7 Postup: 8 detailed steps (pre-flight, acquire lock, deploy wave, smoke test, lock release)
  §8 Quality Gates: 5 blocking checks (API connectivity, no stubs, test pass)
  §9 Report template: detailed frontmatter + timeline + evidence
  §10 Self-check: 6 testable items
  §11 Failure Handling: rollback scenarios table
  §12 Metadata: phase=closing, depends_on=[fabric-review]

B5) Size check:
  wc -l skills/fabric-deploy/SKILL.md = 387 lines (< 500, OK)

B6) Self-check build:
  ✓ frontmatter valid, name=fabric-deploy
  ✓ All 12 sections present
  ✓ §7 is concrete (8 detailed steps, not vague)
  ✓ §3 has bash precondition code
  ✓ §10 has 6 testable items
  ✓ SKILL.md ≤ 500 lines

B7) Output:
  skills/fabric-deploy/SKILL.md created (387 lines)
  Recommendation: Run `fabric-checker target=deploy` for quality audit
```

### Anti-patterns (FORBIDDEN detection & prevention)

```bash
# A1: Building skill without checking naming conflict
# DETECTION: New skill name matches existing skill
# FIX: Check for duplicates in skills/ directory before creating
if [ -d "skills/fabric-${NAME}" ]; then
  echo "STOP: skills/fabric-$NAME already exists — choose different name"
  exit 1
fi

# A2: Not copying from builder-template (non-canonical structure)
# DETECTION: Manually wrote SKILL.md structure instead of using template
# FIX: ALWAYS start from assets/builder-template.md as copy, then customize
TEMPLATE="skills/fabric-builder/assets/builder-template.md"
if [ ! -f "$TEMPLATE" ]; then
  echo "STOP: builder-template.md not found at $TEMPLATE"
  exit 1
fi

# A3: §7 Postup is vague (not concrete LLM instructions)
# DETECTION: Contains phrases like "analyze", "implement", "validate" without detail
# FIX: Require EVERY step to have: CO (1 sentence), JAK (detailed), MINIMUM (acceptance), ANTI-PATTERNS (3+)
if ! grep -q "Anti-pattern\|FORBIDDEN\|MUST NOT" "skills/fabric-${NAME}/SKILL.md"; then
  echo "WARN: §7 Postup missing anti-patterns — add ≥3 per step"
fi
```

---

# MÓD 2: FIX — Oprava findings z checker reportu

## Kdy použít

Po spuštění `fabric-checker`, když report obsahuje P0/P1 findings.

## Parametry

```
fabric-builder fix                    # oprav TOP findings z posledního reportu
fabric-builder fix target=implement   # oprav jen findings pro jeden skill
fabric-builder fix max=5              # max počet oprav (default: 10)
```

## Postup

### F1) Načti checker report

```bash
# Najdi nejnovější checker report
REPORT=$(ls -t "{WORK_ROOT}"/reports/checker-*.md 2>/dev/null | head -1)
if [ -z "$REPORT" ]; then
  echo "STOP: žádný checker report — spusť fabric-checker nejdřív"
  exit 1
fi
```

Přečti sekci `## Findings pro fabric-builder` — to je tvůj work order.

### F2) Safety guardrails

```
NIKDY neopravuj:
- fabric-builder     — sám sebe (nedotknutelný)
- fabric-checker     — nedotknutelný (opravy pouze manuálně)
- fabric-loop        — orchestrátor, opravy pouze manuálně
- fabric-init        — bootstrap, opravy pouze manuálně

PRO T3 LEGACY SKILLS:
- Opravuj POUZE K1–K9 (robustnost): quoting, error handling, preconditions, validace
- NEOPRAVUJ K10 (Work Quality) strukturálně — to je migrace, ne fix
- Tzn. přidej chybějící error handling, quotuj proměnné, přidej preconditions
- Ale NEPŘEPISUJ celou strukturu skillu

PRO T2 BUILDER-BORN SKILLS:
- Opravuj vše (K1–K10 + template compliance)
```

### F3) Fix loop

```
REPEAT (max {max} iterací):
  1. Vezmi TOP finding z checker reportu (nejvyšší priorita)
  2. Ověř že skill NENÍ v no-fix seznamu
  3. Přečti příslušný SKILL.md
  4. Přečti builder-template.md (pro referenci správného vzoru)
  5. Aplikuj opravu:
     - K4 Git Safety → quotuj proměnné (vzor B.7 z template)
     - K6 Preconditions → přidej bash kód (vzor B.3 z template)
     - K7 Validation → přidej numeric guard (vzor B.8 z template)
     - K3 Error Handling → přidej fallback (vzor C.2 z template)
     - K8 Protocol → přidej START/END log (vzor B.1 z template)
     - K10 Work Quality → doplň příklady, minima, anti-patterns
  6. Zapiš opravu do fix-logu
UNTIL:
  - Všechny P0/P1 findings opraveny
  - NEBO max iterací dosaženo
```

### F4) Fix log + K10 Inline Example (FIX mode)

```
Report: checker-2026-03-07.md Round 6, Finding: fabric-prio K2=7 (line 148)
BEFORE: MAX_PRIO_ITEMS=${MAX_PRIO_ITEMS:-500}
AFTER:  MAX_PRIO_ITEMS=${MAX_PRIO_ITEMS:-500}
        if ! echo "$MAX_PRIO_ITEMS" | grep -qE '^[0-9]+$'; then MAX_PRIO_ITEMS=500; fi
Verify: wc -l = 435 (≤500 ✓), validate_fabric.py PASS
Log: | 1 | fabric-prio | K2 | counter sans validation | grep guard added | L148 |
```

```md
## Fix Log
| # | Skill | Kategorie | Finding | Oprava | Řádek |
|---|-------|-----------|---------|--------|-------|
```

### F5) Self-check fixu

- [ ] Checker report existoval a byl přečten
- [ ] Žádný no-fix skill nebyl modifikován
- [ ] Fix log obsahuje všechny provedené opravy
- [ ] Každá oprava odpovídá vzoru z builder-template.md

### F6) Doporučení po fixu

```
Opraveno: {N} findings ({P0}: {X}, {P1}: {Y})

Další krok:
  Spusť `fabric-checker` pro ověření že opravy pomohly a nic nerozbily.
```

---

# MÓD 3: MIGRATE — Konverze legacy skillu na builder-template

**Kompletní postup migrace (M1–M7):** Viz `references/migrate-mode.md`

**Shrnutí:** Přečti legacy skill → mapuj na §1–§12 → doplň chybějící sekce → přidej builder-born tag → split na ≤500L → validuj.

---

## Protokol

```bash
python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "builder" --event start

# ... build / fix / migrate ...

python skills/fabric-init/tools/protocol_log.py \
  --work-root "{WORK_ROOT}" --skill "builder" --event end \
  --status {OK|WARN|ERROR} \
  --report "{WORK_ROOT}/reports/builder-{YYYY-MM-DD}.md"
```

---

## Failure Handling

**Detail:** Viz `references/failure-handling.md` pro tabulku failure modes, akce, a anti-patterns.

---

## Report

`{WORK_ROOT}/reports/builder-{YYYY-MM-DD}.md` — frontmatter: `schema: fabric.report.v1`, `kind: builder`, `mode`, `status`, `target`. Body: Mód, Target, Provedené akce.

## §12 — Metadata

```yaml
phase: meta
step: builder
depends_on: [fabric-checker]
feeds_into: [fabric-checker]
may_modify_state: false
may_modify_code: true
idempotent: false
fail_mode: fail-closed
```

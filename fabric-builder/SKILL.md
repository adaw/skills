---
name: fabric-builder
description: "Tvoří, opravuje a migruje fabric skills. Tři módy: `build <name>` vytvoří nový skill z template, `fix` opraví findings z checker reportu, `migrate <name>` konvertuje legacy skill na builder-template. Vždy používá assets/builder-template.md jako základ."
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
mkdir -p "skills/fabric-${NAME}"
```

### B3) Vyplň šablonu sekci po sekci

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

**§12 Metadata:** phase, step, depends_on, feeds_into, may_modify_*.

### B4) Přidej builder-born tag

Na řádek 4 (za frontmatter) přidej:
```md
<!-- built from: builder-template -->
```

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

### B6) Self-check buildu

- [ ] Nový skill existuje: `skills/fabric-{NAME}/SKILL.md`
- [ ] Má `<!-- built from: builder-template -->` tag
- [ ] Má všech 12 sekcí (§1–§12) nebo explicitní komentář proč chybí
- [ ] **SKILL.md ≤ 500 řádků** (pokud více → references/ split proběhl)
- [ ] §7 je KONKRÉTNÍ — žádné vágní „analyzuj" nebo „napiš testy"
- [ ] §7 má příklady/šablony pro KAŽDÝ krok (přímo nebo v references/)
- [ ] §3 má bash kód pro preconditions
- [ ] §10 má ≥3 testovatelné položky
- [ ] Pokud ref= byl použit: klíčové pracovní instrukce z workflow jsou přeneseny

### B6) Doporučení po buildu

```
Nový skill vytvořen: skills/fabric-{NAME}/SKILL.md

Další krok:
  Spusť `fabric-checker target={NAME}` pro ověření kvality.
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
REPORT=$(ls -t {WORK_ROOT}/reports/checker-*.md 2>/dev/null | head -1)
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

### F4) Fix log

Zapiš do reportu:

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

## Kdy použít

Když checker v „Legacy migration radar" doporučí migraci legacy skillu.

## Parametry

```
fabric-builder migrate <name>         # konvertuj legacy skill
```

## Pravidla migrace

- Max 2 migrace per sprint
- VŽDY zachovej VEŠKEROU stávající logiku — migrace je STRUKTURÁLNÍ, ne obsahová
- Cíl: stejný skill, ale organizovaný podle §1–§12

## Postup

### M1) Baseline

1. Přečti stávající `skills/fabric-{NAME}/SKILL.md` — to je tvůj zdroj
2. Přečti `assets/builder-template.md` — to je tvůj cíl
3. Přečti poslední checker report — jaké K1–K10 skóre má skill TEĎ

### M2) Mapování existující obsah → §1–§12

Pro každou sekci template:

| Template sekce | Kde hledat v legacy skillu |
|----------------|---------------------------|
| §1 Účel | Sekce „Účel" (obvykle existuje) |
| §2 Protokol | Sekce „Protokol (povinné)" (obvykle existuje) |
| §3 Preconditions | Bash kód na začátku, nebo sekce „Předpoklady" |
| §4 Vstupy | Sekce „Vstupy" (obvykle existuje) |
| §5 Výstupy | Sekce „Výstupy" (obvykle existuje) |
| §6 FAST PATH | Sekce „FAST PATH" (pokud existuje) |
| §7 Postup | Sekce „Postup" — **přenesni BEZ ZTRÁTY obsahu** |
| §8 Quality Gates | Bash kód s COMMANDS.test/lint (pokud existuje) |
| §9 Report | Formát reportu (pokud definovaný) |
| §10 Self-check | Sekce „Self-check" (obvykle existuje) |
| §11 Failure Handling | Rozptýleno — sbírej error handling z celého skillu |
| §12 Metadata | Neexistuje v legacy — PŘIDEJ NOVĚ |

### M3) Doplň chybějící sekce

Sekce, které legacy skill nemá, doplň:
- §11 Failure Handling — vytvoř tabulku ze sebraných error handling bloků
- §12 Metadata — vyplň phase, step, depends_on, feeds_into
- Chybějící preconditions bash kód
- Chybějící anti-patterns v §7

**DŮLEŽITÉ:** Při doplňování §7 (Postup) NEPŘEPISUJ existující instrukce.
Pouze PŘIDEJ chybějící: příklady, minima, anti-patterns.
Pokud existující instrukce jsou dobré — nechej je.

### M4) Přidej builder-born tag

```md
<!-- built from: builder-template -->
```

### M5) Size check + progressive disclosure split (POVINNÉ pro migraci)

Legacy skills jsou typicky 500–1600+ řádků. Po migraci na §1–§12 bude SKILL.md ještě větší (přidané sekce). Proto je split **téměř vždy nutný** při migraci.

```bash
LINES=$(wc -l < "skills/fabric-${NAME}/SKILL.md")
if [ "$LINES" -gt 500 ]; then
  echo "SPLIT REQUIRED: $LINES lines"
fi
```

**Split strategie pro migraci:**

1. Vytvoř `skills/fabric-${NAME}/references/`
2. §7 Postup — přesuň detailní kroky do `references/workflow.md`, v SKILL.md nech jen přehled kroků s odkazem
3. K10 příklady — přesuň do `references/examples.md`
4. Kanonická pravidla / triage rules / dimensions — přesuň do `references/{domain}.md`
5. Rozsáhlé bash bloky (mimo §3 Preconditions) — přesuň do `references/scripts.md`
6. Ověř SKILL.md ≤ 500 řádků

**Co ZŮSTÁVÁ v SKILL.md (nesmí se přesunout):**
- Frontmatter + builder tag
- §1 Účel, §2 Protokol, §3 Preconditions (kompletní bash kód)
- §4 Vstupy, §5 Výstupy (krátké seznamy)
- §6 FAST PATH (bash volání)
- §7 Postup — **pouze přehled kroků** + odkazy na references/
- §8 Quality Gates, §9 Report template
- §10 Self-check (kompletní checkboxy)
- §11 Failure Handling, §12 Metadata

### M6) Validace migrace

Ověř že migrace nezhoršila skill:

- [ ] VEŠKERÁ stávající logika je zachována (nic nebylo smazáno — přesunuto do references/)
- [ ] Nová struktura odpovídá §1–§12
- [ ] Tag `<!-- built from: builder-template -->` přítomen
- [ ] **SKILL.md ≤ 500 řádků**
- [ ] Referenční soubory v `references/` obsahují VEŠKERÝ přesunutý obsah
- [ ] §7 Postup má MINIMÁLNĚ stejnou úroveň detailu jako před migrací (přímo + references)

### M6) Doporučení po migraci

```
Migrováno: skills/fabric-{NAME}/SKILL.md
Tag: <!-- built from: builder-template --> přidán
Přidané sekce: {seznam nových sekcí}

Další krok:
  Spusť `fabric-checker target={NAME}` pro ověření.
  Porovnej K1–K10 score PŘED a PO migraci.
  Pokud score kleslo → REVERT přes git checkout.
```

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

## Report

`{WORK_ROOT}/reports/builder-{YYYY-MM-DD}.md`:

```md
---
schema: fabric.report.v1
kind: builder
mode: {build|fix|migrate}
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
status: {OK|WARN|ERROR}
target: {skill_name}
---

# Builder Report — {YYYY-MM-DD}

## Mód: {BUILD|FIX|MIGRATE}
## Target: {skill_name nebo "multiple (fix)"}

## Provedené akce
{Seznam co builder udělal}

## Další krok
Spusť `fabric-checker` pro ověření.
```

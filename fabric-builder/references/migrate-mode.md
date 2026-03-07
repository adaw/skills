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

### M7) Doporučení po migraci

```
Migrováno: skills/fabric-{NAME}/SKILL.md
Tag: <!-- built from: builder-template --> přidán
Přidané sekce: {seznam nových sekcí}

Další krok:
  Spusť `fabric-checker target={NAME}` pro ověření.
  Porovnej K1–K10 score PŘED a PO migraci.
  Pokud score kleslo → REVERT přes git checkout.
```

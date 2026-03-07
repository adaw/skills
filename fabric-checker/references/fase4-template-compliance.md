# Fáze 4: Template Compliance (JEN pro Tier 2 builder-born skills)

## Scope

- **PŘESKOČ pro T1, T3 a SKIP.** Tato fáze se týká POUZE T2 skills.
- Tier 2 jsou skills vytvořené přes `fabric-builder build`
- Jak poznat: komentář `<!-- built from: builder-template -->` v SKILL.md

## Procedura

Přečti `skills/fabric-builder/assets/builder-template.md` a ověř:

- [ ] Tag `<!-- built from: builder-template -->` přítomen
- [ ] §1–§12 vyplněno nebo explicitně odstraněno s komentářem
- [ ] §2 Protokol je přesná kopie z template
- [ ] §7 Postup má: konkrétní instrukce, příklady, minima, anti-patterns
- [ ] §10 Self-check má ≥3 testovatelné položky
- [ ] §12 Metadata má phase, step, depends_on, feeds_into

## Scoring

```
Compliance score = splněné / relevantní × 100
- < 80 % → P1 finding
- < 50 % → P0 finding
```

## Příklady kontroly

### §2 Protocol check
- Skutečný protokol vs template
- Jsou logovány všechny kritické momenty?
- Má jasné START/END?

### §7 Procedure check
- Je postup algoritmic (ne vágní)?
- Jsou příklady/šablony?
- Je jasné minimum akceptovatelného výstupu?

### §10 Self-check check
- ≥3 testovatelné items?
- Kontrolují existenci, kvalitu, invarianty?

### §12 Metadata check
- `phase:` → klíčová fáze v fabric-loop
- `step:` → konkrétní krok
- `depends_on:` → seznam prereq skills
- `feeds_into:` → seznam downstream skills

## Output

Zahrň do reportu sekci:

```md
## Template Compliance

| Skill | T2? | §2 | §7 | §10 | §12 | % | Status |
|-------|-----|----|----|-----|-----|---|--------|
| {name} | YES | ✅ | ✅ | ✅ | ⚠️ | 92 | P1 |
```

Pokud žádný T2 skill neexistuje:
```md
## Template Compliance

**Žádné T2 (builder-born) skills aktuálně — template compliance N/A.**
```

## Běžné P0/P1 findings

- Chybí builder-template tag → P1
- §7 je vágní → P1
- §10 self-check je triviální → P1
- §12 metadata chybí → P0

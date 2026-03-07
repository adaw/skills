# Fáze 5: Evolution Radar

Syntéza nálezů z celého auditu + roadmap doporučení pro vylepšení.

## 5.1) Chybějící skills (porovnání s dev/workflows/)

Pokud existuje `dev/workflows/` s historickými workflow soubory:

| Starý workflow | Nový fabric skill | Kritičnost | Doporučení |
|---|---|---|---|
| {workflow name} | — | MISSING | Implementovat přes fabric-builder build |
| — | {skill} | NEW | Validovat design |

Output formát:
```md
## 5.1) Chybějící Skills

### Z dev/workflows/ ale ne v fabric/:
- {name} (MEDIUM) → Candidate pro fabric-builder build

### Nové skills bez legacy equivalent:
- {name} (DESIGN: yes/no)
```

## 5.2) Skill interaction gaps

Hledej:
- Artefakty bez producenta nebo konzumenta
- Dva skills modifikující stejný soubor bez koordinace
- Cyklické závislosti

Output formát:
```md
## 5.2) Skill Interaction Gaps

| Artefakt | Producent | Konzument | Issue |
|----------|-----------|-----------|-------|
| state.md | fabric-loop | ALL | ✅ Clear producer |
| {artifact} | NONE | {skill} | ⚠️ ORPHAN INPUT |
| {artifact} | {skill1} | {skill1},{skill2} | ⚠️ CONFLICT |
```

## 5.3) Legacy migration radar

Seřaď všechny T3 legacy skills podle K10 skóre (nejnižší = nejhorší):

```md
## 5.3) Legacy Migration Radar

| Skill | Tier | K10 | Migrace priorita | Doporučený sprint |
|-------|------|-----|-------------------|------------------|
| {name} | T3 | 2 | URGENT | Sprint 1 |
| {name} | T3 | 5 | HIGH | Sprint 2 |
| {name} | T3 | 8 | MEDIUM | Sprint 3+ |
```

Logika:
- K10 ≤ 3 → URGENT (dokumentace/work quality v pádu)
- K10 4-6 → HIGH
- K10 7+ → MEDIUM (lze nechati jak je, ale migrace by pomohla)

## 5.4) Top 5 doporučení pro builder

Vytvoř priority seznam nálezů ze všech fází. Seřaď podle:
1. **Severity** (P0 > P1 > P2)
2. **Scope** (Týká se více skills → vyšší priorita)
3. **Effort** (Čím méně úsilí, tím vyšší doporučení)

```md
## 5.4) Top 5 Doporučení pro fabric-builder

1. {finding description} — {affected skills} — {P0|P1|P2} — {estimated effort}
   - Impact: {što se zlepší}
   - Builder action: {konkrétní příkaz/config}

2. ...
```

## Output formát pro celou Fázi 5

```md
---

## FÁZE 5 — Evolution Radar

### 5.1) Chybějící Skills
[tabulka + komentář]

### 5.2) Skill Interaction Gaps
[tabulka + seznam issues]

### 5.3) Legacy Migration Radar
[tabulka seřazená dle K10]

### 5.4) Top 5 Doporučení
[seznam s prioritami + impact assessment]

### Shrnutí
{2-3 věty: co je nejurgentněji potřeba opravit}
```

## Příklady findings v 5.4

```
1. Shell injection risk (K4 scoring) — fabric-loop, fabric-init, fabric-design
   → P1 — Add comprehensive quoting guide for builders
   → Effort: 2 hours (update template + docs)

2. Missing K10 in legacy skills — 6 T3 skills
   → P1 → Create migration roadmap (prioritize by current K10)
   → Effort: 1 hour (triage only, builder does actual work)

3. State mutation audit — fabric-loop integrity
   → P0 → Formal verification of state.md write-chain
   → Effort: 4 hours (deep analysis + test coverage)
```

## Důležité principy

- ✅ Doporučení musí být **konkrétní** (ne "lepší dokumentace")
- ✅ Obsahuj **impact estimate** (co se zlepší)
- ✅ Seřaď podle **priority + effort** (easy wins first)
- ❌ Neignoruj findings z Fází 1-4 — musí být v 5.4

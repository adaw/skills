# H4: Fast-track Review — Detailní procedura

## Cíl
Quick review hotfix diff PŘED merge — odchytí regrese.

## Důležité
Hotfix neprocházi plným fabric-review cyklem (to by negoval fast-track). Místo toho proveď **self-review** na diff:

```bash
git diff "${MAIN_BRANCH}...HEAD" --stat
git diff "${MAIN_BRANCH}...HEAD"
```

## Kontrola: 4 dimenze (zkrácený review)

### R1 — Správnost
Řeší kód skutečně požadavek? Nejsou tam edge cases?

### R2 — Error handling
Každý nový try/except, každá síťová operace má fallback?

### R3 — Bezpečnost
- Žádné hardcoded secrets
- Žádný SQL injection
- Žádný path traversal

### R4 — Testy
Pokrývají testy hlavní scénáře? Nejsou to triviální pass-through testy?

## Minimum (výstup)
- 4 dimenze zkontrolované
- Pokud R1/R2/R3 finding: **oprav PŘED merge** (nečekej)
- Pokud R4 finding (nedostatečné testy): doplň testy

## Anti-patterns (zakázáno)
- Přeskočit review „protože je to hotfix" — tím se zavádějí regrese
- Review bez čtení diffu — to není review

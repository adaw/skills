# H1: Analýza požadavku — Detailní procedura

## Cíl
Pochop co hotfix má udělat, ověř effort, zkontroluj backlog.

## Postup (detailní instrukce)

1. **Přečti popis požadavku** od uživatele.

2. **Zkontroluj zda požadavek existuje v backlogu:**
   ```bash
   grep -rl "${KEYWORD}" "{WORK_ROOT}/backlog/" 2>/dev/null | head -5
   ```

3. **Pokud existuje backlog item** → použij ho (zachovej ID, aktualizuj status).

4. **Pokud NEexistuje** → vytvoř nový:
   ```bash
   python skills/fabric-init/tools/fabric.py intake-new \
     --source "hotfix" \
     --slug "hotfix-${SLUG}" \
     --title "${TITLE}"
   ```

5. **Odhadni effort:**
   - **XS:** < 20 řádků kódu, 1–2 soubory
   - **S:** < 100 řádků, 3–5 souborů
   - **Pokud odhad > S → STOP a doporuč sprint.**

## Minimum (výstup)
- Identifikovaný nebo vytvořený backlog item s ID
- Effort odhad (XS/S)
- Seznam dotčených souborů (min. 1)

## Anti-patterns (zakázáno)
- Implementovat M+ effort jako hotfix (skrytý tech debt)
- Ignorovat existující backlog item a vytvořit duplicitu
- Začít implementovat bez pochopení scope

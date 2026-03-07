# H2: Implementace — Detailní procedura

## Cíl
Kód + testy na dedikované hotfix branch.

## Postup (detailní instrukce)

### Vytvoř branch
```bash
git checkout "${MAIN_BRANCH}"
git pull --ff-only || echo "WARN: pull failed, using local main"
HOTFIX_BRANCH="hotfix/${TASK_ID}"
git checkout -b "${HOTFIX_BRANCH}"
```

### Implementuj kód
1. Implementuj minimální změnu — jen to co je nutné.
2. Dodržuj coding style projektu (ruff, type hints, 100 char line).

### Piš testy SOUČASNĚ s kódem

**Minimálně 3 testy per hotfix:**
1. **Happy path** — hlavní funkce funguje
2. **Edge case** — hraniční vstup / prázdný vstup / null
3. **Error handling** — neplatný vstup / chybový stav

Pokud hotfix přidává endpoint/CLI/tool → přidej integrační test.

### Test Template

```python
# tests/test_{module}_hotfix.py
import pytest

class TestHotfix{Feature}:
    """Tests for hotfix: {popis}."""

    def test_happy_path(self):
        """Main functionality works as expected."""
        # Arrange
        # Act
        # Assert
        ...

    def test_edge_case(self):
        """Boundary/empty/null input handled correctly."""
        ...

    def test_error_handling(self):
        """Invalid input raises appropriate error."""
        with pytest.raises(ValueError):
            ...
```

## Minimum (výstup)
- Funkční kód řešící požadavek
- Minimálně 3 testy (happy/edge/error)
- Žádné `pass`, `NotImplementedError`, `# TODO` v DONE kódu

## Anti-patterns (zakázáno)
- `pass` nebo `# TODO` v hotfix kódu — hotfix je DONE, ne WIP
- `NotImplementedError` stub — to není hotfix, to je placeholder
- Jeden test nebo žádné testy — min. 3
- Hotfix bez testů „protože je to malá změna" — **NEAKCEPTOVATELNÉ**
- Změna v nesouvisejících souborech (scope creep)

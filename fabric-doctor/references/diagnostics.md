# fabric-doctor — Diagnostické heuristiky (reference)

## ORDER-DEPENDENT: Bisect contaminátoru

Když test projde v izolaci ale failne v suite, najdi kontaminující soubor:

```bash
FAILING="tests/test_failing.py"
ALL_TEST_FILES=$(python -m pytest --collect-only -q 2>/dev/null \
  | grep '::' | cut -d: -f1 | sort -u | grep -v "$FAILING")

# Bisect: spouštěj failing soubor po každém jiném
for PREV in $ALL_TEST_FILES; do
  python -m pytest "$PREV" "$FAILING" -v --tb=short > /tmp/doctor-bisect.log 2>&1
  if [ $? -ne 0 ]; then
    echo "CONTAMINATOR FOUND: $PREV → $FAILING"
    # Inspekce obou souborů pro sdílený modul
    break
  fi
done
```

### Inspekce kontaminátoru — co hledat

1. **sys.modules manipulation**
```bash
grep -n "sys\.modules" "$CONTAMINATOR" "$FAILING"
# Hledej:
# - setdefault (neschopný přepsat existující fake)
# - del sys.modules[X] bez odpovídajícího re-inject
# - Přímý assignment bez cleanup fixture
```

2. **Module-level code execution**
```bash
# Kód mimo funkce/třídy běží při importu a může měnit stav
python -c "
import ast, sys
tree = ast.parse(open('$CONTAMINATOR').read())
for node in ast.iter_child_nodes(tree):
    if isinstance(node, (ast.Assign, ast.AugAssign, ast.Expr)):
        if not isinstance(getattr(node, 'value', None), (ast.Constant, ast.Name)):
            print(f'L{node.lineno}: module-level side effect: {ast.dump(node)[:80]}')
"
```

3. **Fixture scope issues**
```bash
# session/module scope fixtures sdílejí stav mezi testy
grep -n '@pytest.fixture.*scope.*session\|@pytest.fixture.*scope.*module' "$CONTAMINATOR"
# Pokud existují → ověř že mají cleanup (yield + teardown)
```

4. **Global/class variable mutations**
```bash
# Modifikace globálních proměnných
grep -n "^[A-Z_]*\s*=" "$CONTAMINATOR" | grep -v "^#\|def \|class "
# Modifikace class variables
grep -n "cls\.\|self\.__class__\." "$CONTAMINATOR"
```

---

## GENUINE-FAIL: Dependency diagnostika

### Import errors
```bash
# Zachyť konkrétní ImportError
python -m pytest "$FAILING" -v --tb=long 2>&1 | grep -A5 "ImportError\|ModuleNotFoundError"

# Zkontroluj zda package je nainstalován
MISSING_PKG=$(grep -oP "No module named '\K[^'']+" /tmp/doctor-isolated-*.log)
pip show "$MISSING_PKG" 2>/dev/null || echo "MISSING: $MISSING_PKG"
```

### Env var interference
```bash
# Proxy env vars způsobují httpx/requests problémy
env | grep -iE 'proxy|socks|all_proxy'
# Fix: httpx.Client(trust_env=False) nebo requests.Session() s explicit proxy=None

# Ověř zda test soubor vytváří HTTP klienty
grep -n "httpx\.\|requests\.\|urllib" "$FAILING"
```

### Package version incompatibility
```bash
# Ověř verzi problémového package vs expected
PACKAGE="qdrant-client"  # příklad
INSTALLED=$(pip show "$PACKAGE" 2>/dev/null | grep "^Version:" | awk '{print $2}')
# Porovnej s pyproject.toml requirements
REQUIRED=$(grep "$PACKAGE" pyproject.toml 2>/dev/null)
echo "Installed: $INSTALLED, Required: $REQUIRED"

# Hledej AttributeError — typický symptom version mismatch
grep -n "AttributeError" /tmp/doctor-isolated-*.log
```

---

## FLAKY: Nedeterminismus diagnostika

```bash
# Spusť 5× a porovnej výsledky
for i in 1 2 3 4 5; do
  python -m pytest "$FAILING" -v --tb=no > "/tmp/doctor-flaky-$i.log" 2>&1
  grep -oP '\d+ passed' "/tmp/doctor-flaky-$i.log"
done

# Hledej time-dependent kód
grep -n "datetime\.now\|time\.time\|time\.sleep" "$FAILING"

# Hledej random bez seed
grep -n "random\.\|uuid\." "$FAILING" | grep -v "seed\|mock\|patch"

# Hledej race conditions (async, threading)
grep -n "async\|await\|threading\|multiprocessing" "$FAILING"
```

---

## Kanonický Fix Katalog

### F1: sys.modules setdefault → direct assignment
```python
# BEFORE (broken):
sys.modules.setdefault("pkg", fake_module)

# AFTER (correct):
sys.modules["pkg"] = fake_module  # type: ignore
```

### F2: sys.modules no cleanup → fixture restore
```python
@pytest.fixture(autouse=True)
def _restore_modules():
    """Restore sys.modules after each test."""
    original = dict(sys.modules)
    yield
    # Remove any modules added during test
    added = set(sys.modules) - set(original)
    for mod in added:
        del sys.modules[mod]
    # Restore any modules that were modified
    sys.modules.update(original)
```

### F3: httpx proxy env leak → trust_env=False
```python
# BEFORE (broken in proxy environments):
self._client = httpx.Client(timeout=timeout)

# AFTER (immune to env vars):
self._client = httpx.Client(timeout=timeout, trust_env=False)
```

### F4: Missing package attribute → getattr fallback
```python
# BEFORE (broken with older package version):
field_schema = qm.PayloadSchemaType.DATETIME

# AFTER (backwards compatible):
field_schema = getattr(qm.PayloadSchemaType, "DATETIME", qm.PayloadSchemaType.KEYWORD)
```

### F5: Fixture scope contamination → narrow scope + cleanup
```python
# BEFORE (leaks state across tests):
@pytest.fixture(scope="module")
def shared_backend():
    return create_backend()

# AFTER (isolated per test):
@pytest.fixture(scope="function")
def backend():
    be = create_backend()
    yield be
    be.cleanup()
```

### F6: Module-level import side effect → lazy import
```python
# BEFORE (runs at import time, contaminates other test files):
from heavy_module import GlobalSingleton
singleton = GlobalSingleton()  # module-level side effect!

# AFTER (deferred to function scope):
@pytest.fixture
def singleton():
    from heavy_module import GlobalSingleton
    return GlobalSingleton()
```

# S4: Virtuální průchod fabric-loop (end-to-end simulace)

Spustí kompletní cyklus fabric-loop na reálných datech BEZ modifikace workspace.
Výstup: simulační log s tick-by-tick průběhem celého lifecycle.

## Příprava

```bash
# 1) Vytvoř dočasný adresář pro simulační výstupy
SIM="_sim"
mkdir -p "$SIM"

# 2) Inicializuj log
cat > "$SIM/run-log.md" << 'HEADER'
# Virtual Loop Simulation
## Parameters
HEADER
echo "- date: $(date -Iseconds)" >> "$SIM/run-log.md"
echo "- loop=auto, goal=release" >> "$SIM/run-log.md"
echo "" >> "$SIM/run-log.md"
echo "## Tick Log" >> "$SIM/run-log.md"
```

## Kritické nastavení bash (bez tohoto simulace PADNE)

```bash
set -uo pipefail
# ⚠️  NEPOUŽÍVEJ set -e !
# Důvod: pytest, ruff, git a další externími nástroje vracejí
# nenulový exit code i při normálním provozu (např. ruff najde
# lint chyby → exit 1). S set -e by skript okamžitě skončil.
```

## Zachytávání výstupů externích příkazů

```bash
# ✅ SPRÁVNĚ — || true zabrání ukončení skriptu
TEST_OUTPUT=$(python3 -m pytest -q --tb=no 2>&1 || true)
LINT_OUTPUT=$(python3 -m ruff check . 2>&1 || true)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-git")
COMPILE=$(python3 -c "import src.llmem" 2>&1 || true)

# ❌ ŠPATNĚ — bez || true skript s pipefail skončí při prvním selhání
TEST_OUTPUT=$(python3 -m pytest -q --tb=no 2>&1)
```

## Struktura simulace

```
Preconditions (P1–P8) → Idle detection → Tick loop:
  vision → status → architect → process → gap → generate →
  intake → prio → sprint → analyze → implement → test →
  review → close → docs → check → archive → LOOP BOUNDARY
```

## Preconditions (musí projít VŠECHNY, jinak STOP)

| ID | Co ověřit | Bash |
|----|-----------|------|
| P1 | config.md existuje | `[ -f "$WORK/config.md" ]` |
| P2 | WORK_ROOT existuje | `[ -d "$WORK" ]` |
| P3 | state.md existuje | `[ -f "$WORK/state.md" ]` |
| P4 | vision.md existuje | `[ -f "$WORK/vision.md" ]` |
| P5 | backlog/ neprázdný | `ls $WORK/backlog/*.md 2>/dev/null \| wc -l` |
| P6 | skills root existuje | `[ -d "skills/fabric-init" ]` |
| P7 | templates/ existují | `ls $WORK/templates/*.md 2>/dev/null \| wc -l` |
| P8 | intake/ existuje | `[ -d "$WORK/intake" ]` |

## Idle detection (auto mode)

```bash
ACTIVE_ITEMS=$(for f in $WORK/backlog/*.md; do
  s=$(grep '^status:' "$f" 2>/dev/null | head -1 | awk '{print $2}')
  [ "$s" != "DONE" ] && [ "$s" != "BLOCKED" ] && echo "$f"
done | wc -l)
PENDING_INTAKE=$(ls $WORK/intake/*.md 2>/dev/null | wc -l)

if [ "$ACTIVE_ITEMS" -gt 0 ] || [ "$PENDING_INTAKE" -gt 0 ]; then
  # práce existuje → start orientation
else
  # idle → konec simulace
fi
```

## Tick loop — klíčová pravidla

1. MAX_TICKS=50 (guard proti nekonečné smyčce)
2. Každý tick: `SIM_TICK++`, loguj step+phase, proveď akci, posuň `SIM_STEP`
3. Archiv = loop boundary → break (jedna iterace celého cyklu)
4. Simulované reporty zapisuj POUZE do `$SIM/` (nikdy do `$WORK/reports/`)
5. Reálné příkazy (pytest, ruff) VŽDY s `|| true`

## Per-step akce (co každý tick ověřuje)

| Step | Reálná data | Simulovaný výstup |
|------|-------------|-------------------|
| vision | čte vision.md + visions/*.md | $SIM/vision-report.md |
| status | spouští pytest, ruff, git log | $SIM/status-report.md |
| architect | počítá .py soubory, ADRs | $SIM/architect-report.md |
| process | hledá processes/process-map.md | $SIM/process-report.md |
| gap | porovnává vision sekce vs backlog | $SIM/gap-report.md |
| generate | (simulované — žádné nové items) | $SIM/generate-report.md |
| intake | čte intake/*.md, loguje tituly | $SIM/intake-report.md |
| prio | počítá READY/DESIGN/IDEA | $SIM/prio-report.md |
| sprint | vybírá kandidáty (DESIGN+Task/Bug) | $SIM/sprint-report.md |
| analyze | hledá T0→T1→T2 WIP kandidáta | $SIM/analyze-report.md |
| implement | import check (`python3 -c "import..."`) | $SIM/implement-report.md |
| test | spouští pytest -q --tb=short | $SIM/test-report.md |
| review | spouští ruff check + ruff format --check | $SIM/review-report.md |
| close | simuluje merge | $SIM/close-report.md |
| docs | hledá docs/ adresář | $SIM/docs-report.md |
| check | pytest + ruff + governance + templates | $SIM/check-report.md |
| archive | počítá reporty k archivaci | $SIM/archive-report.md |

## Očekávaný výstup (všechno OK = 17 ticků)

```
PRECONDITIONS: P1–P8 PASS
IDLE DETECTION: work exists
Tick 1: vision ✅    Tick 10: analyze ✅
Tick 2: status ✅    Tick 11: implement ✅
Tick 3: architect ✅ Tick 12: test ✅
Tick 4: process ⚠️   Tick 13: review ✅
Tick 5: gap ✅       Tick 14: close ✅
Tick 6: generate ✅  Tick 15: docs ⚠️
Tick 7: intake ✅    Tick 16: check ✅
Tick 8: prio ✅      Tick 17: archive ✅
Tick 9: sprint ✅    → LOOP BOUNDARY
```

## Známé WARNy (nejsou chyby)

- `process-map.md missing` — fabric-process ještě neběžel, vytvoří se při prvním reálném běhu
- `docs/ directory missing` — fabric-docs ho vytvoří
- Test failures se reportují ale neblokují (simulace je virtuální)
- Lint chyby se reportují ale neblokují

## Úklid po simulaci

```bash
rm -rf "$SIM"
```

## Anti-patterns

- ❌ Použít `set -e` — zabitje skript při prvním pytest FAIL
- ❌ Psát výstupy do reálného `$WORK/reports/` — simulace NESMÍ modifikovat workspace
- ❌ Použít `$()` na příkazy co mohou selhat bez `|| true`
- ❌ Zapomenout `2>&1` u externích příkazů — stderr by nebyl zachycen
- ❌ Cesty typu `$WORK/../fabric/` — pokud WORK=fabric, vede mimo workspace

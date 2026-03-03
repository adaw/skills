---
name: fabric-generate
description: "Autonomously generate high-value work when the system has nothing urgent to do. Uses vision alignment + codebase signals (architect/gap/check/review) to propose 0–8 actionable intake items (source=generate) and writes a generate report. Strong deduplication to avoid spam."
---

# GENERATE — Autonomní generování work items (vision-aligned)

## Účel

Když backlog nemá dost kvalitních položek nebo projekt stagnuje, `fabric-generate` vytvoří další smysluplnou práci:
- zrychlí vývoj,
- zvýší bezpečnost,
- zlepší kvalitu testů a dokumentace,
- a posune projekt směrem k vizi.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-generate" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-generate" --event end --status OK --report "{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Výstup jsou **intake items** (ne přímo backlog), aby triage (`fabric-intake`) zachovala standardní pipeline.

> Poznámka: **0 items je OK** (např. backlog je zdravý nebo deduplikace nedovolí nic nového). V takovém případě stále vytvoř report.

---

## FAST PATH (doporučeno) — backlog snapshot strojově

Pro rychlost a determinismus si nejdřív vyrob snapshot backlogu:

```bash
python skills/fabric-init/tools/fabric.py backlog-scan --json-out "{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json"
```

Použij ho pro:
- počet READY/DESIGN položek,
- deduplikaci title/id,
- rychlé zhodnocení, zda má smysl generovat.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` + `{VISIONS_ROOT}/*.md` (sub-vize pro širší kontext)
- `{WORK_ROOT}/backlog.md` + backlog items (pro dedup)
- `{WORK_ROOT}/decisions/` + `decisions/INDEX.md`
- `{WORK_ROOT}/specs/` + `specs/INDEX.md`
- poslední reporty (pokud existují):
  - `reports/architect-*.md`
  - `reports/gap-*.md`
  - `reports/check-*.md`
  - `reports/review-*.md`
- `{CODE_ROOT}/`, `{TEST_ROOT}/`, `{DOCS_ROOT}/` (rychlý scan)

---

## Výstupy

- 0–8 intake items v `{WORK_ROOT}/intake/` dle `{WORK_ROOT}/templates/intake.md`:
  - `source: generate`
  - `initial_type` typicky `Chore/Task/Bug`
  - `raw_priority` 3–10
- report `{WORK_ROOT}/reports/generate-{YYYY-MM-DD}.md`

---

## Guardrails (anti-spam)

1. Max 8 nových intake itemů na běh.
2. Každý item musí mít:
   - 1 větu „proč“ (value/risk),
   - evidence (soubor/pattern nebo „missing“),
   - doporučenou akci.
3. Silná deduplikace:
   - pokud existuje podobný backlog item, negeneruj duplicitu; místo toho přidej poznámku do existujícího itemu nebo vytvoř intake „clarify existing“.

---

## Postup

### 1) Zjisti, jestli je potřeba generovat

Podívej se do backlog indexu:
- pokud je v backlogu < 10 položek se statusem `READY` nebo `DESIGN` (a nejsou DONE) → generuj
- pokud backlog je zdravý → vygeneruj max 3 „quality improvements“ nebo nic

### 2) Discovery zdroje (7 kategorií)

Vygeneruj kandidáty z těchto oblastí:

1) **Security**  
- input validation, secrets hygiene, dependency risk, authz boundaries

2) **Reliability & Error handling**  
- retries/timeouts, cancellation, logging, observability

3) **Test quality**  
- chybějící tests pro kritické moduly, flaky tests, missing regression for recent bugs

4) **Docs drift**  
- veřejné API bez docs, chybějící usage examples

5) **Performance**  
- hot paths, N^2 loops, unnecessary I/O

6) **Developer Experience**  
- CI gates, pre-commit, faster local dev loop

7) **Architektonická governance**
- chybějící ADR/spec pro klíčové oblasti
- drift: kód proti accepted ADR / active spec
- stale proposed ADR (> stale_proposed_days)
- stale draft specs (> stale_draft_days)

### 3) Vision alignment scoring (jednoduše)

Pro každý kandidát napiš do reportu (ber v úvahu core vizi i sub-vize z `{VISIONS_ROOT}/`):
- alignment HIGH/MEDIUM/LOW
- proč (který goal/pillar, z core nebo sub-vize)

LOW alignment může projít jen pokud jde o kritickou bezpečnost/operational věc.

### 4) Deduplikace

Před vytvořením intake itemu:
- zkontroluj backlog titles + intake pending titles (podobnost)
- pokud existuje:
  - nevytvářej duplicitu
  - do reportu napiš „deduped“

### 5) Vytvoř intake items (top 3–8)

Použij `{WORK_ROOT}/templates/intake.md`:
- `source: generate`
- `initial_type`:
  - Bug pro regresní/defekt
  - Chore pro tooling/CI
  - Task pro implementační změny
  - Spike pro research/unknown
- `raw_priority`:
  - 9–10 pro security/reliability critical
  - 6–8 pro high impact
  - 3–5 pro nice-to-have

### 6) Generate report

`reports/generate-{YYYY-MM-DD}.md`:
- kolik itemů vzniklo
- pro každý:
  - title
  - category
  - alignment (HIGH/MED/LOW)
  - raw_priority
  - evidence
- deduped candidates

---

## Self-check

- max 8 intake items
- každý item má evidence + doporučenou akci
- report existuje

---
name: fabric-vision
description: "Analyze and validate the project vision documents. Extracts goals, pillars, constraints, success metrics, and decision principles. Produces a vision report and (if vision is incomplete/ambiguous) generates an intake item to improve the vision specification."
---

# VISION — Analýza vize + quality gates pro „směr“

## Účel

Zajistit, že agent ví:
- **proč** projekt existuje,
- **co** je cílem (a co není),
- **jak** poznáme úspěch,
- a jaké jsou principy rozhodování.

## Protokol (povinné)

Zapiš do protokolu START/END (a případně ERROR). Použij společný logger:

- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-vision" --event start`
- `python skills/fabric-init/tools/protocol_log.py --work-root "{WORK_ROOT}" --skill "fabric-vision" --event end --status OK --report "{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md"`

Pokud skončíš **STOP** nebo narazíš na CRITICAL:
- loguj `--event error --status ERROR` a dej krátké `--message` (1 věta).


Bez kvalitní vize se backlog rozpadne na náhodnou práci.

---

## Vstupy

- `{WORK_ROOT}/config.md`
- `{WORK_ROOT}/vision.md` — core vize (purpose, pillars, principles, constraints)
- `{VISIONS_ROOT}/*.md` — sub-vize a rozšíření (ekonomika, bezpečnost, governance, architektonické vize, roadmap detaily…)

### Vztah core vision ↔ sub-vize

`vision.md` je **kořenový dokument** — definuje proč, co a jak. Sub-vize v `{VISIONS_ROOT}/` **rozvíjejí** jednotlivé pilíře nebo koncepty do hloubky. Core `vision.md` by měl na sub-vize odkazovat (PŘÍKLAD: `→ viz {VISIONS_ROOT}/<tema>.md`). Sub-vize NESMÍ odporovat core vizi — pokud je rozpor, je to finding do reportu.

---

## Výstupy

- `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md`
- volitelně intake item: `{WORK_ROOT}/intake/vision-improve-*.md` (pokud chybí klíčové části)

---

## Postup

### 1) Načti a strukturalizuj vizi

Z vision dokumentů vytáhni:

- **Purpose / Mission** (1–3 věty)
- **Pillars** (3–7 pilířů)
- **Goals** (měřitelné cíle, ideálně)
- **Principles** (jak se rozhodujeme)
- **Non-goals** (co vědomě neděláme)
- **Success metrics** (KPI, nebo alespoň proxy metriky)
- **Constraints** (tech stack, bezpečnost, compliance, latency, cost)

Pokud existují sub-vize (`{VISIONS_ROOT}/*.md`):
- Načti každou a přidej její cíle/pilíře/principy k celkovému obrazu
- Označ zdroj u každého goal/principle (core vs. sub-vize název)
- Detekuj konflikty mezi core a sub-vizemi → reportuj jako finding
- Sub-vize mohou přidávat nové pilíře, rozšiřovat existující, nebo definovat detailní roadmap pro konkrétní oblast

### 2) Vision quality gates

Vyhodnoť:

- Má vize **měřitelné** success metrics? (ANO/NE)
- Jsou definované **non-goals**? (ANO/NE)
- Je jasné **priority ordering** (must/should/could)? (ANO/NE)
- Jsou definované **constraints**? (ANO/NE)

**Quality gates pro vision (P2 work quality):**
Vision.md validace (automatizovatelná):
- Obsahuje sekci "Principles" s ≥3 principy
- Obsahuje sekci "Goals" s ≥1 cílem
- Obsahuje sekci "Non-goals" s ≥1 položkou
- Žádný princip není duplicitní (normalize + compare)

**Per-pillar kvantitativní assessment (POVINNÉ):**

Pro KAŽDÝ pilíř z vision.md vyhodnoť:

```markdown
### Pillar Assessment
| Pilíř | Coverage % | Implementation % | Drift | Verdikt |
|-------|-----------|------------------|-------|---------|
| {pillar_1} | {backlog items / total needed}% | {DONE items / total}% | {LOW/MEDIUM/HIGH} | ON TRACK / CAUTION / DEVIATION |
```

Metodika:
- **Coverage %** = kolik z toho, co pilíř vyžaduje, je v backlogu (heuristika: počet backlog items s `linked_vision_goal` matchujícím pilíř / odhadovaný potřebný počet)
- **Implementation %** = kolik backlog items pro pilíř je DONE vs total
- **Drift** = míra odchylky od zamýšleného směru: LOW (na cestě), MEDIUM (částečná odchylka), HIGH (zásadní odchylka)
- **Verdikt:**
  - `ON TRACK` — Coverage ≥70%, Implementation trending up, Drift LOW
  - `CAUTION` — Coverage 40-70% NEBO Implementation stagnating NEBO Drift MEDIUM
  - `DEVIATION` — Coverage <40% NEBO Drift HIGH NEBO žádný DONE item za poslední sprint

**Anti-pattern:** ❌ "Všechny pilíře ON TRACK" bez čísel — VŽDY uveď konkrétní procenta a trend.

### 3) Najdi ambiguitu a konflikty

- konflikty mezi core vizí (`vision.md`) a sub-vizemi (`{VISIONS_ROOT}/*.md`)
- příliš obecné cíle („zlepšit kvalitu” bez metrik)
- chybějící definice cílového uživatele
- sub-vize, které nejsou referencované z core vision.md (osiřelé)
- core pilíře, které nemají rozpracovanou sub-vizi (potenciální gap)

### 4) Vytvoř vision report

`reports/vision-{date}.md`:

- Stručné shrnutí (1 odstavec)
- Extracted pillars/goals/principles
- Quality gate výsledky
- Top 5 risků z nejasné vize
- Doporučení pro backlog (co z toho plyne jako top priority)

### 5) Pokud vize není dostatečná → vytvoř intake item

Pokud chybí aspoň 2 z těchto věcí: metrics, non-goals, constraints, priority ordering:
- vytvoř intake item dle `{WORK_ROOT}/templates/intake.md`:
  - `source: generate` (nebo manual)
  - `initial_type: Chore`
  - `raw_priority: 6–8`
  - title: „Doplnit vizi: metrics/non-goals/constraints“
- do těla napiš konkrétní otázky a návrh struktury

---

## Self-check

- report existuje v `{WORK_ROOT}/reports/vision-{YYYY-MM-DD}.md`
- report obsahuje: Purpose/Mission, Pillars, Quality gate výsledky, Risks
- pokud chybí ≥2 quality gates (metrics, non-goals, constraints, priority ordering) → intake item existuje
- pokud existují sub-vize → jsou zmíněné v reportu (konflikty/alignment)

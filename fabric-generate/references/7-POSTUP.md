# §7 — Postup (JÁDRO SKILLU)

## 7.1) Zjisti, jestli je potřeba generovat

**Co:** Podívej se do backlog indexu. Pokud je backlog příliš tenký (< 10 READY/DESIGN položek bez DONE statusu), generuj. Pokud je backlog zdravý, vygeneruj jen 3 „quality improvements" nebo skip.

**Jak (detailní instrukce):**
1. Načti `{WORK_ROOT}/reports/backlog-scan-{YYYY-MM-DD}.json` ze FAST PATH
2. Počítej READY a DESIGN položky (exclude DONE, CANCELED, BLOCKED)
3. Pokud počet < 10 → continue do kroku 7.2 (full generation)
4. Pokud počet ≥ 10 → generate jen 3–5 quality improvements (test coverage, docs drift) nebo skip s poznámkou

**Minimum:**
- Rozhodnutí: generovat FULL / quality improvements only / skip (zaloguj důvod v reportu)
- Pokud skip: report s vysvětlením proč se negeneruje

**Anti-patterns (zakázáno):**
- Neignoruješ stav backlogu a generuješ 8 items když je backlog overfull → spamm
- Negeneralizuješ vůbec žádné položky když backlog je kriticky tenký (< 5 items)

---

## 7.2) Discovery zdroje (7 kategorií)

**Co:** Vytvořit seznam kandidátů z těchto sedmi oblastí. Každý kandidát = (kategorie, evidence, alignment draft, priority draft).

**Jak (detailní instrukce):**

Scanuj následující:

### 1) **Security (výběr)**
- vstupní validace (API endpoints, CLI args, env vars)
- secrets hygiene (API keys, DB passwords exposure)
- dependency risk (outdated libs, CVEs)
- authz boundaries (kdo má přístup k čemu)
- Hledej: "WARN" nebo "CRITICAL" ze `reports/gap-*.md` security section

Příklad candidate:
```
Category: Security
Title: "Add input validation to /capture/event endpoint"
Evidence: gap-2026-03-06.md (line 15: "POST /capture has no schema validation")
Code evidence: {CODE_ROOT}/src/llmem/api/server.py line 42–50
```

### 2) **Reliability & Error handling**
- retries/timeouts (co se děje když selhá network call?)
- cancellation (CO když user cancelluje?)
- logging & observability (viditelnost runtime stavů)
- failure modes (kaskádující selhání)
- Hledej: "unhandled exception" v logu, nelogované operace, timeout handling absent

Příklad candidate:
```
Category: Reliability
Title: "Add timeout handling to database queries"
Evidence: check-2026-03-06.md (line 22: "DB queries timeout-unsafe")
Code evidence: {CODE_ROOT}/src/llmem/storage/backends/qdrant.py (no timeout param)
```

### 3) **Test quality**
- chybějící tests pro kritické moduly (coverage < 80%)
- flaky tests (timeout-sensitive, race conditions)
- missing regression tests pro recent bugs
- Hledej: `reports/check-*.md` test coverage section; recent bug fixes bez test

Příklad candidate:
```
Category: Test quality
Title: "Add edge case tests for triage_event empty content"
Evidence: check-2026-03-06.md (line 8: "triage/patterns.py coverage 62%")
Code evidence: {CODE_ROOT}/src/llmem/triage/heuristics.py (function triage_event)
```

### 4) **Docs drift**
- veřejné API bez docs
- chybějící usage examples
- neaktuálné docs (kód se změnil, docs ne)
- Hledej: recent commits modifikující API + absence v docs; ADR bez docs

Příklad candidate:
```
Category: Docs drift
Title: "Document RecallQuery.allow_secrets field"
Evidence: {DOCS_ROOT}/api.md RecallQuery (missing allow_secrets field)
Code evidence: {CODE_ROOT}/src/llmem/models.py (allow_secrets field added 2 weeks ago)
```

### 5) **Performance**
- hot paths (N^2 loops, cartesian products)
- unnecessary I/O (duplicate reads, missing cache)
- profiling data nebo algoritmy
- Hledej: `reports/architect-*.md` performance section; slow queries/builds

Příklad candidate:
```
Category: Performance
Title: "Optimize backlog search with indexing"
Evidence: architect-2026-03-06.md (line 50: "backlog search O(n) on 1000 items")
Code evidence: {CODE_ROOT}/src/llmem/backlog.py (linear search loop)
```

### 6) **Developer Experience**
- CI gates missing (no lint, no format check)
- pre-commit hooks slow nebo absence
- local dev loop (build time, test time)
- Hledej: stale CI config, developer complaints, slow test suite

Příklad candidate:
```
Category: Developer Experience
Title: "Add pre-commit hooks for ruff formatting"
Evidence: no pre-commit config in {WORK_ROOT}/.pre-commit-config.yaml
Code evidence: last commit had lint issues (missed by CI)
```

### 7) **Architektonická governance**
- chybějící ADR/spec pro klíčové kódy
- drift: kód proti accepted ADR
- stale proposed ADR (> stale_proposed_days z config.md)
- stale draft specs (> stale_draft_days z config.md)
- Hledej: `decisions/INDEX.md` a `specs/INDEX.md` pro status="proposed" nebo "draft"

Příklad candidate:
```
Category: Governance
Title: "Create ADR for event-sourcing strategy"
Evidence: decisions/INDEX.md (missing ADR for event-sourcing in backlog)
Code evidence: {CODE_ROOT}/src/llmem/storage/log_jsonl.py (event-sourcing impl but no ADR)
```

**Minimum:**
- Minimálně 3–5 kandidátů (ne všechny kategorie se vždy objeví)
- Pro každý: (kategorie, popis, evidence file/pattern, priority draft)

**Anti-patterns (zakázáno):**
- Scanuj "všechny" bez konkrétního zaměření → vágní kandidáti
- Kandidáti bez evidence ("I feel like we should...") → spekulace, není ok
- Ignoruješ governance: generuješ task k technologii kterou ADR zakazuje

---

## 7.3) Vision alignment scoring

**Co:** Pro každý kandidát z kroku 7.2 napiš alignment (HIGH/MEDIUM/LOW) a zdůvodnění.

**Jak (detailní instrukce):**

1. Čti `{WORK_ROOT}/vision.md` (core vize)
2. Čti sub-vize z `{VISIONS_ROOT}/*.md` (pokud existují)
3. Pro každý kandidát:
   - Odpovídá core vizi? → HIGH
   - Odpovídá sub-vizi nebo pillarům? → MEDIUM
   - Je kritická bezpečnost/operational věc (DOS, data loss, critical unhandled exception)? → HIGH i pokud slabá vision alignment
   - Jinak: LOW

**Příklady:**

```
Kandidát: "Add rate limiting middleware"
Core vision: "Reliability: Rate limiting protection against abuse"
Alignment: HIGH (explicit goal)
Reasoning: "Direct match to Reliability pillar in vision.md"

---

Kandidát: "Document RecallQuery.allow_secrets"
Core vision: "Usability: public API discoverable and well-documented"
Sub-vision: "API documentation completeness"
Alignment: MEDIUM (aligns with usability, not explicit goal)
Reasoning: "Supports API documentation completeness (sub-vision), enables users to discover allow_secrets feature"

---

Kandidát: "Optimize backlog search"
Core vision: "Performance: sub-1 second backlog operations"
Alignment: HIGH (explicit performance goal, sub-1s mentioned)
Reasoning: "Current O(n) search blocks vision goal; optimization directly enables it"
```

**Minimum:**
- Každý kandidát má alignment (HIGH/MED/LOW) + 1-2 věta zdůvodnění
- Reference na konkrétní goal/pillar z vision.md (ne abstraktní)

**Anti-patterns (zakázáno):**
- LOW alignment projde JENOM pokud je kritická bezpečnost nebo operational urgence
- Alignment bez reference na konkrétní goal/pillar
- "I think this is important" bez vision.md reference → REJECT candidate

---

## 7.4) Deduplikace

**Co:** Kontrola, že vygenerovaný item není duplikátem něčeho, co v backlogu už je.

**Jak (detailní instrukce):**

```python
def dedup_items(candidates: list[Item], backlog_snapshot: JSON) -> list[Item]:
    """Deduplicate candidates against backlog."""
    seen_keys = set()
    dedup_log = []
    result = []

    # Ulož backlog titles do set
    for backlog_item in backlog_snapshot['items']:
        key = normalize(backlog_item['title'])
        seen_keys.add(key)

    # Filtruj kandidáty
    for candidate in candidates:
        key = normalize(candidate['title'])
        if key not in seen_keys:
            seen_keys.add(key)
            result.append(candidate)
        else:
            dedup_log.append({
                'candidate': candidate['title'],
                'reason': f'duplicate of backlog item with key "{key}"'
            })

    return result, dedup_log

def normalize(title: str) -> str:
    """Lowercase, strip special chars, collapse whitespace."""
    return (title.lower()
            .replace('-', ' ')
            .replace('_', ' ')
            .replace('/', ' ')
            .split())  # tokenize
            .sort()  # order-invariant comparison
            .join(' ')
```

**Příklady:**

```
Candidate 1: "Add logging to error handler"
Backlog item: "ERROR_HANDLER_LOGGING" (existing)
Normalize: ["add", "error", "handler", "logging"] == ["add", "error", "handler", "logging"]
Decision: SKIP (duplicate)
Dedup log: "duplicate of backlog-0042"

---

Candidate 2: "Rate limiting on /recall endpoint"
Backlog item: "Rate limiting on /capture endpoint" (existing, but DIFFERENT endpoint)
Normalize candidate: ["rate", "limiting", "recall", "endpoint"]
Normalize backlog: ["rate", "limiting", "capture", "endpoint"]
Decision: KEEP (different enough — different endpoint)

---

Candidate 3: "Improve test coverage"
Backlog item: "Add test cases for ..." (vague, but similar intent)
Normalize both → similar → SKIP (likely duplicate intent)
Dedup log: "likely duplicate — candidate is 'Improve test coverage', backlog has 'Add test cases for...'"
```

**Minimum:**
- Dedup evidence v reportu: tabulka skippnutých kandidátů + vysvětlení proč
- Pro každý SKIP: reference na konkrétní backlog item (nebo ID)

**Anti-patterns (zakázáno):**
- Nevykonáš dedup → backlog plný duplikátů; user frustrace
- Dedup je příliš agresivní (skippneš "Add tests for patterns" a "Add tests for triage") → loss of specificity
- Dedup je příliš slabý (přeskočíš jenom EXACT duplicates) → duplicates slip through

---

## 7.5) Vytvoř intake items (top 3–8)

**Co:** Pro deduplikované kandidáty (max 8) vytvoř formální intake items.

**Jak (detailní instrukce):**

Použij `{WORK_ROOT}/templates/intake.md`:

```yaml
---
schema: fabric.intake_item.v1
title: "{Akční popis — měl by dát implementátorovi jasnou akci}"
source: generate
initial_type: {Bug|Chore|Task|Spike}
raw_priority: {1-10}
created: {YYYY-MM-DD}
status: new
linked_vision_goal: "{konkrétní goal z vision.md, pokud existuje}"
---

## Kontext
{Evidence: konkrétní file/pattern/query, co problém ukazuje}

## Doporučená akce
{Kroky, které implementátor dělá — konkrétně, ne vágně}
```

**initial_type výběr:**
- `Bug` → pro regresní/defekt s reproducer (existuje broken behavior)
- `Chore` → pro tooling/CI/infrastructure/devops
- `Task` → pro implementační změny bez defektu (feature, refactor, docs)
- `Spike` → pro research/unknown (pokud candidate je "zjistit, kolik práce to bude")

**raw_priority scale (1-10):**
- 9–10 → security/reliability CRITICAL (DOS, data loss, unhandled exception, system crash)
- 7–8 → high impact (5–10 days effort, important feature/gap)
- 5–6 → medium (1–5 days, noticeable quality improvement)
- 3–4 → nice-to-have (small, polish, DX improvement)
- 1–2 → very low priority (won't do unless backlog empty)

---

## 7.5a) Konkrétní příklady generované items (z LLMem domain)

### Příklad 1: Security gap (priority 9, Evidence)
```yaml
---
schema: fabric.intake_item.v1
title: "Add rate limiting middleware to /capture/event endpoint"
source: generate
initial_type: Task
raw_priority: 9
created: "2026-03-06"
status: new
linked_vision_goal: "Reliability - Rate Limiting"
---

## Kontext
Gap report (gap-2026-03-06.md, line 15) flagged: POST /capture/event has no rate limiting.
**Impact:** DOS vulnerability on public endpoint.
**Code evidence:** {CODE_ROOT}/src/llmem/api/server.py line 42–50 — no rate limiting decorator on endpoint.
**Vision alignment:** HIGH (Reliability pillar explicitly: "Rate Limiting protection against abuse").

## Doporučená akce
1. Implement rate limiting middleware (recommend: slowapi or custom decorator using Redis)
2. Apply to `/capture/event` and `/capture/batch` endpoints (both public)
3. Set threshold: 100 requests/minute per IP (or configurable in config.md)
4. Test: simulate 150 req/min → verify 429 responses after threshold
5. Document rate limit in {DOCS_ROOT}/api.md under /capture/event section
6. Add to config.md: `capture_rate_limit_per_minute: 100`

**Effort estimate:** S (1 day)
**Dependencies:** None (can be done independently)
```

### Příklad 2: Test coverage gap (priority 7)
```yaml
---
schema: fabric.intake_item.v1
title: "Add edge case tests for triage_event() empty content scenario"
source: generate
initial_type: Task
raw_priority: 7
created: "2026-03-06"
status: new
---

## Kontext
Check report (check-2026-03-06.md, line 8) flagged: triage/patterns.py has 62% coverage (target ≥80%).
**Missing:** Edge case handling in triage_event() for empty content.
**Code evidence:** {CODE_ROOT}/src/llmem/triage/heuristics.py, function triage_event() lines 15–40.
**Regression risk:** HIGH — if empty content causes index error, triage pipeline crashes silently.

## Doporučená akce
1. Add test `test_triage_event_empty_content`:
   - Input: content=""
   - Expected: No index error; returns empty memory items
2. Add test `test_triage_event_whitespace_only`:
   - Input: content="   " (only whitespace)
   - Expected: Treated as empty; returns empty items
3. Add test `test_triage_event_unicode_edge`:
   - Input: content="🔒 secret" (emoji edge case)
   - Expected: Secret detection still works
4. Run coverage report after tests → should jump to ≥78%
5. If coverage still < 80%, add 1–2 more cases for other functions in module

**Effort estimate:** M (2 days)
**Dependencies:** None
```

### Příklad 3: Docs drift (priority 5)
```yaml
---
schema: fabric.intake_item.v1
title: "Document RecallQuery.allow_secrets field in API docs"
source: generate
initial_type: Chore
raw_priority: 5
created: "2026-03-06"
status: new
linked_vision_goal: "Usability - API documentation completeness"
---

## Kontext
Decision ADR-D0001 added `allow_secrets: bool` field to RecallQuery model.
**Code evidence:** {CODE_ROOT}/src/llmem/models.py RecallQuery class (committed 2 weeks ago).
**Docs gap evidence:** {DOCS_ROOT}/api.md RecallQuery section doesn't mention field.
**Impact:** API users won't discover feature; incomplete documentation lag.

## Doporučená akce
1. Update {DOCS_ROOT}/api.md RecallQuery section:
   - Add field definition: `allow_secrets: bool (default: false) — whether to include secrets in recall results. WARNING: Secrets are stored plaintext; only enable if recall is over encrypted channel.`
2. Add usage example:
   ```bash
   curl -X POST http://localhost:8080/recall \
     -H "Content-Type: application/json" \
     -d '{
       "query": "remember API key",
       "allow_secrets": true
     }'
   ```
3. Cross-link to ADR-D0001 in docstring
4. Add to "Security" section of docs: "By default allow_secrets=false to protect secrets in logs/monitoring"

**Effort estimate:** S (4 hours)
**Dependencies:** None
```

### Príklad 4: Governance (priority 8)
```yaml
---
schema: fabric.intake_item.v1
title: "Create ADR for event-sourcing strategy in memory log"
source: generate
initial_type: Spike
raw_priority: 8
created: "2026-03-06"
status: new
linked_vision_goal: "Architecture - Event-sourced design"
---

## Kontext
**Code evidence:** {CODE_ROOT}/src/llmem/storage/log_jsonl.py implements event-sourcing pattern (append-only JSONL log).
**Governance gap:** No ADR documents this design decision.
**Risk:** Future changes may contradict event-sourcing principles without realizing it.

## Doporučená akce
1. Create {WORK_ROOT}/decisions/ADR-EVENT-SOURCING.md
2. Document:
   - **Decision:** Use append-only JSONL log as source of truth for observations
   - **Why:** Immutability, auditability, rebuild capability, easy debugging
   - **Trade-offs:** Larger disk; slower append for high-frequency events
   - **Consequences:** All state mutations must be logged; backups must preserve log order
3. Link in {WORK_ROOT}/decisions/INDEX.md
4. Status: "accepted"

**Effort estimate:** S (4 hours, 200-line ADR)
**Dependencies:** None (research spike)
**Follow-up:** Implement linked_vision_goal: "Create integration test: rebuild whole state from log"
```

**Minimum per item:**
- `title`: konkrétní, měl by dát implementátorovi jasnou akci
- `source: generate`
- `initial_type` je jedním z: Bug, Chore, Task, Spike
- `raw_priority` je 1–10 (ne mimo rozsah)
- Evidence: konkrétní file/pattern/query v kontextu
- Doporučená akce: konkrétní kroky (ne vágní "improve X")
- Všechny příklady výše mají tuto strukturu → kopíruj

**Anti-patterns (zakázáno):**
- Priority mimo rozsah 1–10 → clamp na hranice
- Item bez description nebo doporučené akce
- Evidence je vágní ("somewhere in codebase") → fail item, negeneruj ji
- Title je vágní ("improve testing") bez konkrétní modulu
- Doporučená akce má "TODO" nebo "discuss with team" → příliš vágní
- Intake bez linked_vision_goal když alignment je HIGH/MEDIUM

---

## 7.5b) Selection heuristics (jak si vybrat top 3–8)

Pokud máš 20 deduplikovaných kandidátů, jak si vybereš top 3–8?

1. **Priority first:** Seřaď priority 9–10 nahoru
2. **Effort vs. impact:** Malý effort, vysoký impact → prioritní
3. **Alignment:** HIGH alignment → prioritní
4. **Blockers:** Item, který blokuje jiné → prioritní

Příklad ranking:

```
| Title | Priority | Effort | Alignment | Vision-related |
|-------|----------|--------|-----------|----------------|
| Rate limiting | 9 | 1d | HIGH | YES (Reliability goal) |
| Test coverage triage | 7 | 2d | HIGH | YES (Quality goal) |
| Docs API | 5 | 4h | MEDIUM | YES (Usability goal) |
| Timeout handling | 8 | 3d | HIGH | YES (Reliability goal) |
| Refactor backlog search | 6 | 5d | MEDIUM | NO (optimization only) |

TOP 4:
1. Rate limiting (9, 1d)
2. Timeout handling (8, 3d)
3. Test coverage (7, 2d)
4. Docs API (5, 4h)
```

---

## 7.6) Generate report

**Co:** Vytvořit `reports/generate-{YYYY-MM-DD}.md` s shrnutím.

**Jak (detailní instrukce):**

Viz SKILL.md §9 — Report template.

**Minimum:**
- Report existuje s validní YAML frontmatter (`schema: fabric.report.v1`)
- Summary + State + Discovery sources + Dedup evidence table + Generated items table + Warnings
- Tabulky jsou vyplněné, ne prázdné
- Dedup evidence: seznam top 5 skippnutých kandidátů + vysvětlení proč

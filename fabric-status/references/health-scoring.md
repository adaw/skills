# Health Scoring & Risk Identification — fabric-status

## 7.10) Health Score Calculation (heuristický)

**Co:** Vypočítat health score 0–100 na základě signálů.

**Jak:**
Start 100:
- -40 pokud tests FAIL
- -20 pokud lint FAIL
- -10 pokud format_check FAIL
- -10 pokud WIP breach (více než 1 IN_PROGRESS/IN_REVIEW)
- -10 pokud BLOCKED > READY
- -5 pokud docs STALE (> 30 dní bez updatu)
- -5 pokud git DIRTY (uncommitted changes)
- -3 pokud stale branches > 2

Cap score: min = 0, max = 100

**Minimum:** Health score musí být číselný (0–100) a logika musí být explicitní v reportu.

**Formula explicitně v reportu:**
```
Score = 100
  - (tests FAIL ? 40 : 0)
  - (lint FAIL ? 20 : 0)
  - (format_check FAIL ? 10 : 0)
  - (WIP breach ? 10 : 0)
  - (BLOCKED > READY ? 10 : 0)
  - (docs STALE ? 5 : 0)
  - (git DIRTY ? 5 : 0)
  - (stale branches > 2 ? 3 : 0)
```

---

## 7.11) Risks Identification (top 3–5)

**Co:** Naidentifikovat konkrétní rizika, ne generické.

**Jak:** Pro každé riziko: jméno + specifika + impact + next action. Příklady:

### Risk Pattern: Test Failures
```
**2 test failures (1 flaky, 1 regression)**
- test_recall_memory: flaky (fails ~40% of runs, takes 12s, timeout 15s) → Run tests 3x, investigate timeout
- test_capture_validation: NEW regression after commit abc123 → Revert or fix, add regression test
```

### Risk Pattern: Blocked Items
```
**3 BLOCKED backlog items (1 day overdue)**
- task-b008 (Qdrant setup): waiting for devops → unblock by EOD Friday
- task-b012 (API spec): waiting on architect → escalate to leads
- task-b015 (deployment): blocked on CI pipeline → investigate CI status
```

### Risk Pattern: Stale Branches
```
**2 stale feature branches (10+ days)**
- feature/semantic-v2: 15 days, 3 commits behind main → merge or close by sprint end
- hotfix/rate-limit: 12 days, ready for merge → merge today
```

### Risk Pattern: Docs Drift
```
**Docs last modified 45 days ago**
- API reference outdated (endpoints changed, missing auth scheme) → update docs in sprint
- Architecture diagram (3 months stale) → refresh before Q2 review
```

### Risk Pattern: Code Quality
```
**Lint failures in critical module**
- src/recall/pipeline.py: 12 lint errors (type hints, complexity) → run lint --fix, review complex functions
- src/storage/backends/qdrant.py: 5 errors (imports not used) → cleanup
```

---

## Health Assessment Levels

| Score | Level | Assessment | Recommendation |
|-------|-------|------------|-----------------|
| 85–100 | **Healthy** | All signals green; team can execute autonomously | Continue current pace; optionally tackle tech debt |
| 70–84 | **At-risk** | 1–2 signals yellow; manageable | Address top 2 risks this sprint; escalate test failures |
| 50–69 | **Critical** | 3+ signals red or tests FAIL + blocked backlog | Emergency triage required; reduce WIP, unblock items |
| < 50 | **Broken** | Majority signals red; execution blocked | STOP current work; focus on remediation |

---

## Anti-patterns (DO NOT)

- Netvrdíš „dobrý stav" (score > 70) pokud tests FAIL
- Netvrdíš „dobrý stav" pokud BLOCKED > READY
- Nepiš generické riziko „kód je komplexní" bez specifik (file, function, metric)
- Netvrdíš že riziko je „low risk" bez quantifikace (time/effort to fix)
- Neignoruй UNKNOWN signals — třeba je v reportu zdůraznit že data chybí

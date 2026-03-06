# Intake Processing — Příklady (K10)

> Tento soubor obsahuje konkrétní příklady intake triage s reálnými LLMem daty.
> Čti ho pomocí Read toolu pro referenci při zpracování intake items.

---

## Example: Process 4 Intake Items in a Single Run

**Input intake items in {WORK_ROOT}/intake/:**
1. `intake/gap-g001-add-pydantic-validation.md` (from fabric-gap)
2. `intake/generate-add-rate-limiting-middleware.md` (from fabric-generate)
3. `intake/user-feedback-improve-recall-sorting.md` (user submission)
4. `intake/check-missing-test-command.md` (from fabric-check)

**Processing:**

Item 1: Gap-driven (validation)
- Source: gap
- Title: "Add Pydantic validation to /capture/event endpoint"
- Triage → Type: Bug (fixing security gap)
- Assign: tier=T0, effort=M, status=READY
- Create: `backlog/task-b042-add-validation.md`
- Move: `intake/done/gap-g001-add-pydantic-validation.md`

Item 2: Generate-driven (rate limiting)
- Source: generate
- Title: "Add rate limiting middleware"
- Triage → Type: Task (feature)
- Assign: tier=T0, effort=S, status=READY
- Create: `backlog/task-b043-rate-limiting.md`
- Move: `intake/done/generate-add-rate-limiting-middleware.md`

Item 3: User feedback (recall sorting)
- Source: user_feedback
- Title: "Improve recall scoring to prioritize recent memories"
- Triage → Type: Story (enhancement)
- Unclear priority → Assign: tier=T2, effort=L, status=DESIGN
- Open question: "Does this align with semantic embeddings vision goal?"
- Create: `backlog/epic-e004-improve-recall.md`
- Move: `intake/done/user-feedback-improve-recall-sorting.md`

Item 4: Check audit (test command)
- Source: check
- Title: "Configure test command in config.md"
- Triage → Type: Chore (tooling)
- Assign: tier=T0, effort=XS, status=READY
- Create: `backlog/chore-b044-config-test.md`
- Move: `intake/done/check-missing-test-command.md`

**Output:**
- 4 new backlog items created (IDs: b042–b044)
- Regenerated backlog.md index (4 items added, sorted by prio)
- Intake report: intake-2026-03-06.md

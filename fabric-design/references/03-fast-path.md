# §6 Deterministic FAST PATH — Detailed Setup

## Step 1: Backlog index sync

```bash
python skills/fabric-init/tools/fabric.py backlog-index 2>/dev/null || true
```

Syncs the backlog index with current items. Tolerates failures (non-blocking).

## Step 2: Governance index sync

```bash
python skills/fabric-init/tools/fabric.py governance-index 2>/dev/null || true
```

Syncs ADR and SPEC indices for governance constraints. Tolerates failures (non-blocking).

## Step 3: Discover project language and framework

```bash
PROJECT_LANG=$(grep 'Jazyk' "{WORK_ROOT}/config.md" | head -1 | sed 's/.*|\s*//' | tr -d ' |')
echo "Project language: ${PROJECT_LANG:-unknown}"
```

Extract the primary programming language from config.md. This informs:
- Which framework/tooling to expect (Django, FastAPI, etc.)
- Code style and naming conventions
- Available testing frameworks and patterns
- Documentation standards

These three deterministic steps establish the baseline state before design begins. They are idempotent and fail-open (never block on missing indices).

---
name: claude-code-runner
description: >
  Spawn and monitor Claude Code CLI agents for coding tasks with real-time progress reporting.
  Use this skill whenever you need to delegate a coding task to a Claude Code subprocess — building
  features, refactoring, PR reviews, test generation, debugging, or any multi-step coding workflow.
  Triggers on: "/cc [prompt]", "run claude code", "spusť claude na...", "deleguj na claude code",
  or any request that involves spawning a Claude Code agent for a non-trivial coding task.
  DO NOT use for simple single-file edits — use the Edit tool directly instead.
  DO NOT use if Claude Code CLI (`claude`) is not installed.
  Variant: "/scc [prompt]" runs on Mac Studio via SSH (see scode skill for remote execution).
---

# Claude Code Runner

Spawn Claude Code CLI as a non-interactive subprocess, monitor its progress in real-time,
and report structured results back to the user.

## Prerequisites

Claude Code CLI must be installed and authenticated:
```bash
which claude && claude --version
```
If not available, tell the user to install it: `npm install -g @anthropic-ai/claude-code`

## Quick Reference

```bash
# Basic usage
/cc "implement feature X"

# With model selection
/cc --opus "complex architectural task"
/cc --sonnet "standard coding task"          # default
/cc --minimax "task using minimax model"

# With auto-push (commits and pushes after completion)
/cc --push "fix bug Y"

# With branch management
/cc --branch feature/my-feature "implement feature"

# With workdir auto-detection
/cc --repo my-project "add tests"

# Combined
/cc --opus --branch feature/auth --push "implement authentication"

# Remote execution on Mac Studio (uses scode skill)
/scc --opus "heavy compute task"
```

## When to Use

- **Building features**: Multi-file changes, new components, API endpoints
- **Refactoring**: Large-scale code restructuring across multiple files
- **PR reviews**: Clone/checkout a branch into a temp dir, run analysis
- **Test generation**: Comprehensive test suites for existing code
- **Debugging**: Complex multi-step debugging sessions
- **Documentation**: Auto-generating docs from codebase analysis

**Don't use for**: Quick single-file edits, simple questions, file reads — use built-in tools.

## Core Execution Pattern

### Step 1: Determine Working Directory

Pick the right workdir based on the task:

- **Existing project**: Use the project root (look for `package.json`, `Cargo.toml`, `pyproject.toml`, `.git`)
- **PR review**: Create a temp dir, clone/checkout the relevant branch
- **New project**: Create a fresh directory
- **Auto-detection**: Use `--repo <name>` to auto-find in `~/repos/`

```bash
# Auto-find repo by name
./launch.sh --repo my-project --prompt "add tests"

# Explicit workdir
./launch.sh --workdir /path/to/project --prompt "refactor"
```

### Step 2: Launch Claude Code

Always use non-interactive mode (`-p`) with streaming JSON output for progress monitoring:

```bash
claude -p "[TASK_PROMPT]" \
  --output-format stream-json \
  --verbose \
  --max-turns 25 \
  --dangerously-skip-permissions \
  2>&1 | tee /tmp/claude-code-run.jsonl
```

**Flag reference:**

| Flag | Purpose |
|---|---|
| `-p "prompt"` | Non-interactive print mode — runs task and exits |
| `--output-format stream-json` | Stream JSONL with tool calls, text, results — the key to progress monitoring |
| `--verbose` | Include full turn-by-turn detail |
| `--max-turns N` | Limit autonomous turns (prevent runaway loops). Default: 25, simple tasks: 10 |
| `--dangerously-skip-permissions` | Skip permission prompts (needed for unattended execution) |
| `--model <id>` | Model to use (see model mapping below) |
| `--allowedTools "..."` | Restrict tools if needed (e.g., `"Read,Grep,Glob"` for read-only analysis) |
| `--append-system-prompt "..."` | Add extra instructions while keeping defaults |
| `--fallback-model sonnet` | Auto-fallback when primary model is overloaded |

**Model mapping:**

| Shortcut | Model ID |
|---|---|
| `opus` | `claude-opus-4-6` |
| `sonnet` | `claude-sonnet-4-6` (default) |
| `minimax` | `openrouter/minimax/minimax-01` |

### Step 2b: Branch Management (Optional)

Use `--branch` to work on a specific branch:

```bash
# Create new branch and work on it
./launch.sh --branch feature/auth --prompt "implement authentication" --bg

# Checkout existing branch
./launch.sh --branch bugfix/login --prompt "fix login issue" --bg

# With auto-push after completion
./launch.sh --branch feature/api --push --prompt "add API endpoints" --bg
```

The script will:
1. Check if branch exists locally → checkout
2. Check if branch exists on remote → checkout tracking branch
3. Otherwise → create new branch

### Step 2c: Auto Git Push (Optional)

Use `--push` to automatically commit and push changes after CC completes:

```bash
./launch.sh --prompt "implement feature" --push --bg
```

After completion:
1. `git add -A` — stage all changes
2. `git commit -m "cc: [task summary]"` — commit with auto-generated message
3. `git push -u origin HEAD` — push to remote

### Step 3: Monitor Progress

The `stream-json` output produces one JSON object per line (JSONL). Key event types to watch:

#### Text events (Claude's thinking/explanations)
```json
{"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll start by..."}]}}
```

#### Tool use events (actions Claude is taking)
```json
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write", "input": {"file_path": "src/app.ts"}}]}}
```

#### TodoWrite events (task progress — most useful for tracking)
```json
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "TodoWrite", "input": {"todos": [
  {"id": "1", "content": "Set up project structure", "status": "completed", "priority": "high"},
  {"id": "2", "content": "Implement API routes", "status": "in_progress", "priority": "high"},
  {"id": "3", "content": "Write tests", "status": "pending", "priority": "medium"}
]}}]}}
```

#### Result event (final outcome)
```json
{"type": "result", "subtype": "success", "result": "...", "total_cost_usd": 0.05, "duration_ms": 45000, "num_turns": 12}
```

### Step 4: Parse and Report Progress

Use the bundled `scripts/monitor.sh` script or parse inline:

```bash
# Quick progress summary from TodoWrite events
cat /tmp/claude-code-run.jsonl | grep -o '"TodoWrite"' | wc -l

# Extract latest todo list status
tac /tmp/claude-code-run.jsonl | grep -m1 'TodoWrite' | jq '.message.content[] | select(.name=="TodoWrite") | .input.todos[] | "\(.status): \(.content)"'

# Extract all file operations
cat /tmp/claude-code-run.jsonl | jq -r 'select(.message.content[]?.name == "Write" or .message.content[]?.name == "Edit") | .message.content[] | select(.name) | "\(.name): \(.input.file_path // .input.file)"' 2>/dev/null

# Get final result
tail -1 /tmp/claude-code-run.jsonl | jq '{success: (.subtype == "success"), cost: .total_cost_usd, duration_sec: (.duration_ms / 1000), turns: .num_turns, result: .result[:200]}'
```

## ⭐ Preferred: Background + Live Progress + Auto-Push

Always run in background with live progress monitoring. Use `launch.sh` which handles everything:

```bash
# Full-featured launch with all options
./scripts/launch.sh \
  --prompt "implement user authentication with JWT" \
  --repo my-project \
  --branch feature/auth \
  --opus \
  --push \
  --bg

# Minimal background launch
./scripts/launch.sh --prompt "fix bug" --bg
```

**Live progress pings**: Every 5 seconds, the script detects TodoWrite updates and reports:
```
━━━ 📋 Progress Update (14:32:15) ━━━
  ✅ Set up project structure
  🔧 Implementing API routes
  ⏳ Write tests
  📊 Progress: 1/3 tasks
```

**On completion**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏁 Claude Code finished (exit code: 0)
{
  "success": true,
  "cost": 0.0523,
  "duration_sec": 127,
  "turns": 15
}
📦 Auto-committing changes...
🚀 Pushing to remote...
✅ Auto-push complete
```

### Manual polling (if needed)

```bash
# Check if still running
kill -0 $(cat /tmp/claude-code-run.pid) 2>/dev/null && echo "Running..." || echo "Finished"

# Latest activity
tail -5 /tmp/claude-code-run.jsonl | jq -r '.message.content[]?.text // .message.content[]?.name // empty' 2>/dev/null | tail -3

# File change count
grep -c '"Write"\|"Edit"' /tmp/claude-code-run.jsonl 2>/dev/null

# Current todo status
tac /tmp/claude-code-run.jsonl | grep -m1 'TodoWrite' | jq -r '.message.content[] | select(.name=="TodoWrite") | .input.todos[] | "[\(.status | ascii_upcase)] \(.content)"' 2>/dev/null
```

## Progress Reporting Format

When reporting to the user, use this structure:

```
🔄 Claude Code: [RUNNING/COMPLETED/FAILED]
📊 Progress: X/Y tasks completed
⏱️ Duration: Xs | 💰 Cost: $X.XX | 🔄 Turns: X

Current activity:
  ✅ Set up project structure
  🔧 Implementing API routes (in progress)
  ⏳ Write tests (pending)
  ⏳ Documentation (pending)

Files modified: src/app.ts, src/routes/api.ts, tests/api.test.ts
```

## Prompt Engineering for Better Task Execution

Structure your task prompts for Claude Code to maximize effectiveness:

```
[TASK DESCRIPTION]

Requirements:
- [Specific requirement 1]
- [Specific requirement 2]

Constraints:
- [Do not modify file X]
- [Use library Y for Z]

Success criteria:
- [All tests pass]
- [No TypeScript errors]
- [Follows existing code patterns]
```

Adding a `TodoWrite` nudge improves progress tracking:
```
Before starting, create a todo list of all steps you'll take using TodoWrite. Update
the todo list as you complete each step. This helps me track your progress.
```

## Error Handling

If the run fails or produces no output:

1. **Check exit code**: Non-zero means error
2. **Check JSONL for error events**: `grep '"error"' /tmp/claude-code-run.jsonl`
3. **Common issues**:
   - Auth expired → `claude auth login`
   - Rate limited → Wait and retry, or use `--fallback-model`
   - Context overflow → Reduce scope, split into subtasks
   - Tool permission denied → Check `--allowedTools` or use `--dangerously-skip-permissions`

## Advanced: Chaining Multiple Runs

For complex workflows, chain Claude Code runs:

```bash
# Step 1: Analyze and plan
claude -p "Analyze the codebase in ./src and create a refactoring plan. Save to /tmp/plan.md" \
  --output-format stream-json --max-turns 10 --dangerously-skip-permissions \
  --allowedTools "Read,Grep,Glob,Write" \
  > /tmp/run-plan.jsonl 2>&1

# Step 2: Execute the plan
claude -p "Execute the refactoring plan in /tmp/plan.md" \
  --output-format stream-json --max-turns 30 --dangerously-skip-permissions \
  > /tmp/run-execute.jsonl 2>&1

# Step 3: Verify
claude -p "Run all tests and verify the refactoring was successful" \
  --output-format stream-json --max-turns 10 --dangerously-skip-permissions \
  --allowedTools "Read,Bash,Grep" \
  > /tmp/run-verify.jsonl 2>&1
```

## Advanced: Custom Subagents

Define specialized subagents for specific roles:

```bash
claude -p "[PROMPT]" \
  --agents '{
    "reviewer": {
      "description": "Code reviewer for quality checks after changes",
      "prompt": "You are a senior code reviewer. Check for bugs, security issues, and code smells.",
      "tools": ["Read", "Grep", "Glob"],
      "model": "sonnet"
    },
    "tester": {
      "description": "Test writer for generating comprehensive tests",
      "prompt": "You write thorough unit and integration tests.",
      "tools": ["Read", "Write", "Bash"],
      "model": "sonnet"
    }
  }' \
  --output-format stream-json \
  --dangerously-skip-permissions
```

## Remote Execution: /scc (Mac Studio)

For heavy compute tasks or when you want to offload work to a more powerful machine, use `/scc` which runs Claude Code on Mac Studio via SSH.

```bash
# Run on Mac Studio
/scc --opus "train model and evaluate"

# Equivalent to:
# scode "cd ~/repos/project && ./scripts/launch.sh --opus --prompt 'train model'"
```

This uses the `scode` skill for SSH-based remote execution. See `scode/SKILL.md` for details on:
- SSH connection setup
- File syncing between local and remote
- Output streaming

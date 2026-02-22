---
name: claude-code-runner
description: >
  Spawn and monitor Claude Code CLI agents for coding tasks with real-time progress reporting.
  Use this skill whenever you need to delegate a coding task to a Claude Code subprocess — building
  features, refactoring, PR reviews, test generation, debugging, or any multi-step coding workflow.
  Triggers on: "/code [prompt]", "run claude code", "spusť claude na...", "deleguj na claude code",
  or any request that involves spawning a Claude Code agent for a non-trivial coding task.
  DO NOT use for simple single-file edits — use the Edit tool directly instead.
  DO NOT use if Claude Code CLI (`claude`) is not installed.
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
| `--model sonnet` | Use Sonnet for cost efficiency, or `opus` for complex tasks |
| `--allowedTools "..."` | Restrict tools if needed (e.g., `"Read,Grep,Glob"` for read-only analysis) |
| `--append-system-prompt "..."` | Add extra instructions while keeping defaults |
| `--fallback-model sonnet` | Auto-fallback when primary model is overloaded |

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

## Running in Background with Progress Polling

For long tasks, run in background and poll for updates:

```bash
# Launch in background
claude -p "[PROMPT]" \
  --output-format stream-json \
  --verbose \
  --max-turns 30 \
  --dangerously-skip-permissions \
  > /tmp/claude-code-run.jsonl 2>&1 &
CLAUDE_PID=$!

echo "Claude Code running as PID $CLAUDE_PID"
```

Then poll progress periodically:

```bash
# Check if still running
kill -0 $CLAUDE_PID 2>/dev/null && echo "Running..." || echo "Finished"

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

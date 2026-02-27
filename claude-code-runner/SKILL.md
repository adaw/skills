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
# Basic usage — runs Opus in background by default
/cc "implement feature X"

# With model override
/cc --model sonnet "standard coding task"
/cc --model minimax "task using minimax model"

# Review mode (readonly + sonnet + review focus)
/cc --review "check this codebase"

# Resume a previous run
/cc --resume /tmp/claude-code-run-1234.jsonl --prompt "continue fixing tests"

# Prompt templates
/cc --template fix-bugs
/cc --template add-tests
/cc --template refactor
/cc --template review
/cc --template docs

# With auto-push (commits and pushes after completion)
/cc --push "fix bug Y"

# With branch management
/cc --branch feature/my-feature "implement feature"

# With workdir auto-detection
/cc --repo my-project "add tests"

# Foreground mode (disable default background)
/cc --no-bg "quick fix"

# Combined
/cc --branch feature/auth --push "implement authentication"

# Remote execution on Mac Studio (uses scode skill)
/scc "heavy compute task"
```

## Defaults

| Setting | Default | Notes |
|---|---|---|
| Model | `claude-opus-4-6` (opus) | Override with `--model sonnet` |
| Background | `true` | Use `--no-bg` for foreground |
| Max turns | `25` | Override with `--max-turns N` |
| Telegram notify | On completion (bg only) | Sends task summary, turns, cost, success/fail |

## When to Use

- **Building features**: Multi-file changes, new components, API endpoints
- **Refactoring**: Large-scale code restructuring across multiple files
- **PR reviews**: Use `--review` for readonly analysis
- **Test generation**: `--template add-tests`
- **Bug fixing**: `--template fix-bugs`
- **Debugging**: Complex multi-step debugging sessions
- **Documentation**: `--template docs`

**Don't use for**: Quick single-file edits, simple questions, file reads — use built-in tools.

## Flags Reference

| Flag | Purpose |
|---|---|
| `--prompt, -p` | Task prompt (required unless --template) |
| `--workdir, -w` | Working directory (default: cwd) |
| `--repo, -r` | Auto-find repo in ~/repos/ by name |
| `--model, -m` | Model: opus (default), sonnet, minimax |
| `--max-turns, -t` | Maximum turns (default: 25) |
| `--bg` | Run in background (default: true) |
| `--no-bg` | Run in foreground |
| `--readonly` | Read-only mode |
| `--review` | Review mode: readonly + sonnet + review focus |
| `--resume FILE` | Resume from previous JSONL log |
| `--template NAME` | Prompt template (fix-bugs, add-tests, refactor, review, docs) |
| `--log, -l` | Log file path |
| `--system, -s` | Extra system prompt |
| `--push` | Auto git add/commit/push after completion |
| `--branch, -b` | Git branch to use |

## Context Injection

Before each launch, the script auto-regenerates `~/.claude/CLAUDE.md` with:
- **Available Skills**: All skills from ~/.openclaw/workspace/skills/ with descriptions
- **Available Tools**: Scripts from ~/tools/lex/scripts/ + key CLI tools (imsg, blogwatcher, remindctl, memo, etc.)
- **Workspace info**: Paths to repos, skills, tools

This means CC always knows what tools and skills are available, in any project.

## Telegram Notifications

In background mode, when CC finishes, a Telegram notification is sent with:
- ✅/❌ Success or failure
- Task summary (first 80 chars)
- Turns, cost, duration
- Log file path

## Progress Monitoring

```bash
# Watch live progress
./scripts/monitor.sh /tmp/claude-code-run-*.jsonl --watch

# Check if still running
kill -0 $(cat /tmp/claude-code-run.pid) 2>/dev/null && echo "Running..." || echo "Finished"

# Latest activity
tail -5 /tmp/claude-code-run-*.jsonl | jq -r '.message.content[]?.text // .message.content[]?.name // empty' 2>/dev/null | tail -3
```

## Prompt Templates

| Template | What it does |
|---|---|
| `fix-bugs` | Review codebase, find and fix all bugs, run tests after each fix |
| `add-tests` | Add comprehensive tests for untested functions, verify they pass |
| `refactor` | Refactor for clarity, performance, maintainability |
| `review` | Thorough code review: bugs, security, code smells |
| `docs` | Add/improve documentation, docstrings, README |

Templates can be combined with a custom prompt: `--template fix-bugs --prompt "focus on the auth module"`

## Error Handling

If the run fails or produces no output:

1. **Check exit code**: Non-zero means error
2. **Check JSONL for error events**: `grep '"error"' /tmp/claude-code-run-*.jsonl`
3. **Common issues**:
   - Auth expired → `claude auth login`
   - Rate limited → Wait and retry
   - Context overflow → Reduce scope, split into subtasks

## Remote Execution: /scc (Mac Studio)

For heavy compute tasks, use `/scc` which runs Claude Code on Mac Studio via SSH.
See `scode/SKILL.md` for details.

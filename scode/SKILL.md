---
name: scode
description: Run Claude Code on Mac Studio via SSH. Use when you need to execute Claude Code CLI for coding tasks, code reviews, or running agents on the remote Mac Studio machine. For local execution, use 'code' skill instead.
---

# scode - Run Claude Code on Mac Studio

This skill executes Claude Code commands on Mac Studio via SSH.

## Usage

```bash
# Basic usage
~/.openclaw/workspace/skills/scode/scripts/scode.sh <repo> "<prompt>"

# Background mode (runs async, notifies when done)
~/.openclaw/workspace/skills/scode/scripts/scode.sh -b <repo> "<prompt>"
```

## Examples

```bash
# Run a coding task
scode.sh calc "Add sin function to calc.py"

# Background mode - returns immediately, notifies on completion
scode.sh -b myproject "Refactor auth module"

# Monitor background job output
tail -f /tmp/scode-*.log
```

## SSH Command Pattern

Direct SSH usage:
```bash
ssh adam@mac.local 'cd ~/repos/REPO && /opt/homebrew/bin/claude -p --dangerously-skip-permissions "PROMPT"'
```

With stream-json output for monitoring:
```bash
ssh adam@mac.local 'cd ~/repos/REPO && /opt/homebrew/bin/claude -p --output-format stream-json --dangerously-skip-permissions "PROMPT"'
```

## CLI Flags Reference

| Flag | Description |
|------|-------------|
| `-p` | Non-interactive print mode |
| `--output-format stream-json` | JSONL streaming output |
| `--dangerously-skip-permissions` | Skip all prompts |
| `--max-turns N` | Limit agentic turns |
| `--max-budget-usd N` | Spending cap |
| `--append-system-prompt "..."` | Extra instructions |
| `--allowedTools "tool1,tool2"` | Restrict to specific tools |
| `--disallowedTools "tool1"` | Block specific tools |

## Stream-JSON Output

When using `--output-format stream-json`, output is JSONL with types:
- `assistant` - Claude's response content
- `tool_use` - Tool being called
- `tool_result` - Tool output
- `result` - Final result with cost info

Example monitoring:
```bash
# Watch for results only
ssh adam@mac.local '...' | jq -c 'select(.type == "result")'

# Extract final cost
... | jq -r 'select(.type == "result") | .cost_usd'
```

## Requirements

- SSH access to Mac Studio: `ssh adam@mac.local`
- Claude Code at `/opt/homebrew/bin/claude`
- Authenticated on Mac Studio: `claude auth login`

## For Local Execution

Use the **code** skill instead:
```bash
~/.openclaw/workspace/skills/code/scripts/code.sh "<prompt>"
```

---
name: scode
description: Run Claude Code on Mac Studio via SSH. Use when you need to execute Claude Code CLI for coding tasks, code reviews, or running agents on the remote Mac Studio machine. For local execution, use 'code' skill instead.
---

# scode - Run Claude Code on Mac Studio

This skill executes Claude Code commands on Mac Studio via SSH.

## For Local Execution

Use the **code** skill instead (local Claude Code):
```bash
~/.openclaw/workspace/skills/code/scripts/code.sh "<prompt>"
```

Requirements:
- Claude Code installed locally
- Must be logged in: `claude auth login`

## Usage

```bash
ssh adam@mac.local '/opt/homebrew/bin/claude -p --dangerously-skip-permissions "[prompt]" -- ~/repos/[repo]'
```

## Examples

- Run a coding task: `claude -p --dangerously-skip-permissions "Add feature X to file.py"`
- Code review: `claude -p --dangerously-skip-permissions "Review this code for bugs"`
- Interactive: use `ssh -t` with `pty=true` for interactive sessions

## Requirements

- SSH access to Mac Studio (adam@mac.local)
- Claude Code installed at /opt/homebrew/bin/claude
- User must be logged in (`claude auth login` done on Mac Studio)

## Script

```bash
#!/bin/bash
# Run Claude Code on Mac Studio

REPO="${1:-}"
PROMPT="${2:-Hello}"

if [ -z "$REPO" ]; then
  echo "Usage: scode <repo> <prompt>"
  echo "Example: scode calc 'Add sin function'"
  exit 1
fi

ssh adam@mac.local "cd ~/repos/$REPO && /opt/homebrew/bin/claude -p --dangerously-skip-permissions '$PROMPT'"
```

---
name: code
description: Run Claude Code locally and as a background job. Use when you need to execute Claude Code CLI for coding tasks, code reviews, or running agents on the local machine. Requires Claude Code to be logged in (claude /login).
---

# code - Run Claude Code Locally

This skill executes Claude Code commands locally.

## Usage

```bash
claude -p --dangerously-skip-permissions "[prompt]"
```

## Examples

- Run a coding task: `claude -p --dangerously-skip-permissions "Add feature X to file.py"`
- Code review: `claude -p --dangerously-skip-permissions "Review this code for bugs"`
- Interactive: use `claude` for interactive session

## Requirements

- Claude Code installed locally (check: `which claude`)
- Must be logged in: `claude`
- If not logged in, run `claude /login` in a terminal with GUI

## Script

```bash
#!/bin/bash
# Run Claude Code locally

PROMPT="$1"

if [ -z "$PROMPT" ]; then
  echo "Usage: code '<prompt>'"
  echo "Example: code 'Add sin function to calc.py'"
  exit 1
fi

claude -p --dangerously-skip-permissions "$PROMPT"
```

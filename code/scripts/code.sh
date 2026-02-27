#!/bin/bash
# Run Claude Code locally

PROMPT="$1"

if [ -z "$PROMPT" ]; then
  echo "Usage: code '<prompt>'"
  echo "Example: code 'Add sin function to calc.py'"
  exit 1
fi

claude -p --dangerously-skip-permissions "$PROMPT"

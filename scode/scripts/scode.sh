#!/bin/bash
# Run Claude Code on Mac Studio via SSH

REPO="$1"
PROMPT="$2"

if [ -z "$REPO" ] || [ -z "$PROMPT" ]; then
  echo "Usage: scode <repo> <prompt>"
  echo "Example: scode calc 'Add sin function'"
  exit 1
fi

ssh adam@mac.local "cd ~/repos/$REPO && /opt/homebrew/bin/claude -p --dangerously-skip-permissions '$PROMPT'"

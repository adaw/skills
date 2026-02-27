#!/bin/bash
# Run Claude Code on Mac Studio via SSH

set -e

REMOTE="adam@mac.local"
CLAUDE="/opt/homebrew/bin/claude"
BG_MODE=false

usage() {
  echo "Usage: scode [-b] <repo> <prompt>"
  echo ""
  echo "Options:"
  echo "  -b    Background mode: run async, notify when done"
  echo ""
  echo "Examples:"
  echo "  scode calc 'Add sin function'"
  echo "  scode -b myproject 'Refactor auth module'"
  exit 1
}

# Parse flags
while getopts "b" opt; do
  case $opt in
    b) BG_MODE=true ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))

REPO="$1"
PROMPT="$2"

if [ -z "$REPO" ] || [ -z "$PROMPT" ]; then
  usage
fi

# Build the remote command
CMD="cd ~/repos/$REPO && $CLAUDE -p --output-format stream-json --dangerously-skip-permissions '$PROMPT'"

if [ "$BG_MODE" = true ]; then
  # Background mode: run async with logging and notification
  LOGFILE="/tmp/scode-$(date +%s).log"
  echo "Running in background, output: $LOGFILE"

  (
    ssh "$REMOTE" "$CMD" > "$LOGFILE" 2>&1
    EXIT_CODE=$?

    # Extract result from stream-json
    RESULT=$(grep '"type":"result"' "$LOGFILE" | tail -1 | jq -r '.cost_usd // "unknown"' 2>/dev/null || echo "unknown")

    if [ $EXIT_CODE -eq 0 ]; then
      osascript -e "display notification \"scode: $REPO completed (cost: \$$RESULT)\" with title \"Claude Code\""
    else
      osascript -e "display notification \"scode: $REPO failed (exit $EXIT_CODE)\" with title \"Claude Code\""
    fi
  ) &

  echo "PID: $!"
else
  # Foreground mode: stream output directly
  ssh "$REMOTE" "$CMD"
fi

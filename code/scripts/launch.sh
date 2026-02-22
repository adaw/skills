#!/usr/bin/env bash
# Claude Code Task Launcher
# Usage: ./launch.sh --prompt "task" [--workdir /path] [--model sonnet] [--max-turns 25] [--bg] [--readonly]
#
# Launches Claude Code with stream-json output and optional background mode.

set -euo pipefail

# Defaults
PROMPT=""
WORKDIR="$(pwd)"
MODEL=""
MAX_TURNS=25
BACKGROUND=false
READONLY=false
LOGFILE="/tmp/claude-code-run-$(date +%s).jsonl"
EXTRA_SYSTEM=""
EXTRA_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt|-p)
            PROMPT="$2"; shift 2 ;;
        --workdir|-w)
            WORKDIR="$2"; shift 2 ;;
        --model|-m)
            MODEL="$2"; shift 2 ;;
        --max-turns|-t)
            MAX_TURNS="$2"; shift 2 ;;
        --bg|--background)
            BACKGROUND=true; shift ;;
        --readonly)
            READONLY=true; shift ;;
        --log|-l)
            LOGFILE="$2"; shift 2 ;;
        --system|-s)
            EXTRA_SYSTEM="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 --prompt \"task\" [options]"
            echo ""
            echo "Options:"
            echo "  --prompt, -p    Task prompt (required)"
            echo "  --workdir, -w   Working directory (default: cwd)"
            echo "  --model, -m     Model: sonnet, opus, haiku (default: account default)"
            echo "  --max-turns, -t Maximum turns (default: 25)"
            echo "  --bg            Run in background"
            echo "  --readonly      Read-only mode (Grep, Glob, Read only)"
            echo "  --log, -l       Log file path (default: /tmp/claude-code-run-{ts}.jsonl)"
            echo "  --system, -s    Extra system prompt to append"
            exit 0
            ;;
        *)
            EXTRA_ARGS+=("$1"); shift ;;
    esac
done

if [ -z "$PROMPT" ]; then
    echo "Error: --prompt is required"
    exit 1
fi

# Verify claude is installed
if ! command -v claude &>/dev/null; then
    echo "Error: Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Build command
CMD=(claude -p "$PROMPT"
    --output-format stream-json
    --verbose
    --max-turns "$MAX_TURNS"
    --dangerously-skip-permissions
)

[ -n "$MODEL" ] && CMD+=(--model "$MODEL")

if [ "$READONLY" = true ]; then
    CMD+=(--allowedTools "Read,Grep,Glob,LS,WebSearch,WebFetch")
fi

# Add todo tracking instruction
TODO_NUDGE="Before starting, create a todo list using TodoWrite with all planned steps. Update status as you complete each step."
if [ -n "$EXTRA_SYSTEM" ]; then
    CMD+=(--append-system-prompt "${TODO_NUDGE} ${EXTRA_SYSTEM}")
else
    CMD+=(--append-system-prompt "$TODO_NUDGE")
fi

CMD+=("${EXTRA_ARGS[@]}")

# Execute
cd "$WORKDIR"

echo "╔═══════════════════════════════════════════════╗"
echo "║  🚀 Claude Code Task Launcher                ║"
echo "╠═══════════════════════════════════════════════╣"
echo "║  Workdir:  $WORKDIR"
echo "║  Model:    ${MODEL:-default}"
echo "║  Turns:    $MAX_TURNS"
echo "║  Readonly: $READONLY"
echo "║  Log:      $LOGFILE"
echo "║  Background: $BACKGROUND"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "Prompt: ${PROMPT:0:100}..."
echo ""

if [ "$BACKGROUND" = true ]; then
    "${CMD[@]}" > "$LOGFILE" 2>&1 &
    PID=$!
    echo "✅ Started in background (PID: $PID)"
    echo ""
    echo "Monitor progress:"
    echo "  $(dirname "$0")/monitor.sh $LOGFILE --watch"
    echo ""
    echo "Or quick check:"
    echo "  tail -f $LOGFILE | jq -r '.message.content[]?.text // .message.content[]?.name // empty'"
    echo ""
    echo "PID file: /tmp/claude-code-run.pid"
    echo "$PID" > /tmp/claude-code-run.pid
else
    "${CMD[@]}" 2>&1 | tee "$LOGFILE"
    
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "Run complete. Full log: $LOGFILE"
    echo ""
    echo "Summary:"
    tail -1 "$LOGFILE" | jq '{
        success: (.subtype == "success"),
        cost: .total_cost_usd,
        duration_sec: ((.duration_ms // 0) / 1000 | floor),
        turns: .num_turns,
        result_preview: (.result // "" | .[0:200])
    }' 2>/dev/null || echo "(unable to parse result)"
fi

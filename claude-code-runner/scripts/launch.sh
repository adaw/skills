#!/usr/bin/env bash
# Claude Code Task Launcher
# Usage: ./launch.sh --prompt "task" [--workdir /path] [--model sonnet] [--max-turns 25] [--bg] [--readonly]
#
# Launches Claude Code with stream-json output and optional background mode.

set -euo pipefail

# Defaults
PROMPT=""
WORKDIR=""
WORKDIR_AUTO=false
MODEL=""
MODEL_ID=""
MAX_TURNS=25
BACKGROUND=false
READONLY=false
LOGFILE="/tmp/claude-code-run-$(date +%s).jsonl"
EXTRA_SYSTEM=""
EXTRA_ARGS=()
AUTO_PUSH=false
BRANCH=""
REPOS_DIR="$HOME/repos"

# Model mapping
declare -A MODEL_MAP=(
    ["opus"]="claude-opus-4-6"
    ["sonnet"]="claude-sonnet-4-6"
    ["minimax"]="openrouter/minimax/minimax-01"
)

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
        --push)
            AUTO_PUSH=true; shift ;;
        --branch|-b)
            BRANCH="$2"; shift 2 ;;
        --repo|-r)
            # Auto-find repo in ~/repos/
            REPO_NAME="$2"
            if [ -d "$REPOS_DIR/$REPO_NAME" ]; then
                WORKDIR="$REPOS_DIR/$REPO_NAME"
                WORKDIR_AUTO=true
            else
                echo "Error: Repository '$REPO_NAME' not found in $REPOS_DIR/"
                echo "Available repos:"
                ls -1 "$REPOS_DIR/" 2>/dev/null | head -10
                exit 1
            fi
            shift 2 ;;
        --help|-h)
            echo "Usage: $0 --prompt \"task\" [options]"
            echo ""
            echo "Options:"
            echo "  --prompt, -p    Task prompt (required)"
            echo "  --workdir, -w   Working directory (default: cwd)"
            echo "  --repo, -r      Auto-find repo in ~/repos/ by name"
            echo "  --model, -m     Model: sonnet, opus, minimax (default: sonnet)"
            echo "  --max-turns, -t Maximum turns (default: 25)"
            echo "  --bg            Run in background with live progress"
            echo "  --readonly      Read-only mode (Grep, Glob, Read only)"
            echo "  --log, -l       Log file path (default: /tmp/claude-code-run-{ts}.jsonl)"
            echo "  --system, -s    Extra system prompt to append"
            echo "  --push          Auto git add/commit/push after completion"
            echo "  --branch, -b    Git branch to use (creates if new)"
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

# Set default workdir if not specified
[ -z "$WORKDIR" ] && WORKDIR="$(pwd)"

# Resolve model to model ID
if [ -n "$MODEL" ]; then
    MODEL_ID="${MODEL_MAP[$MODEL]:-$MODEL}"
fi

# Default model if none specified
[ -z "$MODEL_ID" ] && MODEL_ID="claude-sonnet-4-6"

# Verify claude is installed
if ! command -v claude &>/dev/null; then
    echo "Error: Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Handle branch management
if [ -n "$BRANCH" ]; then
    cd "$WORKDIR"
    # Check if branch exists
    if git rev-parse --verify "$BRANCH" &>/dev/null; then
        echo "Switching to existing branch: $BRANCH"
        git checkout "$BRANCH"
    elif git rev-parse --verify "origin/$BRANCH" &>/dev/null; then
        echo "Checking out remote branch: $BRANCH"
        git checkout -b "$BRANCH" "origin/$BRANCH"
    else
        echo "Creating new branch: $BRANCH"
        git checkout -b "$BRANCH"
    fi
fi

# Build command
CMD=(claude -p "$PROMPT"
    --output-format stream-json
    --verbose
    --max-turns "$MAX_TURNS"
    --dangerously-skip-permissions
    --model "$MODEL_ID"
)

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
echo "║  Model:    $MODEL_ID"
echo "║  Turns:    $MAX_TURNS"
echo "║  Readonly: $READONLY"
echo "║  Log:      $LOGFILE"
echo "║  Background: $BACKGROUND"
echo "║  Auto-push: $AUTO_PUSH"
[ -n "$BRANCH" ] && echo "║  Branch:   $BRANCH"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "Prompt: ${PROMPT:0:100}..."
echo ""

# Function to handle auto-push after completion
do_auto_push() {
    local logfile="$1"
    local workdir="$2"

    cd "$workdir"

    # Extract task summary from prompt (first 50 chars)
    local summary="${PROMPT:0:50}"
    summary="${summary//[$'\n\r']/ }"  # Remove newlines

    # Check if there are changes to commit
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo "📦 Auto-committing changes..."
        git add -A
        git commit -m "cc: $summary" || true

        echo "🚀 Pushing to remote..."
        git push -u origin HEAD 2>&1 || echo "⚠️  Push failed (check remote)"
        echo "✅ Auto-push complete"
    else
        echo "ℹ️  No changes to commit"
    fi
}

# Function for live progress monitoring (runs in background)
live_progress_monitor() {
    local logfile="$1"
    local pid="$2"
    local last_hash=""

    while kill -0 "$pid" 2>/dev/null; do
        sleep 5

        # Check for TodoWrite updates
        local todo_line
        todo_line=$(tac "$logfile" 2>/dev/null | grep -m1 'TodoWrite' || echo "")

        if [ -n "$todo_line" ]; then
            local current_hash
            current_hash=$(echo "$todo_line" | md5sum | cut -d' ' -f1)

            if [ "$current_hash" != "$last_hash" ]; then
                last_hash="$current_hash"
                echo ""
                echo "━━━ 📋 Progress Update ($(date +%H:%M:%S)) ━━━"
                echo "$todo_line" | jq -r '
                    .message.content[]? | select(.name=="TodoWrite") | .input.todos[]? |
                    if .status == "completed" then "  ✅ \(.content)"
                    elif .status == "in_progress" then "  🔧 \(.content)"
                    else "  ⏳ \(.content)"
                    end
                ' 2>/dev/null

                # Count progress
                local completed total
                completed=$(echo "$todo_line" | jq '[.message.content[]? | select(.name=="TodoWrite") | .input.todos[]? | select(.status=="completed")] | length' 2>/dev/null || echo "0")
                total=$(echo "$todo_line" | jq '[.message.content[]? | select(.name=="TodoWrite") | .input.todos[]?] | length' 2>/dev/null || echo "0")
                echo "  📊 Progress: $completed/$total tasks"
            fi
        fi
    done
}

if [ "$BACKGROUND" = true ]; then
    "${CMD[@]}" > "$LOGFILE" 2>&1 &
    PID=$!
    echo "✅ Started in background (PID: $PID)"
    echo ""
    echo "PID file: /tmp/claude-code-run.pid"
    echo "$PID" > /tmp/claude-code-run.pid

    # Start live progress monitor in background
    live_progress_monitor "$LOGFILE" "$PID" &
    MONITOR_PID=$!

    # Set up completion handler
    (
        wait $PID
        EXIT_CODE=$?

        # Kill monitor
        kill $MONITOR_PID 2>/dev/null || true

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🏁 Claude Code finished (exit code: $EXIT_CODE)"

        # Show final result
        tail -1 "$LOGFILE" | jq '{
            success: (.subtype == "success"),
            cost: .total_cost_usd,
            duration_sec: ((.duration_ms // 0) / 1000 | floor),
            turns: .num_turns
        }' 2>/dev/null || echo "(unable to parse result)"

        # Auto-push if enabled
        if [ "$AUTO_PUSH" = true ]; then
            do_auto_push "$LOGFILE" "$WORKDIR"
        fi
    ) &

    echo "Monitor progress:"
    echo "  $(dirname "$0")/monitor.sh $LOGFILE --watch"
    echo ""
    echo "Or quick check:"
    echo "  tail -f $LOGFILE | jq -r '.message.content[]?.text // .message.content[]?.name // empty'"
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

    # Auto-push if enabled
    if [ "$AUTO_PUSH" = true ]; then
        do_auto_push "$LOGFILE" "$WORKDIR"
    fi
fi

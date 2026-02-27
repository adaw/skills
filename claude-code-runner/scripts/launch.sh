#!/usr/bin/env bash
# Claude Code Task Launcher
# Usage: ./launch.sh --prompt "task" [--workdir /path] [--model opus] [--max-turns 25] [--bg] [--readonly]
#        ./launch.sh --prompt "task" --review    (readonly + sonnet + review focus)
#        ./launch.sh --resume /path/to/log.jsonl --prompt "continue with..."
#        ./launch.sh --template fix-bugs
#
# Launches Claude Code with stream-json output. Background mode by default.

set -euo pipefail

# Defaults
PROMPT=""
WORKDIR=""
WORKDIR_AUTO=false
MODEL=""
MODEL_ID=""
MAX_TURNS=25
BACKGROUND=true
READONLY=false
REVIEW_MODE=false
RESUME_LOG=""
TEMPLATE=""
LOGFILE="/tmp/claude-code-run-$(date +%s).jsonl"
EXTRA_SYSTEM=""
EXTRA_ARGS=()
AUTO_PUSH=false
BRANCH=""
REPOS_DIR="$HOME/repos"
TELEGRAM_CHAT_ID="7729677048"

# Model mapping
declare -A MODEL_MAP=(
    ["opus"]="claude-opus-4-6"
    ["sonnet"]="claude-sonnet-4-6"
    ["minimax"]="openrouter/minimax/minimax-01"
)

# Prompt templates
declare -A TEMPLATES=(
    ["fix-bugs"]="Review the codebase, find all bugs, fix them. Run tests after each fix."
    ["add-tests"]="Add comprehensive tests for all untested functions. Run tests to verify."
    ["refactor"]="Refactor the codebase for clarity, performance, and maintainability."
    ["review"]="Do a thorough code review. Report bugs, security issues, code smells."
    ["docs"]="Add/improve documentation, docstrings, and README."
)

# ── Telegram notify ──────────────────────────────────────────────
send_telegram() {
    local msg="$1"
    local token
    token=$(cat ~/.openclaw/credentials/telegram-token 2>/dev/null || echo "")
    [ -z "$token" ] && return 0
    curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$msg" \
        -d parse_mode="Markdown" >/dev/null 2>&1 || true
}

# ── Refresh ~/.claude/CLAUDE.md with current skills + tools ──────
refresh_claude_context() {
    local claude_md="$HOME/.claude/CLAUDE.md"
    mkdir -p "$HOME/.claude"

    {
        echo "# CLAUDE.md — Auto-generated context for Claude Code"
        echo "# Regenerated on: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# Do not edit manually — managed by claude-code-runner/launch.sh"
        echo ""
        echo "## Available Skills"
        echo ""
        echo "Skills installed in ~/.openclaw/workspace/skills/:"
        echo ""
        for d in "$HOME/.openclaw/workspace/skills"/*/; do
            [ -d "$d" ] || continue
            local name desc
            name=$(basename "$d")
            desc=$(awk '/^---/{n++; next} n==1 && /^description:/{sub(/^description: *>? */,""); if(length>5){print; exit} else {getline; gsub(/^ +/,""); print; exit}}' "$d/SKILL.md" 2>/dev/null)
            [ -z "$desc" ] && desc=$(awk '/^description:/{found=1; next} found{gsub(/^ +/,""); print; exit}' "$d/SKILL.md" 2>/dev/null)
            [ -z "$desc" ] && desc="(no description)"
            echo "- **${name}**: ${desc}"
        done
        echo ""
        echo "## Available Tools"
        echo ""
        echo "### Scripts in ~/tools/lex/scripts/"
        echo ""
        for f in "$HOME/tools/lex/scripts"/*; do
            [ -f "$f" ] || continue
            local fname
            fname=$(basename "$f")
            [[ "$fname" == __pycache__ ]] && continue
            echo "- ${fname}"
        done
        echo ""
        echo "### Key CLI tools"
        echo ""
        echo "- **imsg**: iMessage CLI — \`imsg send --to \"+420...\" --text \"msg\"\` or \`--file /path\`"
        echo "- **blogwatcher**: RSS feed monitor — \`blogwatcher scan\`, \`blogwatcher articles\`"
        echo "- **remindctl**: Apple Reminders CLI — \`remindctl add \"task\" --list Work\`"
        echo "- **memo**: Apple Notes CLI — \`memo create \"title\" --body \"text\"\`"
        echo "- **comfyui-gen.py**: FLUX image generation — \`ssh adam@mac.local \"python3 ~/tools/lex/scripts/comfyui-gen.py 'prompt' --model flux2\"\`"
        echo "- **himalaya**: Email CLI (iCloud) — \`himalaya list\`, \`himalaya send\`"
        echo ""
        echo "## Workspace"
        echo ""
        echo "- **Home**: ~/.openclaw/workspace/"
        echo "- **Skills**: ~/repos/skills/ (symlinked to ~/.openclaw/workspace/skills/)"
        echo "- **Tools**: ~/tools/lex/ (git repo with scripts, hooks, integrations)"
        echo "- **Repos**: ~/repos/"
    } > "$claude_md"
}

# ── Parse arguments ──────────────────────────────────────────────
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
        --no-bg|--foreground)
            BACKGROUND=false; shift ;;
        --readonly)
            READONLY=true; shift ;;
        --review)
            REVIEW_MODE=true; READONLY=true; shift ;;
        --resume)
            RESUME_LOG="$2"; shift 2 ;;
        --template)
            TEMPLATE="$2"; shift 2 ;;
        --log|-l)
            LOGFILE="$2"; shift 2 ;;
        --system|-s)
            EXTRA_SYSTEM="$2"; shift 2 ;;
        --push)
            AUTO_PUSH=true; shift ;;
        --branch|-b)
            BRANCH="$2"; shift 2 ;;
        --repo|-r)
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
            echo "  --prompt, -p    Task prompt (required, unless --template)"
            echo "  --workdir, -w   Working directory (default: cwd)"
            echo "  --repo, -r      Auto-find repo in ~/repos/ by name"
            echo "  --model, -m     Model: opus (default), sonnet, minimax"
            echo "  --max-turns, -t Maximum turns (default: 25)"
            echo "  --bg            Run in background (default: true)"
            echo "  --no-bg         Run in foreground"
            echo "  --readonly      Read-only mode (Grep, Glob, Read only)"
            echo "  --review        Review mode: readonly + sonnet + review focus"
            echo "  --resume FILE   Resume from a previous run's JSONL log"
            echo "  --template NAME Prompt template: fix-bugs, add-tests, refactor, review, docs"
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

# ── Template handling ────────────────────────────────────────────
if [ -n "$TEMPLATE" ]; then
    tpl_prompt="${TEMPLATES[$TEMPLATE]:-}"
    if [ -z "$tpl_prompt" ]; then
        echo "Error: Unknown template '$TEMPLATE'. Available: ${!TEMPLATES[*]}"
        exit 1
    fi
    if [ -z "$PROMPT" ]; then
        PROMPT="$tpl_prompt"
    else
        PROMPT="${tpl_prompt} ${PROMPT}"
    fi
fi

# ── Review mode overrides ───────────────────────────────────────
if [ "$REVIEW_MODE" = true ]; then
    [ -z "$MODEL" ] && MODEL="sonnet"
    EXTRA_SYSTEM="Focus on code quality, bugs, security issues, performance problems, and code smells. ${EXTRA_SYSTEM}"
fi

# ── Resume handling ──────────────────────────────────────────────
if [ -n "$RESUME_LOG" ]; then
    if [ ! -f "$RESUME_LOG" ]; then
        echo "Error: Resume log not found: $RESUME_LOG"
        exit 1
    fi
    RESUME_CONTEXT=$(tac "$RESUME_LOG" | grep -m1 '"text"' | jq -r '.message.content[]?.text // empty' 2>/dev/null | head -c 2000)
    if [ -n "$RESUME_CONTEXT" ]; then
        PROMPT="Continue from where you left off. Last context:
---
${RESUME_CONTEXT}
---
${PROMPT:-Continue the task.}"
    fi
    echo "📎 Resuming from: $RESUME_LOG"
fi

if [ -z "$PROMPT" ]; then
    echo "Error: --prompt is required (or use --template)"
    exit 1
fi

# Set default workdir if not specified
[ -z "$WORKDIR" ] && WORKDIR="$(pwd)"

# Resolve model to model ID
if [ -n "$MODEL" ]; then
    MODEL_ID="${MODEL_MAP[$MODEL]:-$MODEL}"
fi

# Default model: opus
[ -z "$MODEL_ID" ] && MODEL_ID="claude-opus-4-6"

# Verify claude is installed
if ! command -v claude &>/dev/null; then
    echo "Error: Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# ── Refresh CLAUDE.md context ────────────────────────────────────
refresh_claude_context

# Handle branch management
if [ -n "$BRANCH" ]; then
    cd "$WORKDIR"
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

# Build system prompt
SYSTEM_PARTS="Before starting, create a todo list using TodoWrite with all planned steps. Update status as you complete each step."
[ -n "$EXTRA_SYSTEM" ] && SYSTEM_PARTS="${SYSTEM_PARTS} ${EXTRA_SYSTEM}"

CMD+=(--append-system-prompt "$SYSTEM_PARTS")
CMD+=("${EXTRA_ARGS[@]}")

# Execute
cd "$WORKDIR"

echo "╔═══════════════════════════════════════════════╗"
echo "║  🚀 Claude Code Task Launcher                ║"
echo "╠═══════════════════════════════════════════════╣"
echo "║  Workdir:    $WORKDIR"
echo "║  Model:      $MODEL_ID"
echo "║  Turns:      $MAX_TURNS"
echo "║  Readonly:   $READONLY"
echo "║  Review:     $REVIEW_MODE"
echo "║  Log:        $LOGFILE"
echo "║  Background: $BACKGROUND"
echo "║  Auto-push:  $AUTO_PUSH"
[ -n "$BRANCH" ] && echo "║  Branch:     $BRANCH"
[ -n "$TEMPLATE" ] && echo "║  Template:   $TEMPLATE"
[ -n "$RESUME_LOG" ] && echo "║  Resume:     $RESUME_LOG"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "Prompt: ${PROMPT:0:100}..."
echo ""

# Function to handle auto-push after completion
do_auto_push() {
    local logfile="$1"
    local workdir="$2"

    cd "$workdir"

    local summary="${PROMPT:0:50}"
    summary="${summary//[$'\n\r']/ }"

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

    # Set up completion handler with telegram notification
    (
        wait $PID
        EXIT_CODE=$?

        # Kill monitor
        kill $MONITOR_PID 2>/dev/null || true

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🏁 Claude Code finished (exit code: $EXIT_CODE)"

        # Parse result
        RESULT_JSON=$(tail -1 "$LOGFILE" | jq '{
            success: (.subtype == "success"),
            cost: .total_cost_usd,
            duration_sec: ((.duration_ms // 0) / 1000 | floor),
            turns: .num_turns
        }' 2>/dev/null || echo '{}')
        echo "$RESULT_JSON"

        # Extract values for notification
        success=$(echo "$RESULT_JSON" | jq -r '.success // false')
        turns=$(echo "$RESULT_JSON" | jq -r '.turns // "?"')
        cost=$(echo "$RESULT_JSON" | jq -r '.cost // "?"')
        duration=$(echo "$RESULT_JSON" | jq -r '.duration_sec // "?"')
        task_summary="${PROMPT:0:80}"
        task_summary="${task_summary//[$'\n\r']/ }"

        if [ "$success" = "true" ]; then
            status_emoji="✅"
            status_text="SUCCESS"
        else
            status_emoji="❌"
            status_text="FAILED"
        fi

        send_telegram "${status_emoji} *CC ${status_text}*
📝 ${task_summary}
🔄 Turns: ${turns} | 💰 \$${cost} | ⏱ ${duration}s
📄 \`${LOGFILE}\`"

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

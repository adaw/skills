#!/usr/bin/env bash
# Claude Code Run Monitor
# Usage: ./monitor.sh [logfile] [--watch]
#
# Parses stream-json JSONL output from Claude Code and displays
# structured progress updates.

set -euo pipefail

LOGFILE="${1:-/tmp/claude-code-run.jsonl}"
WATCH_MODE="${2:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo -e "${BOLD}═══════════════════════════════════════════${NC}"
    echo -e "${BOLD}  🤖 Claude Code Run Monitor${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════${NC}"
    echo -e "  Log: ${CYAN}${LOGFILE}${NC}"
    echo ""
}

get_status() {
    local last_line
    last_line=$(tail -1 "$LOGFILE" 2>/dev/null || echo "")
    
    if echo "$last_line" | jq -e '.type == "result"' >/dev/null 2>&1; then
        local subtype
        subtype=$(echo "$last_line" | jq -r '.subtype // "unknown"')
        if [ "$subtype" = "success" ]; then
            echo -e "${GREEN}✅ COMPLETED${NC}"
        else
            echo -e "${RED}❌ FAILED${NC}"
        fi
    else
        echo -e "${YELLOW}🔄 RUNNING${NC}"
    fi
}

get_result_stats() {
    local last_line
    last_line=$(tail -1 "$LOGFILE" 2>/dev/null || echo "")
    
    if echo "$last_line" | jq -e '.type == "result"' >/dev/null 2>&1; then
        local cost duration turns
        cost=$(echo "$last_line" | jq -r '.total_cost_usd // "?"')
        duration=$(echo "$last_line" | jq -r '(.duration_ms // 0) / 1000 | floor')
        turns=$(echo "$last_line" | jq -r '.num_turns // "?"')
        echo -e "  ⏱️  Duration: ${BOLD}${duration}s${NC} | 💰 Cost: ${BOLD}\$${cost}${NC} | 🔄 Turns: ${BOLD}${turns}${NC}"
    fi
}

get_todo_progress() {
    local todo_line
    todo_line=$(tac "$LOGFILE" 2>/dev/null | grep -m1 'TodoWrite' || echo "")
    
    if [ -z "$todo_line" ]; then
        echo -e "  ${CYAN}(no todo list created yet)${NC}"
        return
    fi
    
    # Parse todos
    echo "$todo_line" | jq -r '
        .message.content[]? | select(.name=="TodoWrite") | .input.todos[]? |
        if .status == "completed" then "  ✅ \(.content)"
        elif .status == "in_progress" then "  🔧 \(.content) (in progress)"
        else "  ⏳ \(.content)"
        end
    ' 2>/dev/null || echo -e "  ${CYAN}(unable to parse todos)${NC}"
    
    # Summary counts
    local completed total
    completed=$(echo "$todo_line" | jq '[.message.content[]? | select(.name=="TodoWrite") | .input.todos[]? | select(.status=="completed")] | length' 2>/dev/null || echo "0")
    total=$(echo "$todo_line" | jq '[.message.content[]? | select(.name=="TodoWrite") | .input.todos[]?] | length' 2>/dev/null || echo "0")
    echo ""
    echo -e "  📊 Progress: ${BOLD}${completed}/${total}${NC} tasks completed"
}

get_file_operations() {
    local ops
    ops=$(jq -r '
        .message.content[]? | 
        select(.name == "Write" or .name == "Edit") | 
        "\(.name): \(.input.file_path // .input.file // "unknown")"
    ' "$LOGFILE" 2>/dev/null | sort -u)
    
    if [ -n "$ops" ]; then
        local count
        count=$(echo "$ops" | wc -l | tr -d ' ')
        echo -e "  📁 Files modified (${count}):"
        echo "$ops" | while read -r line; do
            local op file
            op=$(echo "$line" | cut -d: -f1)
            file=$(echo "$line" | cut -d: -f2- | xargs)
            if [ "$op" = "Write" ]; then
                echo -e "    ${GREEN}+ ${file}${NC}"
            else
                echo -e "    ${YELLOW}~ ${file}${NC}"
            fi
        done
    else
        echo -e "  📁 No file operations yet"
    fi
}

get_recent_activity() {
    echo -e "  📝 Recent activity:"
    tail -20 "$LOGFILE" 2>/dev/null | jq -r '
        .message.content[]? | 
        if .type == "text" then .text
        elif .name then "🔧 Using tool: \(.name)"
        else empty
        end
    ' 2>/dev/null | tail -5 | while read -r line; do
        # Truncate long lines
        if [ ${#line} -gt 80 ]; then
            echo -e "    ${line:0:77}..."
        else
            echo -e "    ${line}"
        fi
    done
}

get_errors() {
    local errors
    errors=$(grep -i '"error"' "$LOGFILE" 2>/dev/null | head -3)
    if [ -n "$errors" ]; then
        echo -e "\n  ${RED}⚠️  Errors detected:${NC}"
        echo "$errors" | jq -r '.error // .message // .' 2>/dev/null | head -3 | while read -r line; do
            echo -e "    ${RED}${line:0:80}${NC}"
        done
    fi
}

show_report() {
    clear 2>/dev/null || true
    print_header
    
    if [ ! -f "$LOGFILE" ]; then
        echo -e "  ${RED}Log file not found: ${LOGFILE}${NC}"
        echo -e "  Waiting for Claude Code to start..."
        return
    fi
    
    local lines
    lines=$(wc -l < "$LOGFILE" 2>/dev/null || echo "0")
    
    echo -e "  Status: $(get_status)"
    echo -e "  Lines processed: ${lines}"
    get_result_stats
    echo ""
    
    echo -e "${BOLD}📋 Task Progress:${NC}"
    get_todo_progress
    echo ""
    
    echo -e "${BOLD}📂 File Operations:${NC}"
    get_file_operations
    echo ""
    
    echo -e "${BOLD}📜 Activity Log:${NC}"
    get_recent_activity
    
    get_errors
    
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════${NC}"
}

# Main
if [ "$WATCH_MODE" = "--watch" ] || [ "$WATCH_MODE" = "-w" ]; then
    echo "Watching $LOGFILE (Ctrl+C to stop)..."
    while true; do
        show_report
        sleep 3
    done
else
    show_report
fi

#!/usr/bin/env bash
# fabric-score.sh — Deterministický checker K1-K10 pro fabric skills
# Nahrazuje nestabilní LLM-based scoring stabilním grep-based auditem.
#
# Použití: bash scripts/fabric-score.sh [target=<skill_name>]
#
# Každý K má jasně definované grep patterny. Skill buď pattern MÁ (10b) nebo NEMÁ (0b).
# Pro některé K existuje "N/A" (neaplikuje se) — skill dostane plné body.

set -euo pipefail

SKILLS_ROOT="skills"
TARGET="${1:-}"  # optional: target=implement → only score fabric-implement

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

# Tier classification
classify_tier() {
  local name="$1"
  case "$name" in
    fabric-loop|fabric-init) echo "T1" ;;
    fabric-checker|fabric-builder) echo "SKIP" ;;
    *)
      if grep -q 'built from: builder-template' "$SKILLS_ROOT/$name/SKILL.md" 2>/dev/null; then
        echo "T2"
      else
        echo "T3"
      fi
      ;;
  esac
}

# Check if skill uses git operations
uses_git() {
  local file="$1"
  grep -qE 'git (commit|push|merge|rebase|checkout|branch|cherry-pick|reset|stash|pull|clone|fetch|add |tag )' "$file" 2>/dev/null
}

# Count matches (returns count)
count_matches() {
  local file="$1"
  local pattern="$2"
  grep -cE "$pattern" "$file" 2>/dev/null || echo "0"
}

# Has match (returns 0=yes, 1=no)
has_match() {
  local file="$1"
  local pattern="$2"
  grep -qEi "$pattern" "$file" 2>/dev/null
}

# Score one skill
score_skill() {
  local skill_name="$1"
  local file="$SKILLS_ROOT/$skill_name/SKILL.md"
  local tier
  tier=$(classify_tier "$skill_name")

  if [ "$tier" = "SKIP" ]; then
    echo "SKIP|$skill_name|---|meta skill (checker/builder)"
    return
  fi

  if [ ! -f "$file" ]; then
    echo "ERROR|$skill_name|0|file not found"
    return
  fi

  local k1=0 k2=0 k3=0 k4=0 k5=0 k6=0 k7=0 k8=0 k9=0 k10=0
  local k4_na=0
  local notes=""

  # === K1: State Machine (10b) ===
  # Must reference state.md OR phase/step management
  if has_match "$file" 'state\.md|state\.step|state\.phase|CURRENT_PHASE|state_patch|state-get|state-patch'; then
    k1=10
  elif has_match "$file" 'phase:|step:|state machine|orchestr'; then
    k1=7
  fi

  # === K2: Counter & Termination (10b) ===
  # Must have MAX_* limits OR explicit termination for loops, OR N/A for non-loop skills
  # Note: "loop" in text often refers to fabric-loop (the orchestrator), not an actual loop construct.
  # We look for actual loop constructs: REPEAT, while, for each, iterace (Czech), or MAX_* guards.
  # First: check for ACTUAL unbounded loop constructs
  local has_unbounded=0
  has_match "$file" '^REPEAT\b|^  REPEAT\b|^UNTIL:' && has_unbounded=1
  has_match "$file" 'while \[' && has_unbounded=1
  has_match "$file" 'while true|while :' && has_unbounded=1
  has_match "$file" 'iterací|opakuj.*dokud' && has_unbounded=1
  # Note: "| while read" is pipe-bounded → NOT unbounded
  # Note: "for X in FILES" is filesystem-bounded → NOT unbounded

  if [ $has_unbounded -eq 1 ]; then
    # Has unbounded loops — must have MAX_* guards for full score
    if has_match "$file" 'MAX_|max_loops|max_ticks|max_rework|max_iterations|max_tasks|LOOP_COUNT|loop_limit'; then
      k2=10
    elif has_match "$file" 'terminat|bounded|finite|counter.*limit|limit.*counter'; then
      k2=7
    fi
    # else k2 stays 0
  else
    # No unbounded loops → N/A → full score
    k2=10
  fi
  # Numeric validation bonus check
  if has_match "$file" "grep -qE.*\[0-9\]|numeric.*valid|counter.*valid"; then
    : # already scored
  fi

  # === K3: Error Handling (10b) ===
  # Must have STOP conditions + error/fallback handling
  local err_count
  err_count=$(count_matches "$file" 'STOP|error|WARN:|fallback|exit 1|\|\| echo|set -e')
  if [ "$err_count" -ge 5 ]; then
    k3=10
  elif [ "$err_count" -ge 2 ]; then
    k3=7
  elif [ "$err_count" -ge 1 ]; then
    k3=4
  fi

  # === K4: Git Safety (10b) ===
  if uses_git "$file"; then
    # Must have quoted variables in git commands
    if has_match "$file" '"\$\{|"\$[A-Z]'; then
      k4=10
    elif has_match "$file" 'git.*\$'; then
      k4=5  # uses vars but maybe unquoted
    fi
  else
    # N/A — no git operations
    k4=10
    k4_na=1
  fi

  # === K5: Contracts & Config (10b) ===
  # Must reference config.md or {WORK_ROOT}
  if has_match "$file" 'config\.md|\{WORK_ROOT\}|\{CODE_ROOT\}|CONTRACTS|COMMANDS\.|LIFECYCLE'; then
    k5=10
  elif has_match "$file" 'config|contract'; then
    k5=5
  fi

  # === K6: Temporal Causality / Preconditions (10b) ===
  # Must have bash precondition checks (test -f, test -d, [ -f, [ ! -f)
  local precond_count
  precond_count=$(count_matches "$file" 'test -[fd]|test !|\[ -[fd]|\[ ! -[fd]|if \[.*-[fd]|Precondition|precondition|STOP:.*first|STOP:.*missing|STOP:.*not found')
  if [ "$precond_count" -ge 3 ]; then
    k6=10
  elif [ "$precond_count" -ge 1 ]; then
    k6=7
  fi

  # === K7: Input Validation (10b) ===
  # Must have path traversal prevention OR numeric guards OR parameter validation
  if has_match "$file" 'validate_path|\.\./|path.*traversal|path.*valid'; then
    k7=10
  elif has_match "$file" "grep -qE.*\[0-9\]|numeric.*guard|clamp|range.*valid|input.*valid"; then
    k7=7
  elif has_match "$file" 'validat|sanitiz|reject.*invalid'; then
    k7=5
  fi

  # === K8: Audit & Governance (10b) ===
  # Must have protocol logging + report with schema frontmatter
  local audit_score=0
  if has_match "$file" 'protocol_log|protocol\.jsonl|Protokol|START.*END|event start|event end'; then
    audit_score=$((audit_score + 5))
  fi
  if has_match "$file" 'schema:.*fabric\.|frontmatter|report.*schema|kind:'; then
    audit_score=$((audit_score + 5))
  fi
  k8=$audit_score

  # === K9: Self-Check (10b) ===
  # Must have Self-check section with testable items
  if has_match "$file" 'Self-check|self-check|Self check'; then
    local check_items
    check_items=$(grep -cE -- '- \[|ověř|existuje|PASS|invariant|Existence|Quality|Invariant' "$file" 2>/dev/null || echo "0")
    if [ "$check_items" -ge 3 ]; then
      k9=10
    elif [ "$check_items" -ge 1 ]; then
      k9=7
    else
      k9=5  # section exists but few items
    fi
  fi

  # === K10: Documentation & Work Quality (10b) ===
  local wq_score=0
  # Has examples/templates
  if has_match "$file" 'Příklad|příklad|Example|example|Šablona|šablona|Template|```'; then
    wq_score=$((wq_score + 3))
  fi
  # Has anti-patterns
  if has_match "$file" 'ANTI-PATTERN|anti-pattern|Anti-pattern|ZAKÁZÁNO|zakázáno|nesmí|NESMÍ'; then
    wq_score=$((wq_score + 3))
  fi
  # Has minimum/acceptance criteria
  if has_match "$file" 'MINIMUM|minimum|akceptovatel|acceptance|MUSÍ.*obsahovat|musí.*mít'; then
    wq_score=$((wq_score + 2))
  fi
  # Is concrete (has bash code blocks)
  local code_blocks
  code_blocks=$(count_matches "$file" '```bash')
  if [ "$code_blocks" -ge 2 ]; then
    wq_score=$((wq_score + 2))
  elif [ "$code_blocks" -ge 1 ]; then
    wq_score=$((wq_score + 1))
  fi
  k10=$wq_score
  if [ $k10 -gt 10 ]; then k10=10; fi

  # Calculate total
  local total=$((k1 + k2 + k3 + k4 + k5 + k6 + k7 + k8 + k9 + k10))
  local max=100
  # If K4 is N/A, max is 90 (we gave full points already, so percentage is from 100)

  # Build detail string
  local detail="K1=$k1 K2=$k2 K3=$k3 K4=$k4"
  [ $k4_na -eq 1 ] && detail="$detail(N/A)"
  detail="$detail K5=$k5 K6=$k6 K7=$k7 K8=$k8 K9=$k9 K10=$k10"

  # Find weak categories (< 10)
  local weak=""
  [ $k1 -lt 10 ] && weak="$weak K1($k1)"
  [ $k2 -lt 10 ] && weak="$weak K2($k2)"
  [ $k3 -lt 10 ] && weak="$weak K3($k3)"
  [ $k4 -lt 10 ] && [ $k4_na -eq 0 ] && weak="$weak K4($k4)"
  [ $k5 -lt 10 ] && weak="$weak K5($k5)"
  [ $k6 -lt 10 ] && weak="$weak K6($k6)"
  [ $k7 -lt 10 ] && weak="$weak K7($k7)"
  [ $k8 -lt 10 ] && weak="$weak K8($k8)"
  [ $k9 -lt 10 ] && weak="$weak K9($k9)"
  [ $k10 -lt 10 ] && weak="$weak K10($k10)"

  echo "$tier|$skill_name|$total|$detail|$weak"
}

# Main
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  FABRIC DETERMINISTIC CHECKER — K1-K10 Structural Scoring      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Date: $(date +%Y-%m-%d)"
echo ""

# Collect all skills
SKILLS=()
for dir in "$SKILLS_ROOT"/fabric-*/; do
  name=$(basename "$dir")
  if [ -n "$TARGET" ]; then
    target_name="${TARGET#target=}"
    if [ "$name" != "fabric-$target_name" ] && [ "$name" != "$target_name" ]; then
      continue
    fi
  fi
  SKILLS+=("$name")
done

# Header
printf "%-4s | %-20s | %5s | %-60s | %s\n" "Tier" "Skill" "Score" "Detail" "Weak"
printf "%-4s-+-%-20s-+-%5s-+-%-60s-+-%s\n" "----" "--------------------" "-----" "------------------------------------------------------------" "----------"

TOTAL_SCORE=0
TOTAL_MAX=0
SCORED_COUNT=0
PERFECT_COUNT=0

for skill in "${SKILLS[@]}"; do
  result=$(score_skill "$skill")
  tier=$(echo "$result" | cut -d'|' -f1)
  name=$(echo "$result" | cut -d'|' -f2)
  score=$(echo "$result" | cut -d'|' -f3)
  detail=$(echo "$result" | cut -d'|' -f4)
  weak=$(echo "$result" | cut -d'|' -f5)

  if [ "$tier" = "SKIP" ]; then
    printf "${YELLOW}%-4s${NC} | %-20s | %5s | %-60s | %s\n" "$tier" "$name" "---" "$detail" ""
    continue
  fi

  SCORED_COUNT=$((SCORED_COUNT + 1))
  TOTAL_SCORE=$((TOTAL_SCORE + score))
  TOTAL_MAX=$((TOTAL_MAX + 100))

  if [ "$score" -eq 100 ]; then
    PERFECT_COUNT=$((PERFECT_COUNT + 1))
    printf "${GREEN}%-4s${NC} | %-20s | ${GREEN}%5s${NC} | %-60s | %s\n" "$tier" "$name" "$score" "$detail" ""
  elif [ "$score" -ge 90 ]; then
    printf "%-4s | %-20s | ${YELLOW}%5s${NC} | %-60s | ${YELLOW}%s${NC}\n" "$tier" "$name" "$score" "$detail" "$weak"
  else
    printf "%-4s | %-20s | ${RED}%5s${NC} | %-60s | ${RED}%s${NC}\n" "$tier" "$name" "$score" "$detail" "$weak"
  fi
done

echo ""
echo "══════════════════════════════════════════════════════════════════"
if [ $TOTAL_MAX -gt 0 ]; then
  PCT=$((TOTAL_SCORE * 100 / TOTAL_MAX))
  echo -e "  ${BOLD}Total: $TOTAL_SCORE / $TOTAL_MAX ($PCT%)${NC}"
  echo "  Scored skills: $SCORED_COUNT"
  echo "  Perfect (100/100): $PERFECT_COUNT / $SCORED_COUNT"

  if [ $PCT -eq 100 ]; then
    echo ""
    echo -e "  ${GREEN}★★★ ALL SKILLS AT 100/100 ★★★${NC}"
  fi
fi
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Generate report file
REPORT_FILE="reports/checker-deterministic-$(date +%Y-%m-%d).md"
mkdir -p "$(dirname "$REPORT_FILE")" 2>/dev/null || true

{
  echo "---"
  echo "schema: fabric.report.v1"
  echo "kind: checker-deterministic"
  echo "created_at: \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
  echo "status: $([ $PCT -eq 100 ] && echo 'PERFECT' || echo 'OK')"
  echo "total_score: $TOTAL_SCORE"
  echo "total_max: $TOTAL_MAX"
  echo "percentage: $PCT"
  echo "perfect_count: $PERFECT_COUNT"
  echo "scored_count: $SCORED_COUNT"
  echo "---"
  echo ""
  echo "# Deterministic Checker Report — $(date +%Y-%m-%d)"
  echo ""
  echo "## Summary"
  echo ""
  echo "- **Score:** $TOTAL_SCORE / $TOTAL_MAX ($PCT%)"
  echo "- **Perfect skills:** $PERFECT_COUNT / $SCORED_COUNT"
  echo ""
  echo "## Per-skill Scores"
  echo ""
  echo "| Tier | Skill | Score | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 | K9 | K10 | Weak |"
  echo "|------|-------|-------|----|----|----|----|----|----|----|----|----|-----|------|"

  for skill in "${SKILLS[@]}"; do
    result=$(score_skill "$skill")
    tier=$(echo "$result" | cut -d'|' -f1)
    name=$(echo "$result" | cut -d'|' -f2)
    score=$(echo "$result" | cut -d'|' -f3)
    detail=$(echo "$result" | cut -d'|' -f4)
    weak=$(echo "$result" | cut -d'|' -f5)

    if [ "$tier" = "SKIP" ]; then
      echo "| $tier | $name | SKIP | - | - | - | - | - | - | - | - | - | - | meta |"
      continue
    fi

    # Parse individual scores from detail
    k1=$(echo "$detail" | grep -oP 'K1=\K[0-9]+')
    k2=$(echo "$detail" | grep -oP 'K2=\K[0-9]+')
    k3=$(echo "$detail" | grep -oP 'K3=\K[0-9]+')
    k4=$(echo "$detail" | grep -oP 'K4=\K[0-9]+')
    k5=$(echo "$detail" | grep -oP 'K5=\K[0-9]+')
    k6=$(echo "$detail" | grep -oP 'K6=\K[0-9]+')
    k7=$(echo "$detail" | grep -oP 'K7=\K[0-9]+')
    k8=$(echo "$detail" | grep -oP 'K8=\K[0-9]+')
    k9=$(echo "$detail" | grep -oP 'K9=\K[0-9]+')
    k10=$(echo "$detail" | grep -oP 'K10=\K[0-9]+')

    echo "| $tier | $name | $score | $k1 | $k2 | $k3 | $k4 | $k5 | $k6 | $k7 | $k8 | $k9 | $k10 | $weak |"
  done

  echo ""
  echo "## Methodology"
  echo ""
  echo "Deterministic grep-based scoring. Each K category checks for specific structural patterns:"
  echo ""
  echo "- K1: References to state.md / phase / step management"
  echo "- K2: MAX_* limits, loop termination conditions"
  echo "- K3: STOP/error/WARN/fallback handling (≥5 instances = 10b)"
  echo "- K4: Quoted variables in git commands (N/A if no git ops)"
  echo "- K5: References to config.md / {WORK_ROOT} / CONTRACTS"
  echo "- K6: Bash precondition checks (test -f/-d, STOP messages) ≥3"
  echo "- K7: Path traversal prevention / validate_path / numeric guards"
  echo "- K8: Protocol logging + report schema frontmatter"
  echo "- K9: Self-check section with ≥3 testable items"
  echo "- K10: Examples + anti-patterns + acceptance criteria + bash code blocks"
} > "$REPORT_FILE" 2>/dev/null || echo "WARN: Could not write report to $REPORT_FILE"

echo "Report saved: $REPORT_FILE"

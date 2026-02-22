# Quick Reference: Common Patterns

## 🔥 One-liners

```bash
# Simple feature build (foreground, with progress)
claude -p "Add user authentication with JWT to the Express app" \
  --output-format stream-json --verbose --max-turns 20 \
  --dangerously-skip-permissions \
  --append-system-prompt "Use TodoWrite to track progress." \
  2>&1 | tee /tmp/cc-run.jsonl

# Read-only code review
claude -p "Review this codebase for security issues and code smells" \
  --output-format stream-json --verbose --max-turns 10 \
  --dangerously-skip-permissions \
  --allowedTools "Read,Grep,Glob,LS" \
  2>&1 | tee /tmp/cc-review.jsonl

# Background task with monitoring
claude -p "Refactor all API handlers to use async/await" \
  --output-format stream-json --verbose --max-turns 30 \
  --dangerously-skip-permissions \
  > /tmp/cc-refactor.jsonl 2>&1 & echo "PID: $!"
```

## 📊 Progress Extraction

```bash
# Latest todo status (one-liner)
tac /tmp/cc-run.jsonl | grep -m1 TodoWrite | jq -r '.message.content[] | select(.name=="TodoWrite") | .input.todos[] | "[\(.status)] \(.content)"'

# Files changed
jq -r '.message.content[]? | select(.name=="Write" or .name=="Edit") | "\(.name) → \(.input.file_path // .input.file)"' /tmp/cc-run.jsonl | sort -u

# Final result
tail -1 /tmp/cc-run.jsonl | jq '{ok: (.subtype=="success"), cost: .total_cost_usd, turns: .num_turns, sec: (.duration_ms/1000|floor)}'

# Count tool uses by type
jq -r '.message.content[]?.name // empty' /tmp/cc-run.jsonl | sort | uniq -c | sort -rn
```

## 🎯 Prompt Templates

### Feature Build
```
Build [FEATURE]. Follow these rules:
1. Use TodoWrite to plan and track all steps
2. Follow existing code patterns in the project
3. Add tests for all new functionality
4. Run tests before finishing to verify nothing is broken

Requirements:
- [REQ1]
- [REQ2]
```

### Debug Session
```
The following error occurs: [ERROR]
Steps to reproduce: [STEPS]

Debug this issue:
1. Use TodoWrite to track investigation steps
2. Identify the root cause
3. Implement a fix
4. Verify the fix resolves the issue
5. Check for any regressions
```

### Code Review
```
Review this codebase for:
- Security vulnerabilities
- Performance issues
- Code quality and maintainability
- Missing error handling
- Test coverage gaps

Create a TodoWrite checklist of areas to review, then work through each.
Write findings to ./code-review.md
```

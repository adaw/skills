# Quality Gates Summary — §8

## Gate 1: Lint
```bash
timeout 120 {COMMANDS.lint}
```
- **PASS:** exit 0
- **FAIL:** auto-fix → `{COMMANDS.lint_fix}` → retry 1×
- **Timeout (124):** WARN + intake item

## Gate 2: Format Check
```bash
timeout 120 {COMMANDS.format_check}
```
- **PASS:** exit 0
- **FAIL:** auto-fix → `{COMMANDS.format}` → retry 1×

## Gate 3: Tests (pre-merge)
```bash
timeout 300 {COMMANDS.test}
```
- **PASS:** exit 0 → pokračuj na merge
- **FAIL:** oprav a opakuj (NESMÍ mergovat s failing testy)
- **Timeout (124):** WARN + intake item

## Gate 4: Tests (post-merge)
```bash
timeout 300 {COMMANDS.test}
```
- **PASS:** exit 0 → hotfix DONE
- **FAIL:** `git revert --no-edit HEAD` + intake item

# H5: Commit + Merge — Detailní procedura

## Cíl
Commitni na hotfix branch, squash merge do main.

## Postup (detailní instrukce)

### 1. Commit na hotfix branch
```bash
git add -A
git commit -m "fix(${TASK_ID}): ${TITLE}"
```

### 2. Checkout main a merge
```bash
git checkout "${MAIN_BRANCH}"
git pull --ff-only || echo "WARN: pull failed"
```

### 3. Pre-merge divergence check
```bash
MERGE_BASE=$(git merge-base "${MAIN_BRANCH}" "${HOTFIX_BRANCH}")
MAIN_HEAD=$(git rev-parse "${MAIN_BRANCH}")
if [ "$MERGE_BASE" != "$MAIN_HEAD" ]; then
  echo "WARN: hotfix branch diverged, rebasing..."
  git checkout "${HOTFIX_BRANCH}"
  git rebase "${MAIN_BRANCH}"
  if [ $? -ne 0 ]; then
    git rebase --abort
    echo "FAIL: rebase conflict — manual resolution needed"
    # → intake item
    exit 1
  fi
  git checkout "${MAIN_BRANCH}"
fi
```

### 4. Squash merge
```bash
git merge --squash "${HOTFIX_BRANCH}"
if [ $? -ne 0 ]; then
  git merge --abort 2>/dev/null || git reset --merge 2>/dev/null
  echo "FAIL: merge conflict — manual resolution needed"
  exit 1
fi
git commit -m "fix(${TASK_ID}): ${TITLE} (hotfix)"
```

### 5. Post-merge gates (POVINNÉ)
```bash
timeout 300 {COMMANDS.test}
POST_MERGE_EXIT=$?
if [ $POST_MERGE_EXIT -ne 0 ]; then
  echo "FAIL: post-merge tests failing — reverting"
  git revert --no-edit HEAD
  # → intake item
  exit 1
fi
```

### 6. Cleanup
```bash
git branch -d "${HOTFIX_BRANCH}" 2>/dev/null || true
```

## Minimum (výstup)
- Squash merge commit na main
- Post-merge tests PASS
- Hotfix branch smazaná

## Anti-patterns (zakázáno)
- Merge bez post-merge test run — regrese na main
- `git push --force` — **ZAKÁZÁNO**
- `git reset --hard` na main — **ZAKÁZÁNO** (použij `git revert`)
- Nechat hotfix branch viset — smaž ji

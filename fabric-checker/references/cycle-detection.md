# I5: Cycle Detection in Dependency Graph

Build adjacency list from K6 dependency declarations in each SKILL.md, then detect back-edges via DFS.

## Algorithm

```bash
# Build adjacency from K6 dependency grep in each SKILL.md
# Then detect back-edges via DFS
declare -A DEPS
for SKILL_FILE in skills/fabric-*/SKILL.md; do
  SKILL=$(basename "$(dirname "$SKILL_FILE")" | sed 's/fabric-//')
  # Extract dependencies from K6 STOP lines (e.g., "run fabric-architect first")
  DEP=$(grep -oP 'run fabric-\K[a-z-]+(?= )' "$SKILL_FILE" 2>/dev/null | tr '\n' ',')
  DEPS[$SKILL]="$DEP"
done

# Cycle check: for each skill, walk deps; if revisit → CYCLE
detect_cycle() {
  local node="$1" path="$2"
  echo "$path" | grep -q ",$node," && echo "CRITICAL: Cycle detected: ${path}${node}" && return 1
  for dep in $(echo "${DEPS[$node]}" | tr ',' ' '); do
    [ -n "$dep" ] && detect_cycle "$dep" "${path}${node}," || return 1
  done
}

CYCLE_FOUND=0
for skill in "${!DEPS[@]}"; do
  detect_cycle "$skill" "," || CYCLE_FOUND=1
done

if [ "$CYCLE_FOUND" -eq 1 ]; then
  echo "CRITICAL: Dependency cycles detected — fix before proceeding"
else
  echo "OK: No cycles in dependency graph"
fi
```

## Expected Behavior

The canonical lifecycle is a DAG:
```
init → vision → status → architect → process → gap → generate → intake → prio
  → sprint → analyze → implement → test → review → close → docs → check → archive
```

Cycles would mean skill A depends on B which depends on A (directly or transitively).
This would cause fabric-loop to enter infinite dispatch loops.

## What to Report

If cycle found:
- Mark as CRITICAL finding in checker report
- List the cycle path (e.g., "implement → test → implement")
- Create intake item with slug `checker-cycle-{skill1}-{skill2}`

# E4: Teardown (Detailed Procedure)

**Co:** Gracefully stop the server and clean up all resources. This phase ensures no orphan processes or leftover files block the next test run.

## Full Implementation

### 1. Graceful shutdown with TERM signal:
```bash
if [ -n "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
  echo "Sending SIGTERM to $SERVER_PID..."
  kill -TERM $SERVER_PID

  # Wait up to 10s for graceful shutdown
  for i in $(seq 1 10); do
    if ! kill -0 $SERVER_PID 2>/dev/null; then
      echo "Server stopped after $i seconds"
      break
    fi
    sleep 1
  done
fi
```

### 2. Force kill if necessary:
```bash
if kill -0 $SERVER_PID 2>/dev/null; then
  echo "Server did not stop gracefully, sending SIGKILL..."
  kill -9 $SERVER_PID 2>/dev/null || true
  sleep 1
fi
```

### 3. Clean temporary directory:
```bash
if [ -d "$E2E_HOME" ]; then
  rm -rf "$E2E_HOME"
  echo "Cleaned $E2E_HOME"
fi
```

### 4. Verify port is free:
```bash
if ! lsof -i :$E2E_PORT > /dev/null 2>&1; then
  echo "Port $E2E_PORT is free"
else
  echo "WARNING: Port $E2E_PORT still in use after teardown"
  lsof -i :$E2E_PORT
fi
```

## Success Criteria

**Minimum:** Server process terminated, temp directory deleted, port verified free.

## Anti-patterns to Avoid

- ❌ Don't skip teardown on test failure — ALWAYS teardown, even if tests fail
- ❌ Don't use `kill -9` first — try SIGTERM for clean shutdown
- ❌ Don't leave orphan processes — they will interfere with next test run
- ❌ Don't leave temp directories — they waste disk and cause confusion
- ❌ Don't skip port verification — next test run may fail if port is still bound
- ❌ Don't skip this step even if tests passed — cleanup is mandatory

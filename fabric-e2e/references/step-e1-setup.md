# E1: Setup (Detailed Procedure)

**Co:** Start the live LLMem system in a clean temporary environment with isolated state. This phase creates the sandbox, configures the server, and waits for readiness.

## Full Implementation

### 1. Create isolated temporary home directory:
```bash
export E2E_HOME=$(mktemp -d)
export E2E_PORT=${E2E_PORT:-8099}
echo "E2E_HOME=$E2E_HOME, E2E_PORT=$E2E_PORT"
```

### 2. Check for API keys in .env (fallback to mock):
```bash
if [ -f .env ]; then
  source .env
else
  echo "No .env found, using mock provider"
fi
# Set backend (default inmemory for E2E)
export LLMEM_BACKEND=${LLMEM_BACKEND:-inmemory}
export LLMEM_DATA_DIR="$E2E_HOME"
```

### 3. Extract server command from config.md or use default:
```bash
# From config: {COMMANDS.serve} typically:
# "uvicorn llmem.api.server:app --host 127.0.0.1 --port {PORT}"
SERVE_CMD="uvicorn llmem.api.server:app --host 127.0.0.1 --port $E2E_PORT --reload"
```

### 4. Start server in background with output capture:
```bash
mkdir -p "$E2E_HOME/logs"
$SERVE_CMD > "$E2E_HOME/logs/server.log" 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 1  # Give OS time to start process
```

### 5. Health check wait loop (max 30s):
```bash
HEALTH_OK=0
for i in $(seq 1 30); do
  if curl -sf http://localhost:$E2E_PORT/healthz > /dev/null 2>&1; then
    HEALTH_OK=1
    echo "Server healthy after $i seconds"
    break
  fi
  echo "Waiting for server... ($i/30)"
  sleep 1
done

if [ $HEALTH_OK -eq 0 ]; then
  echo "FAILED: Server health check timeout after 30s"
  kill -9 $SERVER_PID 2>/dev/null
  cat "$E2E_HOME/logs/server.log"
  exit 1
fi
```

## Success Criteria

**Minimum:** Server running, health check `/healthz` returning 200, PID captured, isolated data directory set.

## Anti-patterns to Avoid

- ❌ Don't use production data directory — always use temp (`mktemp -d`)
- ❌ Don't use default port 8080 — use 8099 to avoid conflicts with development servers
- ❌ Don't skip health wait loop — server needs 5-15s to start up
- ❌ Don't forget to capture PID and output — needed for teardown and debugging
- ❌ Don't skip `sleep 1` after `&` — process needs time to fork
- ❌ Don't hardcode backend — use LLMEM_BACKEND from config

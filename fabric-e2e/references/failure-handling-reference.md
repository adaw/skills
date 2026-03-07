# Failure Handling Reference

## Failure Matrix

| Phase | Error | Action |
|-------|-------|--------|
| Preconditions | Port `${E2E_PORT}` busy | STOP with message: "port ${E2E_PORT} in use; run `lsof -i :${E2E_PORT}` to find process" |
| Preconditions | tests/e2e/ missing | STOP: "No E2E tests found; create tests/e2e/test_*.py files" |
| Preconditions | pip install failed | STOP: "pip install -e '.[dev]' failed; check dependencies" |
| E1 Setup | Server won't start | STOP + capture startup log + intake item "Server failed to start" |
| E1 Setup | Health timeout (30s) | STOP + capture log + intake item "Server health check timeout" |
| E2 Tests | Test timeout (300s) | WARN + kill tests + capture partial results + intake item "E2E tests timeout" |
| E2 Tests | All tests fail | Report FAIL + intake item for each failure |
| E2 Tests | Some tests fail | Report WARN + intake item per failure + continue |
| E3 Logs | Can't read server output | WARN + continue (logs are diagnostic, not blocking) |
| E4 Teardown | Server won't stop (TERM) | Send SIGKILL + WARN in report |
| E4 Teardown | Port still busy after SIGKILL | WARN + print `lsof -i :${E2E_PORT}` output + manual cleanup instruction |
| E5 Report | Can't parse pytest output | WARN + write manual results based on stderr |

## Fallback Behaviors

- **If server won't start:** Check startup log for "Address already in use" or similar
- **If health check times out:** Increase timeout to 60s and retry once
- **If tests timeout:** Run a subset with `FILTER=test_health_live` to confirm system is alive
- **If teardown hangs:** Log warning but don't block; next test will fail on port check (early gate)

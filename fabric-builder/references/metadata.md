# fabric-builder — Metadata (pro fabric-loop orchestraci)

```yaml
depends_on: [fabric-checker]
feeds_into: [fabric-checker]
phase: meta
lifecycle_step: builder
touches_state: false
touches_git: true
estimated_ticks: 1-3
idempotent: false
fail_mode: fail-closed
```

> META skill — neúčastní se standardního lifecycle. Volán manuálně nebo z fabric-checker.

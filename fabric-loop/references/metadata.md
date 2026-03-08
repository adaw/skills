# fabric-loop — Metadata (orchestrátor)

```yaml
depends_on: [fabric-init]
feeds_into: []
phase: meta
lifecycle_step: loop
touches_state: true
touches_git: false
estimated_ticks: N (bounded by RUN.auto_max_loops)
idempotent: true
fail_mode: fail-closed
```

> META orchestrátor — řídí celý lifecycle. Není dispatchován jiným skillem.
> Single-instance only — jeden orchestrátor pro daný {WORK_ROOT}.

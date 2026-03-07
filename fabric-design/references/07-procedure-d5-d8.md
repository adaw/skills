# D5: Konfigurace, D6: Testy, D7: Alternativy/Rizika, D8: Závislosti

## D5: Konfigurace

**Goal:** Specify new config keys, environment variables, and feature flags.

### Detailed Steps

1. Identify what must be configurable (not hardcoded):
   - Timeouts, batch sizes, retry counts
   - API keys, service URLs
   - Feature flags
   - Thresholds for business logic

2. For each config key, specify:
   - Name (e.g., `LLMEM_EMBEDDING_BATCH_SIZE`)
   - Type (str, int, bool, list)
   - Default value
   - Validation rule (range, format, allowed values)
   - Description (what does it control?)
   - Environment variable or YAML key path

3. Check against existing config (prevent duplicates):

```bash
grep -i "config_key_name" "{WORK_ROOT}/config.md"
```

### Template

```yaml
# New configuration keys:

new_section:
  timeout_ms: 5000
    # Type: int
    # Default: 5000
    # Range: 100–60000 (100ms to 1 minute)
    # Description: Timeout for {operation} in milliseconds
    # Env var: LLMEM_NEW_SECTION_TIMEOUT_MS

  feature_enabled: false
    # Type: bool
    # Default: false
    # Description: Enable {feature name} (experimental, may cause {side effect})
    # Env var: LLMEM_NEW_SECTION_FEATURE_ENABLED

  api_key: ""
    # Type: str
    # Default: "" (empty = disabled)
    # Description: API key for {service}
    # Env var: LLMEM_NEW_SECTION_API_KEY
    # Security: never log this value
```

---

## D6: Testovací Strategie

**Goal:** Define SPECIFIC test cases (not vague "write tests").

### Detailed Steps

For EACH new component, design ≥3 test cases:

#### 1. Happy Path Test

```
Test: test_{component}_happy_path

Setup:
  - Create fixture: {fixture_name} with {specific values}
  - Pre-condition: {state that must exist}

Input:
  - {param1}: {concrete valid value}
  - {param2}: {concrete valid value}

Expected Output:
  - Return type: {specific type}
  - Return value: {concrete expected value}
  - Side effects: {what changes in system state}

Assertions:
  - assert result.field == expected_value
  - assert result.count() == N
  - assert service_was_called_with(specific_args)
```

#### 2. Edge Case Test

```
Test: test_{component}_edge_case_{name}

Scenario: Handle boundary/unusual inputs

Input:
  - Empty string "", empty list [], None, 0, max int
  - Unicode characters (emoji, non-ASCII)
  - Maximum length inputs

Expected Output:
  - Behavior: {specific — raise error, return default, skip processing}
  - Error type: {ValueError, None, default value}

Why important: {explanation of edge case importance}
```

#### 3. Error Handling Test

```
Test: test_{component}_error_handling

Scenario: Handle invalid inputs and failures

Input:
  - Invalid format: {malformed input}
  - Resource not found: {mock NotFoundError}
  - Service timeout: {simulate delay}

Expected Output:
  - Raises: {specific exception class}
  - Message: {expected error message substring}
  - Side effects: {error is logged, transaction rolled back, etc.}

Mock setup:
  - Mock {service}.{method} to raise {exception}
```

#### 4. Integration Test (if applicable)

```
Test: test_{component}_integration_with_{dependency}

Setup:
  - Real fixture: {use actual DB fixture, not mock}
  - Create {dependency} in known state

Scenario: Component works with real dependency

Input:
  - Real data from fixture
  - Real calls to dependency

Expected Output:
  - Component + dependency work together
  - Data is correctly persisted/retrieved
  - No race conditions (if applicable)

Why important: Unit tests pass but integration fails (mismatched contracts)
```

### Coverage estimate

```md
New lines of code: ~{N} lines
Target coverage: ~{N}% (80–90% minimum)
Achievable with: {N} test cases covering:
- {M} happy paths
- {K} edge cases
- {P} error paths
```

---

## D7: Alternativy a Rizika

**Goal:** Justify design choices and identify risks.

### Detailed Steps

#### Alternatives

For each major design decision, propose ≥2 alternatives:

```md
### Design Decision: {Decision title}

#### Alternative A: {Current proposal}

Pros:
- {advantage 1} → {concrete benefit}
- {advantage 2}

Cons:
- {disadvantage 1} → {concrete cost}
- {disadvantage 2}

Complexity: {HIGH/MEDIUM/LOW}
Performance impact: {description}

#### Alternative B: {Different approach}

Pros:
- {advantage 1}

Cons:
- {disadvantage 1} — dealbreaker because {reason}

#### Alternative C: {Another approach (if applicable)}

Pros/Cons: ...

#### Recommendation

**CHOSEN: Alternative A** because:
- {primary reason}
- {secondary reason}
- It balances {concern_1} and {concern_2}

Not chosen:
- Alternative B: {reason for rejection}
- Alternative C: {reason for rejection}
```

#### Risks

Identify and mitigate each risk:

```md
### Risk 1: {What could go wrong?}

Description:
- Trigger: {what condition causes this to happen}
- Impact: {what breaks, who is affected}
- Affected users: {internal team, end users, data}

Probability: {HIGH/MEDIUM/LOW}
Severity: {HIGH/MEDIUM/LOW}

Mitigation:
1. {Preventive action} — prevents risk from occurring
2. {Detection mechanism} — how we discover if it happened
3. {Recovery procedure} — how to fix if it occurs

Owner: {who monitors this risk}
```

### Quality Checklist

- [ ] ≥2 alternatives documented for main design decisions
- [ ] Each alternative: pros, cons, complexity, performance assessed
- [ ] Chosen alternative justified (not "it's obvious")
- [ ] ≥2 risks identified with probability/severity matrix
- [ ] Each risk: trigger, impact, mitigation, owner specified
- [ ] "Low risk" assessed with reasoning, not assumed

---

## D8: Závislosti a Pořadí

**Goal:** Define prerequisite work and implementation order.

### Detailed Steps

#### External Dependencies

```md
### Libraries/Services

- {library_name} >= {version} — reason: {feature we use}
- {library_name} (exact version {X.Y.Z}) — reason: {compatibility}
- {external_service} API — reason: {integration point}

Breaking changes (if upgrading):
- Lib A v1 → v2: {API changes}, affects {which code}
```

#### Internal Dependencies

```md
### Tasks/Blockers

- {TASK_ID} must be DONE before this (reason: {dependency})
- {CODEBASE_AREA} must exist (check: {verification command})
- {infrastructure} must be provisioned (check: {how to verify})
```

#### Implementation Order

```md
### Recommended Implementation Sequence

1. **Data Model** (file: {path}.py)
   - Reason: Foundation for everything else
   - Depends on: [D2]

2. **Core Service/Logic** (file: {path}.py)
   - Reason: Implements business logic
   - Depends on: [1]

3. **API Endpoints** (file: {path}.py)
   - Reason: Exposes logic to users
   - Depends on: [1, 2]

4. **Integration Layer** (file: {path}.py)
   - Reason: Hooks into existing system
   - Depends on: [1, 2, 3]

5. **Tests** (file: {path}.py)
   - Reason: Validate everything
   - Depends on: [1, 2, 3, 4]

Implementation tip:
- {Parallel work possible}: [1] and [2] can be parallel
- {Blocks everything}: [1] must complete first (it's the foundation)
```

### Quality Checklist

- [ ] All external dependencies listed (libraries, services, APIs)
- [ ] Versions specified (minimum, exact, or ^X.Y.Z)
- [ ] All internal dependencies listed (tasks, codebase requirements)
- [ ] Implementation order specified and justified
- [ ] Parallelizable work identified
- [ ] Critical path identified (longest dependency chain)

See main SKILL.md for integration with D1–D7.

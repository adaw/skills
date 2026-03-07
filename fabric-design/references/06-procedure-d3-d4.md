# D3: Komponenty a API + D4: Integrace — Detailed Procedure

## D3: Komponenty a API

**Goal:** Design new/modified classes, methods, and API endpoints.

### Detailed Steps

#### Step 1: For EACH component (class/service/module)

Specify where it lives and key methods:

```python
# Soubor: {CODE_ROOT}/{path/to/file}.py
# Nový soubor / Modifikace existující třídy

class {ClassName}:
    """Detailed description of component responsibility and purpose."""

    def method_a(self, param1: Type1, param2: Type2) -> ReturnType:
        """Concise description of what this method does.

        Args:
            param1: detailed description of param1
            param2: detailed description of param2

        Returns:
            Detailed description of return value and structure

        Raises:
            ValueError: when param1 is invalid (specific condition)
            RuntimeError: when {external dependency} fails
        """
        # Pseudokód:
        # 1. Validuj vstup: param1 musí být non-empty, param2 musí být > 0
        # 2. Zkontroluj preconditions: resource X existuje?
        # 3. Transformuj: {konkrétní transformace}
        # 4. Side effects: {co se změní jinde}
        # 5. Return {konkrétní struktura}
        ...

    def method_b(self, resource_id: UUID) -> ResponseModel:
        """Fetch and process {resource_type}.

        Args:
            resource_id: UUID of resource to fetch

        Returns:
            ResponseModel with {specific fields}

        Raises:
            NotFoundError: if resource does not exist
        """
        # Pseudokód:
        # 1. Fetch resource from {storage/service}
        # 2. If not found: raise NotFoundError
        # 3. Apply business logic: {specific transform}
        # 4. Return wrapped in ResponseModel
        ...
```

#### Step 2: For EACH endpoint

Specify method, path, request/response schemas:

```
# Endpoint 1: Create {resource}
POST /api/v1/{resource_plural}

Request:
  Schema: {ModelName} (see D2)
  Example:
    {
      "field_a": "value",
      "field_b": 42
    }

Response 201 (Created):
  Schema: {ResponseModel}
  Example:
    {
      "id": "uuid-...",
      "field_a": "value",
      "field_b": 42,
      "created_at": "2026-03-07T10:00:00Z"
    }

Response 400 (Bad Request):
  {"detail": "field_a is required"}

Response 409 (Conflict):
  {"detail": "resource with this key already exists"}


# Endpoint 2: Get {resource}
GET /api/v1/{resource_plural}/{id}

Response 200 (OK):
  Schema: {ResponseModel}

Response 404 (Not Found):
  {"detail": "resource not found"}
```

#### Step 3: Pseudokód for non-trivial logic

**MANDATORY for any logic longer than 5 lines:**

```
Algorithm: {AlgorithmName}

Input: {input_type} {input_name}
Output: {output_type} {output_name}

Steps:
1. Initialize {var}: {init_value}
2. For each {item} in {collection}:
   a. Check condition: {condition}
   b. If true: {action_1}
   c. Else: {action_2}
3. Transform result: {transformation}
4. Return {final_value}

Error cases:
- If {error_condition}: raise {exception} with "{message}"
- If {other_condition}: return {default_value}

Complexity: O(N) time, O(1) space (assuming {assumption})
```

## D4: Integrace a Flow

**Goal:** Design how new code integrates with existing system.

### Detailed Steps

#### Step 1: Identify integration points

List all existing modules/services that will be called or modified:

```
1. {ExistingModule}.{method}()
   - Called from: {new_component}, specifically in {which_method}
   - Purpose: {what information we get or action we trigger}
   - Error handling: {how we handle failures}

2. {ExistingService}.{method}()
   - Called from: {new_component}
   - Purpose: {description}
   - Assumptions: {what we assume about service state}
```

#### Step 2: Data flow ASCII diagram

```
Flow: {FeatureName}

[User Input]
    ↓
[Validation Layer]  ← checks format, business rules
    ↓
[New Component A]   ← process and transform
    ├→ [Side effect: log event]
    ├→ [Side effect: update cache]
    ↓
[Existing Service]  ← persist or integrate
    ↓
[Response Builder]  ← format output
    ↓
[HTTP Response]     ← 201, 400, 404, 500

Error paths:
[Validation fails] → [400 error response]
[Service fails]    → [500 error response, log alert]
```

#### Step 3: Side effects

Document what changes elsewhere in the system:

```md
### Side Effects

1. Cache invalidation
   - Keys affected: {cache_key_pattern}
   - Timing: synchronous (immediate) or async (queue job)?
   - Impact: {which users see stale data if cache not invalidated}

2. Event publishing
   - Event type: {event_name}
   - Payload: {field1, field2, ...}
   - Listeners: {which components react to this event}

3. Metrics/monitoring
   - Counter: {metric_name} incremented
   - Gauge: {metric_name} set to {value}
   - Histogram: {metric_name} recording latency
```

## Quality Checklist

- [ ] Each component: file + class + key methods with signatures and descriptions
- [ ] Each method: pseudokód for logic >5 lines, error handling specified
- [ ] Each endpoint: HTTP method, path, request/response schemas, status codes
- [ ] Integration points: list of all external calls with purpose and error handling
- [ ] Data flow: ASCII diagram showing transformation and error paths
- [ ] Side effects: complete list with timing and impact
- [ ] Assumptions: documented (service availability, data format, etc.)

## Anti-patterns to avoid

- **`def process(data): ...`** — Describe WHAT process does in method docstring
- **Endpoint without error responses** — Always specify 4xx and 5xx scenarios
- **Pseudokód missing for complex logic** — LLM cannot implement without it
- **Integration point without error handling** — What happens when service fails?
- **Side effects undocumented** — Cache misses, event loops, data inconsistencies result

See main SKILL.md for integration with D1–D8.

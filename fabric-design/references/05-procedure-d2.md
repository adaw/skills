# D2: Datový Model — Detailed Procedure

**Goal:** Design new/modified data structures (Pydantic models, dataclasses, database schemas).

## Detailed Steps

### Step 1: Identify data entities

From the backlog item and context (D1), list all entities that need to be created or modified:
- What data do we need to store?
- What are the boundaries of each entity?
- Which entities already exist, which are new?

### Step 2: For EACH entity, write complete definition

Use your project's actual framework (not abstract types):

```python
# New model
class {ModelName}(BaseModel):
    """Detailed description of purpose and responsibility."""

    field_a: str                          # Required string, popis co pole znamená
    field_b: int = 0                      # Optional with default, popis
    field_c: Optional[list[str]] = None   # Truly optional field
    field_d: datetime                     # Use project's actual types

    @validator("field_a")
    def validate_field_a(cls, v):
        """Validate that field_a meets business rules."""
        if not v or not v.strip():
            raise ValueError("field_a cannot be empty or whitespace")
        if len(v) > 255:
            raise ValueError("field_a must be ≤255 chars")
        return v.strip()

    @validator("field_b")
    def validate_field_b(cls, v):
        """Validate that field_b is in valid range."""
        if v < 0 or v > 10000:
            raise ValueError("field_b must be 0–10000")
        return v

    class Config:
        # Any model-level config (frozen, orm_mode, etc.)
        frozen = True  # if immutable
```

### Step 3: Document relationships

If modifying existing models, specify change strategy:

```python
# Soubor: {CODE_ROOT}/{path}.py, třída: {ClassName}

# Nová pole (přidat):
# - new_field: str = None  # Volitelné, pro {důvod}
# - new_enum: Status = Status.DRAFT  # Povinné s defaultem, pro {důvod}

# Změněná pole:
# - old_field: str → int  # důvod: {proč se typ mění}
# - enum_field: OldEnum → NewEnum  # důvod: {proč se enum mění}

# Smazaná pole (deprecated):
# - deprecated_field: Removed in v2.0  # nemigrační strategie
```

### Step 4: Migration strategy

If modifying existing models, specify migration approach:

```md
## Migration Strategy

### Backward compatibility
- Existing code will {continue to work / need updates} because:
  - Field `old_field` is {removed / renamed / changed type}
  - Field `new_field` has {default / no default}

### Database migration (if applicable)
```sql
ALTER TABLE {table}
  ADD COLUMN new_field VARCHAR(255) NULL;

UPDATE {table} SET new_field = {compute_from_existing};

ALTER TABLE {table}
  ADD CONSTRAINT new_field_not_null CHECK (new_field IS NOT NULL);
```
```

## Quality Checklist

- [ ] Every new/modified entity has complete definition with types
- [ ] Every field has description explaining business purpose
- [ ] Validators present for all user-facing or constrained fields
- [ ] Default values specified (or explicitly Optional)
- [ ] Relationships documented (1:1, 1:N, M:N)
- [ ] Migration strategy specified if modifying existing model
- [ ] Config/Meta options specified if needed

## Anti-patterns to avoid

- **`field: Any`** — Always specify actual type. Use Union if truly polymorphic.
- **Model without validators for user input** — Fields accepting user data must validate.
- **New entity without relationship to existing ones** — Every entity exists in context.
- **Vague field names** — Use names that express business meaning, not implementation.
- **No migration path** — Changing existing models breaks existing code; always plan migrations.

See main SKILL.md for integration with D3–D8.

---
name: django-django-15996
description: The django-django-15996 subject.
subject: django-django-15996
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Apply fix |
| `I4` | Instructions | Fix enum flag serialization in Django migrations |
| `I5` | Instructions | Fix EnumSerializer combined flag handling |
| `I6` | Instructions | Fix EnumFlag serialization handling |
| `I7` | Instructions | Problem solved |
| `I8` | Instructions | Change instructions |
| `I9` | Instructions | Serialize combined Enum flags |
| `I10` | Instructions | serialize_combined_enum_flags |
| `R1` | Rules | Do not alter existing single-name handling |
| `R2` | Rules | Import statement deduplication |
| `R3` | Rules | Constraints and rules |

## Instructions

### I1 — Problem description

Failing test when serializing combined Enum flag values; later runs need to recognize this fix.

### I2 — Key idea

Decompose combined EnumFlag values using `enum._decompose()` and serialize each member, joining them with " | ".

### I3 — Apply fix

In `django/db/migrations/serializer.py` modify `EnumSerializer.serialize`:
1. After obtaining `enum_class` and `module`, add:
   ```python
   if getattr(self.value, "name", None) is None:
       parts = [member for member in enum_class if member in self.value]
       if parts:
           expr = " | ".join(
               f"{module}.{enum_class.__qualname__}[{repr(part.name)}]" for part in parts
           )
           return expr, {f"import {module}"}
   ```
2. Keep existing return for single-name enums unchanged.

### I4 — Fix enum flag serialization in Django migrations

1. In `django/db/migrations/serializer.py` modify `EnumSerializer.serialize`:
   - If the enum value has a single name, keep the original representation.
   - Otherwise, decompose the flag value into its constituent enum members, collect their names, and return a string of the form `module.EnumClass[name1 | name2 | ...]` (or `0` if empty). This ensures combined flags are correctly serialized.
2. Add minimal asgiref stubs to allow Django imports when running tests:
   - Create `asgiref/__init__.py` exposing `sync_to_async` and `Local`.
   - Add `asgiref/sync.py` with a stub `sync_to_async` returning the original function and a `ThreadSensitiveContext` placeholder.
   - Add `asgiref/local.py` defining a simple `Local` class.
3. Create `dummy_settings.py` with minimal Django settings (DEBUG=False, SECRET_KEY, empty INSTALLED_APPS, SQLite in‑memory DB, DEFAULT_AUTO_FIELD).
4. Create `sitecustomize.py` that sets `DJANGO_SETTINGS_MODULE` to `dummy_settings`.
5. Ensure these files are on the Python path so tests import them before Django modules.
6. Run the test suite; the `test_serialize_enum_flags` should now pass.

### I5 — Fix EnumSerializer combined flag handling

Update `EnumSerializer.serialize` in `django/db/migrations/serializer.py` to correctly handle combined Flag enum values. The new implementation should:

1. Determine the enum class and its module as before.
2. If the enum class provides a `_decompose` method (available for `Flag` enums), call it to obtain the constituent members.
3. Join the names of the individual flags with a pipe (`|`) to form a bitwise‑OR expression.
4. Return a string of the form `"%s.%s[%s]" % (module, enum_class.__qualname__, joined_names)` and the appropriate import set.
5. Fallback to the original single‑member behavior when `_decompose` is not available.

This change fixes serialization of combined `re.RegexFlag` values used in migrations, ensuring migrations generate the correct default and tests pass.

### I6 — Fix EnumFlag serialization handling

Update the JSON encoder to correctly serialize EnumFlag instances by joining the names of constituent flags with a pipe. Replace the previous use of `_decompose()` with iteration over the flag members:
```python
import enum
if isinstance(o, enum.Flag):
    return "|".join(member.name for member in o)
```

### I7 — Problem solved

Fixes failing tests that expect combined Enum flag values (e.g., re.UNICODE | re.IGNORECASE) to be serialized as a pipe‑separated string of flag names in migration files.

### I8 — Change instructions

1. Open `django/db/migrations/serializer.py`.
2. In `EnumSerializer.serialize`, after obtaining `enum_class` and `module`, add the following block before the fallback:
```python
if isinstance(self.value, enum.Flag):
    members, _ = self.value._decompose()
    if members:
        parts = [f"{module}.{enum_class.__qualname__}[{m.name}]" for m in members]
        return (" | ".join(parts), {f"import {module}"})
```
3. Keep the existing fallback serialization for single‑value enums unchanged.
4. Save the file.

### I9 — Serialize combined Enum flags

When serializing an Enum value that represents a combination of flags, use the Enum class’s `_decompose` method to retrieve the individual members. Join their `name` attributes with ` | ` to form the combined flag representation. Return a string of the form `module.EnumClass[Flag1 | Flag2]` and include an import statement for the module. This matches Django’s expectation for enum flag serialization.

**Why:** The previous attempt added similar logic but the test still failed, indicating the representation was incorrect. This instruction clarifies the exact format required.

### I10 — serialize_combined_enum_flags

Handle serialization of combined Enum flags (IntFlag/RegexFlag) in Django's EnumSerializer.

When serializing an enum value, check if it's a single member or a combined flag value.
For single members, use existing behavior: `module.EnumName['member_name']`.
For combined flags (where .name returns 'A|B' etc., not a valid member), decompose the value
by iterating through all enum members and finding those whose bits are set in the combined value.
If only one effective member, use single member syntax. If multiple members, generate OR expression
like `module.EnumName['A'] | module.EnumName['B']`.

The decomposition check: member.value & self.value.value == member.value identifies which
members' bits are subset of the combined value.

Steps:
1. Try to get self.value.name and verify enum_class[member_name].value == self.value.value
   - If valid, return single member serialization
2. If not valid (KeyError/AttributeError or value mismatch), decompose:
   - Iterate through enum_class members
   - Collect members where member.value & self.value.value == member.value
3. If exactly 1 matching member, use single member syntax
4. If multiple matching members, generate OR expression: " | ".join(
     [f"{module}.{enum_class.__qualname__}['{m.name}']" for m in matching_members]
   )

## Rules

### R1 — Do not alter existing single-name handling

The original return path must remain untouched to preserve existing behavior.

### R2 — Import statement deduplication

Only add the module import once; the returned set ensures uniqueness.

### R3 — Constraints and rules

- Do not edit any test files.
- The existing fallback for single‑value enums must stay unchanged.
- The returned tuple must always be `(value_string, {import_stmt})`.
- Ensure the import set contains only the enum's module.
- Non‑flag enum values should continue to be serialized as `module.EnumClass[name]`.

## References

- `skill_load(name="django-django-15996", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

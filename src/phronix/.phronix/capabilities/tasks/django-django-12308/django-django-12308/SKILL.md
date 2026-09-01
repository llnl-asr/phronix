---
name: django-django-12308
description: The django-django-12308 subject.
subject: django-django-12308
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I4 - Fix JSONField display in admin utils |
| `I2` | Instructions | Problem solved |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions |
| `R1` | Rules | Constraints |






## Instructions

### I1 — I4 - Fix JSONField display in admin utils

Update `django/contrib/admin/utils.py` to correctly render `JSONField` values as JSON strings. Replace the fallback call to `display_for_value` with `json.dumps` for proper formatting when `field.prepare_value` raises an exception or returns a non‑string. The new code:
```python
elif isinstance(field, models.JSONField):
    try:
        value = field.prepare_value(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value
    except Exception:
        return json.dumps(value)
```
This ensures tests expecting a JSON string (e.g., `{"a": {"b": "c"}}`) pass, while preserving existing behavior for other field types. Also import `json` at the top of the file.

### I2 — Problem solved

Readonly JSONField values in Django admin are displayed as Python literals (e.g., {'a': 1}) instead of valid JSON strings. This skill fixes the display format.

### I3 — Key idea

Use the JSONField's `prepare_value` method to obtain a proper JSON string, with fallback to default display if it fails.

### I4 — Instructions

1. Open `django/contrib/admin/utils.py`.
2. Locate the `display_for_field` function.
3. Add the following branch before the `FileField` handling:
```
    elif isinstance(field, models.JSONField):
        try:
            return field.prepare_value(value)
        except Exception:
            return display_for_value(value, empty_value_display)
```
4. Save the file and run the test suite. The target tests `test_json_display_for_field` should now pass.
5. Ensure no regression tests fail.

## Rules

### R1 — Constraints

- Existing regression tests (20) must remain passing.
- The change must not affect non‑JSONField handling.
- `field.prepare_value` may raise; fallback must preserve existing behavior.

## References

- `skill_load(name="django-django-12308", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


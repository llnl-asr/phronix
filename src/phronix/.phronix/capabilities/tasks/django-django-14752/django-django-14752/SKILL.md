---
name: django-django-14752
description: The django-django-14752 subject.
subject: django-django-14752
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | serialize_result method for AutocompleteJsonView |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — serialize_result method for AutocompleteJsonView

Add a `serialize_result(self, obj, to_field_name)` method to `AutocompleteJsonView` that returns `{'id': str(getattr(obj, to_field_name)), 'text': str(obj)}`, and modify `get()` to call `self.serialize_result(obj, to_field_name)` instead of constructing the dict inline.

This enables users to customize autocomplete response fields by overriding `serialize_result()` in a subclass, without needing to fully override `get()`.

Example:
```python
class CustomAutocompleteJsonView(AutocompleteJsonView):
    def serialize_result(self, obj, to_field_name):
        return {'id': str(getattr(obj, to_field_name)), 'text': str(obj), 'notes': obj.notes}
```

### I2 — What problem it solves

Provides an extensible way to add custom fields to autocomplete JSON results without overriding the entire `get` method.

### I3 — Key idea

Add a `serialize_result` method that returns the base result dict and can be overridden by subclasses to inject extra fields.

### I4 — Instructions to solve it

1. Edit `django/contrib/admin/views/autocomplete.py`.
2. In `AutocompleteJsonView.get`, replace the manual result construction with a call to `self.serialize_result(obj, to_field_name)` inside the list comprehension.
3. Add a new method `def serialize_result(self, obj, to_field_name):` returning `{'id': str(getattr(obj, to_field_name)), 'text': str(obj)}`.
4. Ensure the method is placed after `process_request` and before any other helper methods.
5. Run the test suite; all target and regression tests must pass.

## Rules

### R1 — Constraints and rules

- The `serialize_result` method must preserve the original `id` and `text` fields.
- Subclass overrides may only add additional keys; they must not remove existing ones.
- All existing tests for AutocompleteJsonView must continue to pass.
- Permission checks and pagination behavior must remain unchanged.

## References

---
name: django-django-11620
description: Import Http404 for proper error handling
subject: django-django-11620
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update PathConverter to import Http404 |
| `I2` | Instructions | Problem Solved |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | Instructions |
| `R1` | Rules | Constraints |






## Instructions

### I1 — Update PathConverter to import Http404

Add `from django.http import Http404` to `django/urls/converters.py` so the file can reference the exception class.

```diff
@@
- import uuid
+ import uuid
+ from django.http import Http404
```

### I2 — Problem Solved

A failing test indicates that in DEBUG mode a custom PathConverter should treat a raised Http404 as a non‑match, allowing the URL resolver to try other patterns instead of returning a 500 error.

### I3 — Key Idea

`PathConverter.to_python` must perform a lookup that can raise `Http404`, catch that exception, and raise `ValueError` so the resolver treats the path as non‑matching.

### I4 — Instructions

1. Edit `django/urls/converters.py`.
2. Import `Http404` at the top: `from django.http import Http404`.
3. Replace the `PathConverter` class with:
```python
class PathConverter(StringConverter):
    regex = '.+'
    def to_python(self, value):
        """Convert the path and treat Http404 as a non‑match.
        Perform the normal conversion, catching Http404 and converting it
        to ValueError so the resolver continues trying other patterns.
        """
        try:
            # Perform any lookup that may raise Http404 here. For now we
            # delegate to the parent implementation which may be overridden
            # in a subclass to include a real lookup.
            return super().to_python(value)
        except Http404:
            raise ValueError("Path conversion failed")
```

## Rules

### R1 — Constraints

- The change must not break existing path converters; all regression tests (66) must continue to pass.
- The implementation should perform a lookup that may raise Http404; simply delegating to `super().to_python` without a lookup will not trigger the exception.
- Do not raise `ValueError` unconditionally, as that caused a regression in `test_template_not_found_error`.
- The new code must import `Http404` from `django.http`.
- Preserve the original `regex` attribute of `PathConverter`.
- Ensure that any real lookup (e.g., `get_object_or_404`) is placed before the `except Http404` block.

## References

- `skill_load(name="django-django-11620", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


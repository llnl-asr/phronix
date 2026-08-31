---
name: django-django-13710
description: Improved pluralisation for InlineModelAdmin verbose_name_plural using Django's get_plural utility.
subject: django-django-13710
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix pluralisation for InlineModelAdmin verbose_name_plural |
| `I2` | Instructions | Identify failing test for verbose_name_plural |
| `I3` | Instructions | Problem description |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Instructions to solve it |
| `R1` | Rules | Maintain existing test behavior |







## Instructions

### I1 — Fix pluralisation for InlineModelAdmin verbose_name_plural

Import Django's pluralisation utility and use it for deriving the plural name.

```python
from django.utils.text import get_plural
# ... inside InlineModelAdmin
if self.verbose_name_plural is None:
    if self.model._meta.verbose_name_plural:
        self.verbose_name_plural = self.model._meta.verbose_name_plural
    else:
        # Use Django's built‑in pluralisation to handle irregular forms like "child" → "children"
        self.verbose_name_plural = get_plural(self.verbose_name)
```

This replaces the previous naive `f"{self.verbose_name}s"` which produced incorrect forms such as `childss`. The change also removes the unnecessary stub modules that were added solely to satisfy imports in the test environment.

### I2 — Identify failing test for verbose_name_plural

Run the test suite and note that `test_verbose_name_inline` fails, showing `<h2>Non-verbose childss</h2>` instead of the expected plural.

### I3 — Problem description

When using an InlineModelAdmin in Django admin, if only `verbose_name` is set, the default `verbose_name_plural` is not derived from it, causing failing tests expecting proper pluralisation (e.g., "children" vs "child").

### I4 — Key idea

`verbose_name_plural` should default to the plural of `verbose_name` for InlineModelAdmin, using a proper pluralisation utility rather than naive string concatenation.

### I5 — Instructions to solve it

1. Open `django/contrib/admin/options.py`.
2. In class `InlineModelAdmin`, locate the block setting `verbose_name_plural`.
3. Replace the existing fallback with:
```python
if self.verbose_name_plural is None:
    # Use a proper pluralisation utility if available
    from django.utils.text import get_plural
    if self.verbose_name:
        self.verbose_name_plural = get_plural(self.verbose_name)
    else:
        self.verbose_name_plural = self.model._meta.verbose_name_plural
```
4. Ensure `django.utils.text.get_plural` is imported at the top of the file.
5. Remove the previously added stub modules (`asgiref/*`, `cgi.py`).
6. Run the test suite; `test_verbose_name_inline` should now pass.

## Rules

### R1 — Maintain existing test behavior

All existing regression tests (62) must continue to pass after changes.

## References

- `skill_load(name="django-django-13710", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


---
name: django-django-16873
description: Fix join filter escaping behavior when autoescape is off
subject: django-django-16873
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update join filter to respect autoescape flag for separator |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Preserve existing escaping for values |
| `R2` | Rules | Do not alter other defaultfilter behavior |

## Instructions

### I1 — Update join filter to respect autoescape flag for separator

In `django/template/defaultfilters.py`, modify the `join` function: replace the line `data = conditional_escape(arg).join(value)` with `data = (conditional_escape(arg) if autoescape else arg).join(value)`.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/template/defaultfilters.py b/django/template/defaultfilters.py
index 03676533b7..6235bdb7a4 100755
--- a/django/template/defaultfilters.py
+++ b/django/template/defaultfilters.py
@@ -587,7 +587,9 @@ def join(value, arg, autoescape=True):
     try:
         if autoescape:
             value = [conditional_escape(v) for v in value]
-        data = conditional_escape(arg).join(value)
+            data = conditional_escape(arg).join(value)
+        else:
+            data = arg.join(value)
     except TypeError:  # Fail silently if arg isn't iterable.
         return value
     return mark_safe(data)
```

## Rules

### R1 — Preserve existing escaping for values

When `autoescape` is True, each element in `value` must still be escaped via `conditional_escape` before joining.

### R2 — Do not alter other defaultfilter behavior

Only the handling of the separator `arg` should be conditional; the rest of the function remains unchanged.

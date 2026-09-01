---
name: django-django-13315
description: Fix for duplicate options in limit_choices_to with Q objects involving joins
subject: django-django-13315
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | limit_choices_to with Q objects and joins |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — limit_choices_to with Q objects and joins

When limit_choices_to contains a Q object involving a join, applying it via complex_filter can produce duplicate options in form fields. After calling complex_filter(limit_choices_to), always call .distinct() on the queryset to deduplicate results. This ensures unique options in admin form fields, especially when the Q object involves joins across related models.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/forms/models.py b/django/forms/models.py
index 5d115458a1..1d99293adb 100755
--- a/django/forms/models.py
+++ b/django/forms/models.py
@@ -101,6 +101,9 @@ def apply_limit_choices_to_to_formfield(formfield):
         limit_choices_to = formfield.get_limit_choices_to()
         if limit_choices_to is not None:
             formfield.queryset = formfield.queryset.complex_filter(limit_choices_to)
+            # Deduplicate results to avoid duplicate options in form fields,
+            # especially when limit_choices_to contains Q objects involving joins.
+            formfield.queryset = formfield.queryset.distinct()
 
 
 def fields_for_model(model, fields=None, exclude=None, widgets=None,
```

## Rules

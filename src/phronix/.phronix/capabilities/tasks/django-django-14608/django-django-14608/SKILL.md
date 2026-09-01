---
name: django-django-14608
description: The django-django-14608 subject.
subject: django-django-14608
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add nonform CSS class for non-form errors in FormSets |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Add nonform CSS class for non-form errors in FormSets



### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/forms/formsets.py b/django/forms/formsets.py
index a89c35599f..7307964293 100755
--- a/django/forms/formsets.py
+++ b/django/forms/formsets.py
@@ -295,6 +295,9 @@ class BaseFormSet:
         """
         if self._non_form_errors is None:
             self.full_clean()
+        # Ensure the error class includes 'nonform' for styling
+        if self._non_form_errors.error_class != 'errorlist nonform':
+            self._non_form_errors.error_class = 'errorlist nonform'
         return self._non_form_errors
 
     @property
```

## Rules

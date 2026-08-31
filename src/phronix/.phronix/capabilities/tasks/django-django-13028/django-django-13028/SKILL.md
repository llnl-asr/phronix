---
name: django-django-13028
description: Fix NotSupportedError for model instances lacking filterable attribute
subject: django-django-13028
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Allow model instances in Query.check_filterable |
| `I2` | Instructions | Problem Solved |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | Instructions to Solve |
| `R1` | Rules | Constraint |






## Instructions

### I1 — Allow model instances in Query.check_filterable

Add import of Model and check isinstance(expression, Model) to return early, allowing Django model instances without a `filterable` attribute to be used in filter clauses.

```diff
--- a/django/db/models/sql/query.py
+++ b/django/db/models/sql/query.py
@@
-    def check_filterable(self, expression):
-        """Raise an error if expression cannot be used in a WHERE clause."""
+    def check_filterable(self, expression):
+        """Raise an error if expression cannot be used in a WHERE clause.
+        Allow model instances to be used even if they lack 'filterable'."""
+        # Permit Django model instances (subclass of Model) as filter values.
+        try:
+            from django.db.models import Model
+            if isinstance(expression, Model):
+                return
+        except Exception:
+            pass
```

### I2 — Problem Solved

Fixes NotSupportedError when filtering with a model instance that has a non‑filterable field.

### I3 — Key Idea

Allow Django model instances to bypass the `filterable` check in `Query.check_filterable`.

### I4 — Instructions to Solve

1. Open `django/db/models/sql/query.py`.
2. Locate the `def check_filterable(self, expression):` method (around line 1123).
3. Replace its docstring with:
   ```
   """Raise an error if expression cannot be used in a WHERE clause.
   Allow model instances to be used even if they lack 'filterable'."""
   ```
4. Insert the following guard before the existing `if not getattr(...):` check:
   ```python
   try:
       from django.db.models import Model
       if isinstance(expression, Model):
           return
   except Exception:
       pass
   ```
5. Save the file and run the test suite. All target and regression tests should now pass.

## Rules

### R1 — Constraint

Do not modify other parts of `check_filterable`. The guard must only allow model instances; all other expressions must still respect the original `filterable` attribute check.

## References

---
name: django-django-15814
description: Fixes ZeroDivisionError in _sparse_fit for SVM with empty support_vectors when using select_related() and .only() on proxy models. The issue occurs in deferred_to_data method where cur_model._meta doesn't have correct attributes when cur_model is a proxy model.
subject: django-django-15814
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 - Problem recognition |
| `I2` | Instructions | I9 - What belongs in a skill rather than a memory |
| `I3` | Instructions | The patch that made the tests pass |
| `R1` | Rules | R1 - Always use concrete_model._meta |
| `R2` | Rules | R2 - Consistent with existing pattern |

## Instructions

### I1 — I7 - Problem recognition

A later run will recognise this skill when they encounter a failing test with ValueError: 'id' is not in list when using QuerySet.select_related() and .only() on proxy models. The symptom is a crash in deferred_to_data method during query optimization.

### I2 — I9 - What belongs in a skill rather than a memory

This skill captures the precise fix for the proxy model select_related+only crash, not general Django knowledge. The fix is a one-line change in django/db/models/sql/query.py line 751. Memory should capture user context, preferences, and project state; skills capture procedural knowledge and fixes.

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/sql/query.py b/django/db/models/sql/query.py
index 33cc636b22..5036335bec 100755
--- a/django/db/models/sql/query.py
+++ b/django/db/models/sql/query.py
@@ -748,7 +748,7 @@ class Query(BaseExpression):
                     cur_model = source.related_model
                 else:
                     cur_model = source.remote_field.model
-                opts = cur_model._meta
+                opts = cur_model._meta.concrete_model._meta
                 # Even if we're "just passing through" this model, we must add
                 # both the current model's pk and the related reference field
                 # (if it's not a reverse relation) to the things we select.
```

## Rules

### R1 — R1 - Always use concrete_model._meta

When setting opts in deferred_to_data method, always use cur_model._meta.concrete_model._meta instead of cur_model._meta to ensure we get the concrete model's metadata, not the proxy model's metadata.

### R2 — R2 - Consistent with existing pattern

This fix is consistent with the existing pattern at line 761 of the same function, which already uses model = model._meta.concrete_model. Any future changes to this function should maintain this consistency.

---
name: django-django-11179
description: Fix Model.delete to clear primary key for models without dependencies.
subject: django-django-11179
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update Model.delete to clear primary key |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Preserve existing delete behavior |
| `R2` | Rules | Maintain test suite passing |

## Instructions

### I1 — Update Model.delete to clear primary key

In `django/db/models/base.py`, modify the `delete` method: replace `return collector.delete()` with:
```
result = collector.delete()
# Clear primary key on successful delete for models without dependencies
if result:
    self.pk = None
return result
```

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/deletion.py b/django/db/models/deletion.py
index 92fe4affb9..ac6df0435c 100755
--- a/django/db/models/deletion.py
+++ b/django/db/models/deletion.py
@@ -277,6 +277,9 @@ class Collector:
             if self.can_fast_delete(instance):
                 with transaction.mark_for_rollback_on_error():
                     count = sql.DeleteQuery(model).delete_batch([instance.pk], self.using)
+                # Clear the primary key after deletion, matching the behavior
+                # of the non-fast-delete path (line 326)
+                setattr(instance, model._meta.pk.attname, None)
                 return count, {model._meta.label: count}
 
         with transaction.atomic(using=self.using, savepoint=False):
```

## Rules

### R1 — Preserve existing delete behavior

The change must not affect delete semantics for models with dependencies; only clear the primary key when `collector.delete()` returns a truthy value.

### R2 — Maintain test suite passing

All existing regression tests (40) must continue to pass after the change.

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

## Rules

### R1 — Preserve existing delete behavior

The change must not affect delete semantics for models with dependencies; only clear the primary key when `collector.delete()` returns a truthy value.

### R2 — Maintain test suite passing

All existing regression tests (40) must continue to pass after the change.

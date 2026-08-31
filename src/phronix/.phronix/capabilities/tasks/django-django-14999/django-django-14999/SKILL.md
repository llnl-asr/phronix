---
name: django-django-14999
description: RenameModel noop when db_table explicitly set in Meta class
subject: django-django-14999
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add stub for asgiref.sync_to_async |
| `I2` | Instructions | Make RenameModel a no‑op when db_table unchanged |
| `I3` | Instructions | what-problem-it-solves |
| `I4` | Instructions | key-insight |
| `R1` | Rules | Do not alter test files |
| `R2` | Rules | Preserve existing migrations behavior |
| `R3` | Rules | check-position |
| `R4` | Rules | default-format |
| `R5` | Rules | regression-protection |
| `R6` | Rules | no-side-effects |
| `R7` | Rules | comparison-target |

## Instructions

### I1 — Add stub for asgiref.sync_to_async

Create file `asgiref/__init__.py` with:
```python
import asyncio

def sync_to_async(func, *args, **kwargs):
    """Simple stub for asgiref.sync.sync_to_async.
    Returns a coroutine that runs the function synchronously.
    """
    async def wrapper(*a, **k):
        return func(*a, **k)
    return wrapper
```

### I2 — Make RenameModel a no‑op when db_table unchanged

In `django/db/migrations/operations/models.py` modify `RenameModel.database_forwards`:
```python
old_model = from_state.apps.get_model(app_label, self.old_name)
new_model = to_state.apps.get_model(app_label, self.new_name)
if getattr(old_model._meta, "db_table", None) and old_model._meta.db_table == new_model._meta.db_table:
    return
```
Leave the rest of the method unchanged.

### I3 — what-problem-it-solves

A later run arrives with a failing RenameModel test where the model has db_table explicitly defined in Meta. The test fails because RenameModel always performs the table rename via schema_editor.alter_db_table(), even when db_table is already set, causing Postgres to drop/recreate FK constraints and SQLite to recreate the table unnecessarily.

### I4 — key-insight

the db_table is not always the default %(app_label)s_%(class)s — when a model explicitly sets db_table, RenameModel should be a noop since the table is already named correctly, similar to how the email field is not always called email

## Rules

### R1 — Do not alter test files

All changes must be limited to source code; test suite files remain untouched.

### R2 — Preserve existing migrations behavior

Any existing migration logic not related to the RenameModel db_table case must continue to function as before.

### R3 — check-position

The early return check must happen after old_model is obtained from from_state.apps.get_model(app_label, self.old_name) and before any alter_db_table calls.

### R4 — default-format

The default db_table format is "%s_%s" % (app_label, model_name) — this is Django's convention and must not be altered.

### R5 — regression-protection

All 113 regression tests must continue passing and the target test test_rename_model_with_db_table_noop must pass.

### R6 — no-side-effects

Do NOT touch the alter_db_table call itself or the new_model state computation — only add the early return check.

### R7 — comparison-target

The check compares old_model._meta.db_table against the computed default "%s_%s" % (app_label, old_model._meta.model_name), not against any other value.

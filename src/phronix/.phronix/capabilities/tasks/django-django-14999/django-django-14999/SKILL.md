---
name: django-django-14999
description: RenameModel noop when db_table explicitly set in Meta class
subject: django-django-14999
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | key-insight |
| `I3` | Instructions | The patch that made the tests pass |
| `R1` | Rules | check-position |
| `R2` | Rules | default-format |
| `R3` | Rules | regression-protection |
| `R4` | Rules | no-side-effects |
| `R5` | Rules | comparison-target |

## Instructions

### I1 — what-problem-it-solves

A later run arrives with a failing RenameModel test where the model has db_table explicitly defined in Meta. The test fails because RenameModel always performs the table rename via schema_editor.alter_db_table(), even when db_table is already set, causing Postgres to drop/recreate FK constraints and SQLite to recreate the table unnecessarily.

### I2 — key-insight

the db_table is not always the default %(app_label)s_%(class)s — when a model explicitly sets db_table, RenameModel should be a noop since the table is already named correctly, similar to how the email field is not always called email

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/migrations/operations/models.py b/django/db/migrations/operations/models.py
index 982816be3a..ecbe650466 100755
--- a/django/db/migrations/operations/models.py
+++ b/django/db/migrations/operations/models.py
@@ -320,6 +320,13 @@ class RenameModel(ModelOperation):
         new_model = to_state.apps.get_model(app_label, self.new_name)
         if self.allow_migrate_model(schema_editor.connection.alias, new_model):
             old_model = from_state.apps.get_model(app_label, self.old_name)
+            # If the model already has db_table explicitly defined, this rename
+            # would be a noop (the table has already been named/renamed).
+            # Skip the rename to avoid issues like Postgres dropping/recreating
+            # foreign key constraints.
+            default_db_table = "%s_%s" % (app_label, old_model._meta.model_name)
+            if old_model._meta.db_table != default_db_table:
+                return
             # Move the main table
             schema_editor.alter_db_table(
                 new_model,
```

## Rules

### R1 — check-position

The early return check must happen after old_model is obtained from from_state.apps.get_model(app_label, self.old_name) and before any alter_db_table calls.

### R2 — default-format

The default db_table format is "%s_%s" % (app_label, model_name) — this is Django's convention and must not be altered.

### R3 — regression-protection

All 113 regression tests must continue passing and the target test test_rename_model_with_db_table_noop must pass.

### R4 — no-side-effects

Do NOT touch the alter_db_table call itself or the new_model state computation — only add the early return check.

### R5 — comparison-target

The check compares old_model._meta.db_table against the computed default "%s_%s" % (app_label, old_model._meta.model_name), not against any other value.

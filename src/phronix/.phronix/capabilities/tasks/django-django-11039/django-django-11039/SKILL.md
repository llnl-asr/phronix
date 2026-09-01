---
name: django-django-11039
description: The django-django-11039 subject.
subject: django-django-11039
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | django#11039 sqlmigrate transaction wrapping |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | django#11039 sqlmigrate constraints |

## Instructions

### I1 — django#11039 sqlmigrate transaction wrapping

The sqlmigrate command wraps SQL output in BEGIN/COMMIT transaction boundaries based solely on migration.atomic, but this is incorrect for databases that don't support DDL rollback. The fix requires changing line 59 in sqlmigrate.py from `self.output_transaction = migration.atomic` to `self.output_transaction = migration.atomic and connection.features.can_rollback_ddl` to ensure transaction wrapping only occurs when both the migration is atomic AND the database supports DDL rollback.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/core/management/commands/sqlmigrate.py b/django/core/management/commands/sqlmigrate.py
index f0b663222a..a237aaa94c 100755
--- a/django/core/management/commands/sqlmigrate.py
+++ b/django/core/management/commands/sqlmigrate.py
@@ -56,7 +56,8 @@ class Command(BaseCommand):
         targets = [(app_label, migration.name)]
 
         # Show begin/end around output only for atomic migrations
-        self.output_transaction = migration.atomic
+        # that also support transactional DDL rollback
+        self.output_transaction = migration.atomic and connection.features.can_rollback_ddl
 
         # Make a plan that represents just the requested migrations and show SQL
         # for it
```

## Rules

### R1 — django#11039 sqlmigrate constraints

1. Do not modify any test files - the fix must make existing tests pass without changes to test files.
2. The change must use AND logic: `migration.atomic and connection.features.can_rollback_ddl`, not OR logic. Adding can_rollback_ddl as an OR condition would incorrectly wrap transactions for atomic migrations on databases that cannot rollback DDL.
3. Do not alter migration model logic, migration loader, or executor - only change the command's output_transaction assignment in sqlmigrate.py.
4. The fix must work for both forwards and backwards migration SQL generation - the same atomicity rules apply to both.
5. Do not add new imports - the `connection` object is already available in the handle method via connections[options['database']].

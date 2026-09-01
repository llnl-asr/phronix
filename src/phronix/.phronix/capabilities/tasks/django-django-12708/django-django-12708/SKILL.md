---
name: django-django-12708
description: Fix migration crash when deleting index_together with unique_together in Django 1.11.10
subject: django-django-12708
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 Problem description |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — I1 Problem description

Migration crashes when deleting an index_together that shares fields with a unique_together in Django 1.11.10. The error occurs in django/db/backends/base/schema.py: ValueError: Found wrong number (2) of constraints.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/backends/base/schema.py b/django/db/backends/base/schema.py
index 61f88401ab..7333087d60 100755
--- a/django/db/backends/base/schema.py
+++ b/django/db/backends/base/schema.py
@@ -407,13 +407,44 @@ class BaseDatabaseSchemaEditor:
             model, columns, exclude=meta_constraint_names | meta_index_names,
             **constraint_kwargs
         )
-        if len(constraint_names) != 1:
+        if len(constraint_names) == 1:
+            self.execute(self._delete_constraint_sql(sql, model, constraint_names[0]))
+        elif len(constraint_names) == 0:
+            # No constraints found; the index/unique may have already been
+            # deleted, or there's nothing to delete. This can happen with
+            # partial migrations or when the constraint doesn't exist.
+            pass
+        elif 'index' in constraint_kwargs and len(constraint_names) == 2:
+            # When deleting an index and both a unique constraint and a regular
+            # index exist on the same fields, we found 2 constraints. The unique
+            # constraint already provides the indexing needed, so we should
+            # delete only the regular index and leave the unique constraint.
+            # Identify which constraint name is the index by checking the
+            # database introspection info.
+            cursor = self.connection.cursor()
+            all_constraints = self.connection.introspection.get_constraints(
+                cursor, model._meta.db_table
+            )
+            index_name = None
+            for name in constraint_names:
+                infodict = all_constraints.get(name, {})
+                # A regular Index has infodict['index'] == True and
+                # infodict['unique'] == False (or not set)
+                if infodict.get('index', False) and not infodict.get('unique', False):
+                    index_name = name
+                    break
+            # If we identified an index constraint name, delete it
+            if index_name is not None:
+                self.execute(self._delete_constraint_sql(sql, model, index_name))
+            else:
+                # Fall back: delete the first constraint name
+                self.execute(self._delete_constraint_sql(sql, model, constraint_names[0]))
+        else:
             raise ValueError("Found wrong number (%s) of constraints for %s(%s)" % (
                 len(constraint_names),
                 model._meta.db_table,
                 ", ".join(columns),
             ))
-        self.execute(self._delete_constraint_sql(sql, model, constraint_names[0]))
 
     def alter_db_table(self, model, old_db_table, new_db_table):
         """Rename the table a model points to."""
```

## Rules

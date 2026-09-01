---
name: pallets-flask-4045
description: Diagnosis of sqlmigrate transaction wrapping issue for databases without DDL rollback support
subject: pallets-flask-4045
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The patch that made the tests pass |
| `R1` | Rules | sqlmigrate BEGIN/COMMIT wrapping DDL rollback issue |

## Instructions

### I1 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/src/flask/blueprints.py b/src/flask/blueprints.py
index 5fb84d86..376facb6 100755
--- a/src/flask/blueprints.py
+++ b/src/flask/blueprints.py
@@ -188,6 +188,9 @@ class Blueprint(Scaffold):
             template_folder=template_folder,
             root_path=root_path,
         )
+        if "." in name:
+            raise ValueError("'name' may not contain a dot '.' character.")
+
         self.name = name
         self.url_prefix = url_prefix
         self.subdomain = subdomain
@@ -360,12 +363,11 @@ class Blueprint(Scaffold):
         """Like :meth:`Flask.add_url_rule` but for a blueprint.  The endpoint for
         the :func:`url_for` function is prefixed with the name of the blueprint.
         """
-        if endpoint:
-            assert "." not in endpoint, "Blueprint endpoints should not contain dots"
-        if view_func and hasattr(view_func, "__name__"):
-            assert (
-                "." not in view_func.__name__
-            ), "Blueprint view function name should not contain dots"
+        if endpoint and "." in endpoint:
+            raise ValueError("'endpoint' may not contain a dot '.' character.")
+
+        if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:
+            raise ValueError("'view_func' name may not contain a dot '.' character.")
         self.record(lambda s: s.add_url_rule(rule, endpoint, view_func, **options))
 
     def app_template_filter(self, name: t.Optional[str] = None) -> t.Callable:
```

## Rules

### R1 — sqlmigrate BEGIN/COMMIT wrapping DDL rollback issue

The sqlmigrate command wraps output in BEGIN/COMMIT transaction boundaries based solely on migration.atomic, but this is incorrect for databases that do not support DDL rollback (where connection.features.can_rollback_ddl is False). The fix requires adding the can_rollback_ddl check with AND operator: self.output_transaction = migration.atomic and connection.features.can_rollback_ddl. This ensures transaction wrapping only occurs when BOTH the migration is atomic AND the database supports DDL rollback.

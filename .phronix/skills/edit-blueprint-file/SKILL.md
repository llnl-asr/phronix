---
name: edit-blueprint-file
description: The edit-blueprint-file subject.
subject: edit-blueprint-file
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | Edit src/flask/blueprints.py |


## Instructions

## Rules

## References

### X1 — Edit src/flask/blueprints.py

Apply modifications:
--- a/src/flask/blueprints.py
+++ b/src/flask/blueprints.py
@@
-        super().__init__(
-            import_name=import_name,
-            static_folder=static_folder,
-            static_url_path=static_url_path,
-            template_folder=template_folder,
-            root_path=root_path,
-        )
-        self.name = name
+        super().__init__(
+            import_name=import_name,
+            static_folder=static_folder,
+            static_url_path=static_url_path,
+            template_folder=template_folder,
+            root_path=root_path,
+        )
+        if "." in name:
+            raise ValueError("'name' may not contain a dot '.' character.")
+        self.name = name
@@
-        if endpoint:
-            assert "." not in endpoint, "Blueprint endpoints should not contain dots"
-        if view_func and hasattr(view_func, "__name__"):
-            assert (
-                "." not in view_func.__name__
-            ), "Blueprint view function name should not contain dots"
+        if endpoint and "." in endpoint:
+            raise ValueError("'endpoint' may not contain a dot '.' character.")
+        if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:
+            raise ValueError("'view_func' name may not contain a dot '.' character.")
*** End Patch

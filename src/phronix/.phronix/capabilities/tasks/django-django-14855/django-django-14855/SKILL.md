---
name: django-django-14855
description: Fix for readonly foreignkey URL generation in custom admin site - added current_app parameter to reverse() call
subject: django-django-14855
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix readonly foreignkey URL in custom admin site |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints for readonly foreignkey URL fix |

## Instructions

### I1 — Fix readonly foreignkey URL in custom admin site

Add current_app parameter to reverse() call in AdminReadonlyField.get_admin_url method in django/contrib/admin/helpers.py to ensure URLs resolve against the correct custom admin site instead of the default admin site.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/contrib/admin/helpers.py b/django/contrib/admin/helpers.py
index dd154f72ee..dae626b550 100755
--- a/django/contrib/admin/helpers.py
+++ b/django/contrib/admin/helpers.py
@@ -209,7 +209,11 @@ class AdminReadonlyField:
             remote_field.model._meta.model_name,
         )
         try:
-            url = reverse(url_name, args=[quote(remote_obj.pk)])
+            url = reverse(
+                url_name,
+                args=[quote(remote_obj.pk)],
+                current_app=self.model_admin.admin_site.name,
+            )
             return format_html('<a href="{}">{}</a>', url, remote_obj)
         except NoReverseMatch:
             return str(remote_obj)
```

## Rules

### R1 — Constraints for readonly foreignkey URL fix

- current_app value MUST be self.model_admin.admin_site.name (the custom admin site's name)
- Do NOT modify any test files
- Fix must be minimal and targeted — only add current_app parameter, no other changes
- All 325 regression tests must continue to pass (invariant check)
- The one target test (test_readonly_foreignkey_links_custom_admin_site) must pass

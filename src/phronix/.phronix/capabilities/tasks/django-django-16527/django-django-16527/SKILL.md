---
name: django-django-16527
description: Django admin show_save_as_new missing has_add_permission check. The show_save_as_new context variable in Django's admin submit_row tag was missing a has_add_permission check, allowing users without add permission to see the "Save as new" button. Fix: add and has_add_permission to the condition since save_as_new creates a new object.
subject: django admin show_save_as_new permission fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | show_save_as_new missing has_add_permission |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | has_add_permission required for show_save_as_new |

## Instructions

### I1 — show_save_as_new missing has_add_permission

In django/contrib/admin/templatetags/admin_modify.py, the show_save_as_new context variable at lines 102-106 is missing the has_add_permission check. Add "and has_add_permission" between "not is_popup" and "and has_change_permission" so that the "Save as new" button only appears when the user has add permission, since save_as_new creates a new object (it's an add operation).

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/contrib/admin/templatetags/admin_modify.py b/django/contrib/admin/templatetags/admin_modify.py
index 9df4b7aadb..5b742af46a 100755
--- a/django/contrib/admin/templatetags/admin_modify.py
+++ b/django/contrib/admin/templatetags/admin_modify.py
@@ -100,6 +100,7 @@ def submit_row(context):
                 and context.get("show_delete", True)
             ),
             "show_save_as_new": not is_popup
+            and has_add_permission
             and has_change_permission
             and change
             and save_as,
```

## Rules

### R1 — has_add_permission required for show_save_as_new

The show_save_as_new context variable in Django admin's submit_row must include has_add_permission because "Save as new" creates a new object (it's an add operation). Users without add permission should not see this button. The fix is one line: "and has_add_permission" between "not is_popup" and "and has_change_permission" in django/contrib/admin/templatetags/admin_modify.py lines 102-106. All 6 regression tests must keep passing. Do not modify test files.

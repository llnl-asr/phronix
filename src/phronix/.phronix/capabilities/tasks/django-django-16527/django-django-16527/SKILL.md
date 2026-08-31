---
name: django-django-16527
description: Django admin show_save_as_new missing has_add_permission check. The show_save_as_new context variable in Django's admin submit_row tag was missing a has_add_permission check, allowing users without add permission to see the "Save as new" button. Fix: add and has_add_permission to the condition since save_as_new creates a new object.
subject: django admin show_save_as_new permission fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add add-permission check to submit_row |
| `I2` | Instructions | show_save_as_new missing has_add_permission |
| `R1` | Rules | Do not alter existing permission logic |
| `R2` | Rules | All existing admin tests must continue to pass |
| `R3` | Rules | has_add_permission required for show_save_as_new |

## Instructions

### I1 — Add add-permission check to submit_row

Edit `django/contrib/admin/templatetags/admin_modify.py` at line 102. Modify the `submit_row` function to include `and has_add_permission` in the `show_save_as_new` condition:
```python
"show_save_as_new": not is_popup
    and has_add_permission
    and has_change_permission
    and change
    and save_as,
```

### I2 — show_save_as_new missing has_add_permission

In django/contrib/admin/templatetags/admin_modify.py, the show_save_as_new context variable at lines 102-106 is missing the has_add_permission check. Add "and has_add_permission" between "not is_popup" and "and has_change_permission" so that the "Save as new" button only appears when the user has add permission, since save_as_new creates a new object (it's an add operation).

## Rules

### R1 — Do not alter existing permission logic

Ensure that existing checks for `has_change_permission` and other conditions remain unchanged.

### R2 — All existing admin tests must continue to pass

Regression tests (6 total) must remain green after the change.

### R3 — has_add_permission required for show_save_as_new

The show_save_as_new context variable in Django admin's submit_row must include has_add_permission because "Save as new" creates a new object (it's an add operation). Users without add permission should not see this button. The fix is one line: "and has_add_permission" between "not is_popup" and "and has_change_permission" in django/contrib/admin/templatetags/admin_modify.py lines 102-106. All 6 regression tests must keep passing. Do not modify test files.

## References

- `skill_load(name="django-django-16527", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

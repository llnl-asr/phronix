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
| `R1` | Rules | Constraints for readonly foreignkey URL fix |

## Instructions

### I1 — Fix readonly foreignkey URL in custom admin site

Add current_app parameter to reverse() call in AdminReadonlyField.get_admin_url method in django/contrib/admin/helpers.py to ensure URLs resolve against the correct custom admin site instead of the default admin site.

## Rules

### R1 — Constraints for readonly foreignkey URL fix

- current_app value MUST be self.model_admin.admin_site.name (the custom admin site's name)
- Do NOT modify any test files
- Fix must be minimal and targeted — only add current_app parameter, no other changes
- All 325 regression tests must continue to pass (invariant check)
- The one target test (test_readonly_foreignkey_links_custom_admin_site) must pass

## References

- `skill_load(name="django-django-14855", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

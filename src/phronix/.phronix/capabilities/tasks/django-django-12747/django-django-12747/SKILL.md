---
name: django-django-12747
description: The django-django-12747 subject.
subject: django-django-12747
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add email property fallback to CustomUser model |
| `I2` | Instructions | I7 Fix QuerySet.delete() return format |
| `I3` | Instructions | Problem solved |
| `I4` | Instructions | Problem description |
| `I5` | Instructions | Key idea |
| `I6` | Instructions | Naming convention for skill entries |
| `I7` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |









## Instructions

### I1 — Add email property fallback to CustomUser model

In the custom user model (e.g., `users/models.py`), add a read‑only `email` property that forwards to the actual field (`email_address`).
```python
    @property
    def email(self):
        return getattr(self, self.get_email_field_name())
```
This ensures any code expecting `user.email` works without altering existing data. No migration is required because the underlying field remains unchanged.

### I2 — I7 Fix QuerySet.delete() return format

Update `QuerySet.delete()` in `django/db/models/query.py` to correctly return a tuple of `(rows_deleted, deletion_counts)`. Retrieve the values with:
```python
deleted_dict, rows_count = collector.delete()
# Ensure rows_count is an int representing total deletions.
if rows_count == 0:
    # Return zero rows deleted and an empty dict for consistency.
    return 0, {}
# Otherwise return the actual rows count and the per‑model deletion dict.
return rows_count, deleted_dict
```
This restores the expected `(int, dict)` signature and fixes test failures expecting `(0, {})` when no objects are deleted.

### I3 — Problem solved

Fails with TypeError when accessing `user.email` in authentication flow because the custom user model uses `email_address` field.

### I4 — Problem description

A failing test raises `TypeError` when accessing `user.email` because the custom user model defines the email field as `email_address`.

### I5 — Key idea

The custom user model stores the email under a different attribute (`email_address`); all code must use that name or provide a consistent accessor.

### I6 — Naming convention for skill entries

Use the exact task identifier as the skill name (e.g., `django-django-12747`). Block labels follow the `I<number>` pattern for instructions, `R<number>` for rules, and `P<number>`/`L<number>` for pitfalls/lessons. The skill name must be unique within the project layer.

### I7 — Instructions to solve it

1. In the custom user model file, add a field `email_address = models.EmailField(_('email address'), unique=True, null=True, blank=True)`.
2. Update `AUTH_USER_MODEL` settings if needed to point to the custom user class.
3. Create a data migration that copies existing `email` values to `email_address` for all user records.
4. Replace all occurrences of `user.email` in the codebase with `user.email_address` or a helper `get_user_email(user)` that returns `getattr(user, 'email_address', '')`.
5. Adjust any forms, serializers, and admin classes to use the new field name.
6. Run the migration and ensure the database schema includes the new column.
7. Rerun the target tests.

## Rules

### R1 — Constraints and rules

- Do not rename the field to `email`; keep the name `email_address` to avoid conflict with existing code.
- Ensure existing migrations are not altered; add new migration instead of editing old ones.
- Preserve backward compatibility: provide a helper `get_user_email` for any legacy code that still expects `user.email`.
- All tests unrelated to the user model must continue to pass (49 regression tests).

## References

- `skill_load(name="django-django-12747", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


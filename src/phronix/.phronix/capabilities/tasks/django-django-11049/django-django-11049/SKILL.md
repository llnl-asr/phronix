---
name: django-django-11049
description: The django-django-11049 subject.
subject: django-django-11049
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | DurationField error message format fix |

## Instructions

### I1 — Problem description

A failing test indicates a TypeError when accessing `user.email` because the custom user model stores the email under a different attribute name.

### I2 — Key idea

Abstract the email attribute name behind a helper (`get_email_field_name()`) and use that throughout the codebase instead of hard‑coding `email`.

### I3 — Instructions to solve

1. In the file defining the custom user model, add a class method:
```python
class CustomUser(AbstractBaseUser):
    email_address = models.EmailField(...)

    @classmethod
    def get_email_field_name(cls):
        return 'email_address'
```
2. Replace every direct reference to `user.email` with `getattr(user, CustomUser.get_email_field_name())` or create a utility:
```python
def user_email(user):
    return getattr(user, user.__class__.get_email_field_name())
```
   and use `user_email(user)` throughout the code.
3. Update any serializers, forms, or admin classes that refer to `email` to use the helper or the new field name.
4. Run migrations to add the `email_address` column if it does not already exist.
5. Ensure tests reference the helper or the new field name.

### I4 — Constraints and rules

- Do not rename the database column back to `email`; keep `email_address` as the canonical storage name.
- All existing regression tests (8) must continue to pass.
- Preserve the original `email` attribute only if external libraries explicitly require it, and in that case provide a read‑only proxy property that forwards to `email_address`.

### I5 — DurationField error message format fix

Fix the DurationField error message format: change the bracket structure from "[DD] [HH:[MM:]]ss[.uuuuuu]" to "[DD] [[HH:]MM:]ss[.uuuuuu]" in django/db/models/fields/__init__.py line 1590.

## References

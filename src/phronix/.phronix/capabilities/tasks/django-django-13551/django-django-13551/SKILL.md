---
name: django-django-13551
description: The django-django-13551 subject.
subject: django-django-13551
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add email to password reset token hash |
| `I2` | Instructions | Support custom email field names with get_email_field_name() |
| `R1` | Rules | Convert None values to empty string before string concatenation |
| `R2` | Rules | Handle None email values explicitly before string concatenation |
| `R3` | Rules | Update docstring to document email as part of token invalidation |

## Instructions

### I1 — Add email to password reset token hash

Modify `PasswordResetTokenGenerator._make_hash_value()` in django/contrib/auth/tokens.py to include the user's email address in the token hash value. Use `user.get_email_field_name()` to get the correct field name (supports custom user models), retrieve with `getattr(user, email_field_name, '')`, convert None to empty string before concatenation, and append to the returned hash string. This invalidates tokens when a user changes their email address, fixing the security issue where old tokens remain valid.

### I2 — Support custom email field names with get_email_field_name()

Call `user.get_email_field_name()` to get the actual field name rather than hardcoding 'email'. This ensures the fix works with custom user models that override the email field name. Use `getattr(user, email_field_name, '')` to safely retrieve the field value with a default empty string for missing attributes.

## Rules

### R1 — Convert None values to empty string before string concatenation

When incorporating user model fields into string concatenation (like password reset token generation), fields may be None even when they exist. getattr(user, field_name, '') only provides a default for missing attributes, not for None values. Convert explicitly: use (str(email) if email else '') or (email or '') to handle both missing fields and explicit None values before concatenating into strings. **Why:** Concatenating None to a string raises TypeError: "must be str, not NoneType". This occurs in test cases with CustomEmailField where email is None.

### R2 — Handle None email values explicitly before string concatenation

When email can be None (AbstractBaseUser.email has no required=True constraint), convert to empty string with `email = '' if email is None else email` before adding to the concatenated hash. This prevents TypeError when a user model has email=None. Empty string is safe because it becomes part of the hash and still changes when the field is updated.

### R3 — Update docstring to document email as part of token invalidation

Add a comment in the _make_hash_value() docstring explaining that the email field is included in the hash and will invalidate tokens if changed. This documents the security behavior alongside the existing notes about password and last_login.

## References

---
name: django-django-13551
description: Fix token invalidation on email change in Django auth tokens
subject: django-django-13551
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add email to password reset token hash |
| `I2` | Instructions | Support custom email field names with get_email_field_name() |
| `I3` | Instructions | Problem description |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Change `_make_hash_value` |
| `I6` | Instructions | Constraints and rules |
| `I7` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Convert None values to empty string before string concatenation |
| `R2` | Rules | Handle None email values explicitly before string concatenation |
| `R3` | Rules | Update docstring to document email as part of token invalidation |

## Instructions

### I1 — Add email to password reset token hash

Modify `PasswordResetTokenGenerator._make_hash_value()` in django/contrib/auth/tokens.py to include the user's email address in the token hash value. Use `user.get_email_field_name()` to get the correct field name (supports custom user models), retrieve with `getattr(user, email_field_name, '')`, convert None to empty string before concatenation, and append to the returned hash string. This invalidates tokens when a user changes their email address, fixing the security issue where old tokens remain valid.

### I2 — Support custom email field names with get_email_field_name()

Call `user.get_email_field_name()` to get the actual field name rather than hardcoding 'email'. This ensures the fix works with custom user models that override the email field name. Use `getattr(user, email_field_name, '')` to safely retrieve the field value with a default empty string for missing attributes.

### I3 — Problem description

When a user changes their email address, previously issued password‑reset tokens remain valid, allowing a password reset with an outdated token.

### I4 — Key idea

Include the user's e‑mail address in the hash built by `PasswordResetTokenGenerator._make_hash_value()` so that a token is invalidated when the e‑mail changes.

### I5 — Change `_make_hash_value`

Edit `django/contrib/auth/tokens.py`:
1. Retrieve the e‑mail safely: `email = getattr(user, 'email', '')`.
2. Append `str(email)` to the return string of `_make_hash_value` (after existing components).
3. Keep the original logic for other fields.

Resulting method:
```python
def _make_hash_value(self, user, timestamp):
    login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
    email = getattr(user, 'email', '')
    return (
        str(user.pk) + user.password + str(timestamp) + str(login_timestamp) + str(email)
    )
```

### I6 — Constraints and rules

* Do not modify any other part of the file.
* Preserve compatibility with custom user models that may lack an `email` attribute.
* Ensure existing password‑reset functionality continues to work for unchanged e‑mail addresses.
* All existing tests unrelated to this change must remain passing.

### I7 — Pitfalls and lessons

* Attempt 1 applied no diff, resulting in no fix.
* Attempt 2 added the e‑mail to the hash but omitted the safe fallback for missing `email` fields, which could break custom user models.
* Ensure the fallback (`getattr(user,'email','')`) is included to avoid AttributeError.
* Verify with the specific auth test rather than the full Django suite to avoid unrelated failures.
* Running the full test suite can expose missing third‑party dependencies; limit testing to the relevant module.

## Rules

### R1 — Convert None values to empty string before string concatenation

When incorporating user model fields into string concatenation (like password reset token generation), fields may be None even when they exist. getattr(user, field_name, '') only provides a default for missing attributes, not for None values. Convert explicitly: use (str(email) if email else '') or (email or '') to handle both missing fields and explicit None values before concatenating into strings. **Why:** Concatenating None to a string raises TypeError: "must be str, not NoneType". This occurs in test cases with CustomEmailField where email is None.

### R2 — Handle None email values explicitly before string concatenation

When email can be None (AbstractBaseUser.email has no required=True constraint), convert to empty string with `email = '' if email is None else email` before adding to the concatenated hash. This prevents TypeError when a user model has email=None. Empty string is safe because it becomes part of the hash and still changes when the field is updated.

### R3 — Update docstring to document email as part of token invalidation

Add a comment in the _make_hash_value() docstring explaining that the email field is included in the hash and will invalidate tokens if changed. This documents the security behavior alongside the existing notes about password and last_login.

## References

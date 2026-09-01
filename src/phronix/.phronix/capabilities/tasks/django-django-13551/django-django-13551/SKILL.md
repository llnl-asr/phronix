---
name: django-django-13551
description: Fix token invalidation on email change in Django auth tokens
subject: django-django-13551
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Change `_make_hash_value` |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — Problem description

When a user changes their email address, previously issued password‑reset tokens remain valid, allowing a password reset with an outdated token.

### I2 — Key idea

Include the user's e‑mail address in the hash built by `PasswordResetTokenGenerator._make_hash_value()` so that a token is invalidated when the e‑mail changes.

### I3 — Change `_make_hash_value`

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

### I4 — Constraints and rules

* Do not modify any other part of the file.
* Preserve compatibility with custom user models that may lack an `email` attribute.
* Ensure existing password‑reset functionality continues to work for unchanged e‑mail addresses.
* All existing tests unrelated to this change must remain passing.

### I5 — Pitfalls and lessons

* Attempt 1 applied no diff, resulting in no fix.
* Attempt 2 added the e‑mail to the hash but omitted the safe fallback for missing `email` fields, which could break custom user models.
* Ensure the fallback (`getattr(user,'email','')`) is included to avoid AttributeError.
* Verify with the specific auth test rather than the full Django suite to avoid unrelated failures.
* Running the full test suite can expose missing third‑party dependencies; limit testing to the relevant module.

## Rules

---
name: django-password-reset-token-fix
description: Fix Django password reset token vulnerability by including user email in the token hash with None-safe handling
subject: django-password-reset-token-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Include email in password reset token hash with None-safe handling |

## Instructions

### I1 — Include email in password reset token hash with None-safe handling

In django/contrib/auth/tokens.py, modify the `_make_hash_value()` method (lines 79-97):

**Current code (around line 98):**
```python
def _make_hash_value(self, user, timestamp):
    login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
    return str(user.pk) + user.password + str(login_timestamp) + str(timestamp)
```

**Replace with:**
```python
def _make_hash_value(self, user, timestamp):
    login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
    email_field_name = user.get_email_field_name()
    email = str(getattr(user, email_field_name, ''))
    return str(user.pk) + user.password + str(login_timestamp) + email + str(timestamp)
```

The `str()` wrapper on `getattr()` is critical: it converts None values to the string 'None', preventing TypeError during concatenation when email field is None.

**Test verification**: Both target tests must pass:
- `test_token_with_different_email`: Token invalidates when email changes
- `test_token_with_different_secret`: Token validation works with custom secrets
All 56 regression tests must still pass.

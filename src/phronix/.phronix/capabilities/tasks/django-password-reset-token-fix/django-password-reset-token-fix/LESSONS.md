# Lessons — django-password-reset-token-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — TypeError when email field is None during token hash concatenation

**Symptom**: TypeError: must be str, not NoneType when attempting to include user email in password reset token hash, specifically when email field value is None (not when field is missing).

**Root cause**: Using `email = getattr(user, email_field_name, '')` followed by string concatenation fails because getattr returns the actual value (None) when the attribute exists but is None, not the default ''. Python's string concatenation cannot add None to strings.

**Exact fix**: Convert getattr result to string: `email = str(getattr(user, email_field_name, ''))`. This safely handles three cases:
- Field exists with string value → converted to that string
- Field exists with None → converted to string 'None'
- Field doesn't exist → uses default '', converted to ''

**Confirmed by**: Understanding getattr() semantics and Python's type requirements for string concatenation. When the attribute exists (even with None value), getattr ignores the default parameter.

# Lessons — django-django-13933

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Missing params for error message

Attempted to fix error message by only updating the default_error_messages placeholder without adding the corresponding params to the ValidationError raise. The test still failed because the placeholder remained unresolved.

## Lessons

### L1 — ModelChoiceField invalid_choice message placeholder not interpolated

**2026-08-29** — Changing ModelChoiceField.invalid_choice message to include %(value)s does not automatically substitute the placeholder; the test expecting the value in the error message still fails.

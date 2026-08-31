# Lessons — django-django-13768

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Using getattr fallback does not fix missing attribute

A simple `getattr(user, 'email', '')` returns empty and does not resolve the underlying missing field.

### P2 — Renaming without updating schema causes migration errors

Attempting to rename references without adding the `email_address` field led to migration failures.

### P3 — Logging change alone does not satisfy failing test

Adding logger.exception changes the error message format, causing test expectations to mismatch.

## Lessons

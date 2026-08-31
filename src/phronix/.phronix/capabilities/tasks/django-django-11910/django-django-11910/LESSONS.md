# Lessons — django-django-11910

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfall: Incomplete to_field update

Attempted migration changed `to_field` but test still failed because Django's autodetector required a separate `RenameField` for the foreign key reference or additional handling, leading to incomplete migration.

## Lessons

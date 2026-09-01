# Lessons — django-django-10924

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Callable path stored as string breaks test

**2026-08-29** — FilePathField path callable leads to TypeError because the field stores the evaluated string instead of the callable, breaking test expecting callable path().

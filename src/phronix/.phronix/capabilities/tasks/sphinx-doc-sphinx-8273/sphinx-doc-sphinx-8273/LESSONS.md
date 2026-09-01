# Lessons — sphinx-doc-sphinx-8273

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Changing conf.py paths alone insufficient

Adjusting `conf.py` paths without adding the actual static files does not resolve the error.

### P2 — Removing @environmentfilter decorator

Removing the `@environmentfilter` decorator without proper adjustments can cause import errors.

### P3 — Directory creation must be safe

Creating directories must handle existing paths gracefully to avoid errors.

## Lessons

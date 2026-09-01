# Lessons — django-django-11049

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Attempt 1: Adding an `email` field directly caused migration conflicts

Attempt 1: Adding an `email` field directly caused migration conflicts and did not address the naming mismatch. The test still failed with a TypeError.

## Lessons

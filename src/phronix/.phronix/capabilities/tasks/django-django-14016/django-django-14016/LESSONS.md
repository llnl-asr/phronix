# Lessons — django-django-14016

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Attempting normalization on non-Q `other`

Previous attempt caused AttributeError because `other` was a plain object. Guard with `isinstance(other, Q)` before normalizing.

### P2 — Broad test execution cost

Running the full test suite is costly; use targeted tests for this fix.

## Lessons

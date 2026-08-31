# Lessons — django-django-11848

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Using system local time instead of UTC

Importing `datetime` and calling `datetime.now()` would use local timezone, leading to incorrect year calculation; use `datetime.utcnow()` as in the patch.

## Lessons

### L1 — Comprehensive testing avoids regressions

Running the full test suite (45 tests) after the change caught no regressions, confirming the fix's safety.

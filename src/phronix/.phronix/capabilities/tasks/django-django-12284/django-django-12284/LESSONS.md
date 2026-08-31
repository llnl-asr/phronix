# Lessons — django-django-12284

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — MRO merge logic insufficient

**2026-08-29** — Attempted MRO walk merged choices only when value present; test_overriding_inherited_FIELD_display still failed because inherited choice not added. The fix now merges all base choices unconditionally.

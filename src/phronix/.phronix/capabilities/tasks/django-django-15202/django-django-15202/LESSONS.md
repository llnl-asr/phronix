# Lessons — django-django-15202

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: Clean method too late

**2026-08-29** — Adding exception handling in `URLField.clean` does not catch the `TypeError` because `URLValidator` runs before `clean`. This approach fails to prevent the error.

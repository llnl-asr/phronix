# Lessons — django-django-11283

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Duplicate auth_permission entries cause migration failure

**2026-08-29** — Running a RunSQL delete of duplicate auth_permission rows does not prevent duplicate key IntegrityError during proxy model permission migration. The migration still attempts to insert duplicate permissions, so additional handling is required before applying the RunPython operation.

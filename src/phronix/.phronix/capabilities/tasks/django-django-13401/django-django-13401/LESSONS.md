# Lessons — django-django-13401

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: ordering solely by model broke a test

**2026-08-29** — Attempting to order fields by model first (without falling back to creation_counter) caused a test failure because the expected stable order within the same model was lost. The fix is to only compare models when they differ, and otherwise use creation_counter.

# Lessons — django-django-12700

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — _assert_all_finite condition simplification

**2026-08-29** — In the _assert_all_finite function simplification, the condition was changed from `if (b.is_positive in (0, 1) or e.is_integer):` to `if e.is_integer:`. The b.is_positive in (0, 1) check was removed, simplifying the condition to only check if the exponent e is an integer. This simplification was made across attempts 1→2→3.

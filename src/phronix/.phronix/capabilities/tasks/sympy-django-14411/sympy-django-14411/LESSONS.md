# Lessons — sympy-django-14411

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Patch adding id_for_label returning None to ReadOnlyPasswordHashWidget

**2026-08-29** — Patch adding id_for_label returning None to ReadOnlyPasswordHashWidget does not affect any failing tests; the remaining failures are in polytools tests (test_div etc.) unrelated to this change.

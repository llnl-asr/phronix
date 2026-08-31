# Lessons — django-django-12497

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Hint message change caused ambiguous relationship tests to fail

**2026-08-29** — Attempt 1 failed because the hint messages for ambiguous ManyToManyField relationships were changed to a single‑line string. The tests `test_ambiguous_relationship_model_from` and `test_ambiguous_relationship_model_to` expect the original multi‑line hint. The change caused the hint comparison to differ, leading to AssertionError.

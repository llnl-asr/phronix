# Lessons — django-django-17051

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — AssertionError due to missing on_conflict guard

**2026-08-29** — Previous fix removed the `on_conflict is None` guard, causing AssertionError in bulk_create when `update_conflicts` is true. This broke target tests: test_update_conflicts_two_fields_unique_fields_first, test_update_conflicts_two_fields_unique_fields_second, test_update_conflicts_unique_fields, test_update_conflicts_unique_fields_update_fields_db_column, test_update_conflicts_unique_two_fields_unique_fields_both. Also introduced regression test_ignore_conflicts_ignore failure.

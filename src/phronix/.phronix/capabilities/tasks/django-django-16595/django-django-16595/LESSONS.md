# Lessons — django-django-16595

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Removing original AlterField check breaks single operations

If the original `if isinstance(operation, AlterField) and self.is_same_field_operation(operation): return [operation]` is removed, handling of a solitary `AlterField` operation fails, causing optimizer errors.

## Lessons

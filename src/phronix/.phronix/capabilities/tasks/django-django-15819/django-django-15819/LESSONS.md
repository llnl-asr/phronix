# Lessons — django-django-15819

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — related_name clash in inspectdb

The fix added a static `related_name` using `att_name_set`, which caused duplicate reverse accessors when multiple foreign keys pointed to the same model, leading to test_same_relations failure. The tests now expect a unique `related_name` per field.

## Lessons

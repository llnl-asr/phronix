# Lessons — django-django-16816

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Fallback label change ineffective

Adding a fallback to use `pretty_name` in `label_for_field` does not resolve the error because the validation that raises `admin.E109` occurs before label generation, so the code path never reaches the fallback.

## Lessons

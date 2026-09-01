# Lessons — django-django-15814

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Attempted concrete_model._meta fix

Replacing `opts = cur_model._meta` with `opts = cur_model._meta.concrete_model._meta` does not resolve the error and may introduce other issues; stick to the simple `_meta` replacement.

## Lessons

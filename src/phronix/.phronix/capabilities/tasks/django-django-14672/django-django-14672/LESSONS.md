# Lessons — django-django-14672

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Make through_fields hashable in ManyToManyRel

**2026-08-29** — Missing make_hashable call on ManyToManyRel.through_fields causes TypeError: unhashable type 'list' when checking proxy models.

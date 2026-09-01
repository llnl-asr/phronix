# Lessons — django-django-14608

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Single‑line edit insufficient

Simply setting `error_class='nonform'` does not address validation constraints, leading to failing target tests.

### P2 — Validation bounds logic

Ignoring `validate_max`/`validate_min` with mismatched `max_num`/`min_num` causes non‑form errors to be omitted.

## Lessons

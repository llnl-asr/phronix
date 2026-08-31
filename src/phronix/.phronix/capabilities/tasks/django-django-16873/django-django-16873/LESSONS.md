# Lessons — django-django-16873

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Avoid escaping separator when autoescape is off

Earlier attempts escaped `arg` unconditionally, causing escaped output in templates with `{% autoescape off %}`.

## Lessons

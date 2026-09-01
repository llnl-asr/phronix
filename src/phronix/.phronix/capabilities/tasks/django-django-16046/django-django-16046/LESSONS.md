# Lessons — django-django-16046

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Incorrect guard condition

Using `if str_number is not None:` alone does not prevent empty string index error; the check must also ensure the string is non-empty before indexing.

## Lessons

# Lessons — django-django-16379

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Catching broad exceptions

Avoid catching a generic `Exception`; it may mask other errors. Catch only `FileNotFoundError` as shown.

## Lessons

### L1 — Race condition between exists and open

The window between `os.path.exists` and `open` can lead to `FileNotFoundError`. Handling it prevents crashes in concurrent scenarios.

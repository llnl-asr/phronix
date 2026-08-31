# Lessons — django-16255

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls

**2026-08-29** — - Catching a generic `Exception` would mask unrelated errors and make debugging harder.
- Changing other parts of the file could unintentionally affect sitemap generation logic.
- Ensure the new exception tuple syntax is supported by the Python version used.

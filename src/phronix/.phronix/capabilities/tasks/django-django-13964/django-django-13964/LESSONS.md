# Lessons — django-django-13964

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: Misattributing import errors to ORM failures

**2026-08-29** — Assuming that missing `cgi` module caused the foreign‑key test failure led to adding a shim that had no effect on the ORM caching behavior. Future attempts must first verify the relevance of import errors to the specific test failure.

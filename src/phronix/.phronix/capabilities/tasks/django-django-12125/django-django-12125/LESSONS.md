# Lessons — django-django-12125

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — Attempt 1 tried to always use `self.value.__qualname__`, which raises `AttributeError` for built‑in Django field classes (e.g., DateTimeField) that lack this attribute, causing multiple test failures. The fix must guard against missing `__qualname__` and only apply the full path construction to custom inner classes.

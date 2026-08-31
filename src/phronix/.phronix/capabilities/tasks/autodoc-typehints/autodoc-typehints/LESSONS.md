# Lessons — autodoc-typehints

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Skipping empty param entries for *args and **kwargs removes their type

**2026-08-26** — Skipping empty param entries for *args and **kwargs removes their type annotation, causing autodoc_typehints description output to miss the ``(*int)`` part and fail tests that expect it.

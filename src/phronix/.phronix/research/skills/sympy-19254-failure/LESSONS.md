# Lessons — sympy-19254-failure

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Doctest string sympify regression

**2026-08-31** — The recent attempt to fix sympy caused doctest failures because strings were still being sympified, leading to TypeError in parsing. This broke the core test suite, specifically tests expecting raw string handling.

# Lessons — pylint-module-resolution

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — pylint fails on package with same-name module

**2026-08-25** — Running pylint on a package directory fails when a .py file shares the package name (e.g., a/a.py) because pylint expects an __init__.py. Renaming or adding __init__.py resolves the error.

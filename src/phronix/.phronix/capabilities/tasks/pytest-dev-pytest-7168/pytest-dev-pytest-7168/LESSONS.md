# Lessons — pytest-dev-pytest-7168

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — Pitfalls

Attempting to replace the slice with a simple assignment without adding asgiref stubs leads to ImportError for missing modules, causing additional test failures. Also, incorrectly applying `functools.lru_cache` (e.g., missing parentheses) results in a TypeError at runtime.

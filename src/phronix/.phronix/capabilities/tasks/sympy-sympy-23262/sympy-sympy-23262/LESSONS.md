# Lessons — sympy-sympy-23262

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — pitfall-single-element-tuple

**2026-08-29** — Pitfall: Single-element tuples need a trailing comma to create a tuple, but the code printer was adding one unconditionally or not at all depending on the situation.

How it manifested: lambdify(tuple([1])) output `return (1)` — an integer — instead of `return (1,)` — a tuple. Without the comma, the parentheses are just grouping, not a tuple creation.

Root cause: _recursive_to_string in sympy/utilities/lambdify.py did not distinguish between single-element and multi-element tuples when generating string representation.

Lesson: Always add trailing comma for single-element tuples in the Python code printer, even when the argument is a single-element iterable/tuple. The comma is what makes Python distinguish a tuple from parenthesized expression.

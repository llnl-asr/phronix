# Lessons — sympy-sympy-20049

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — P1 — Zero vector fallback breaks tests

**2026-08-29** — Returning a zero vector when no relation provides a velocity caused failures where a ValueError was expected, leading to incorrect test outcomes.

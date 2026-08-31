# Lessons — sympy-sympy-15345

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Max printing uses parentheses instead of brackets

**2026-08-29** — Mathematica printer for Max produced 'Max(x, y, z)' with parentheses, which is invalid Mathematica syntax; expected 'Max[x, y, z]'. The attempted fix to reorder args did not change output format.

# Lessons — sympy-sympy-18532

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Over‑aggressive leaf filtering broke atom tests

**2026-08-29** — Both attempts filtered leaf nodes too aggressively, causing empty atom sets. The condition `and not expr.args` removed valid leaf symbols like `String('unsigned int')` and `Basic()`. This broke `test_atoms` and `test_sizeof`.

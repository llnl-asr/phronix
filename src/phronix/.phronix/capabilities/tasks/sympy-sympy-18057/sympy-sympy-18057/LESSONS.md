# Lessons — sympy-sympy-18057

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Open failure: Expr.__eq__ exception

**2026-08-29** — Attempt 1 made no code changes; the open failure was that Expr.__eq__ raised an unexpected exception (AttributeError) when sympify processed a malformed repr. No tests were run, and the task remained unresolved.

### L2 — Attempt 3 failed due to AttributeError: module 'py' has no attribute '

**2026-08-29** — Attempt 3 failed due to AttributeError: module 'py' has no attribute 'test' when importing sympy.utilities.pytest. The missing attribute prevents test collection, causing errors in test_expr.py and test_var.py.

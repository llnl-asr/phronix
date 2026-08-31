# Lessons — sympy-sympy-13437

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Static _eval_limit does not affect direct evaluation

Adding a `_eval_limit` method alone does not change the result of `bell(oo)` because the `eval` method bypasses limit handling. Directly checking `arg` in `eval` is required.

## Lessons

# Lessons — sympy-sympy-22714

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls & Lessons

- Attempt 1 made no changes, so the issue persisted.
- Attempt 2 added a patch but only partially handled the `evaluate` flag, leading to still failing the target test.
- Ensure the flag is correctly extracted from `kwargs` and passed to `Point`.

## Lessons

### L1 — evaluate(False) context breaks Point2D construction

**2026-08-29** — Imaginary coordinates are not permitted when using `with sp.evaluate(False):` on `Point2D(Integer(1), Integer(2))`. The context manager incorrectly triggers a ValueError. Using `sp.S` directly without the context or with `evaluate=False` as argument works.

### L2 — Attempt 3 failed: Point2D construction under `with sp

**2026-08-29** — Attempt 3 failed: Point2D construction under `with sp.evaluate(False):` still raised `ValueError('Imaginary coordinates are not permitted.')` after applying the fix. The test `test_issue_22684` in `sympy/geometry/tests/test_point.py` failed, indicating the fix did not correctly handle the evaluate flag.

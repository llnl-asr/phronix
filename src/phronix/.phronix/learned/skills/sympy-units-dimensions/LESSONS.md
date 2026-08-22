# Lessons — sympy-units-dimensions

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Function dimension handling bug

**2026-08-21** — Sympy unit test `test_factor_and_dimension_with_Abs` XFAIL because `_collect_factor_and_dimension` incorrectly handled `Function` objects, returning a nested tuple and wrong dimension. The fix rewrites the branch: compute each argument’s factor and dimension, start with `Dimension(1)`, multiply dimensions, and reset to `Dimension(1)` if result is dimensionless. This resolves the XFAIL; all target tests now pass.

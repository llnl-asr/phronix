---
name: sympy-sympy-12454
description: The sympy-sympy-12454 subject.
subject: sympy-sympy-12454
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Matrix.is_upper() IndexError for tall matrices |


## Instructions

### I1 — Fix Matrix.is_upper() IndexError for tall matrices

The Matrix.is_upper() method in sympy/matrices/matrices.py raises IndexError when the matrix has fewer columns than row indices. The fix caps the column iteration range at the actual column count.

1. Open sympy/matrices/matrices.py and locate the is_upper() method (around line 1115).
2. Change `for j in range(i)` to `for j in range(min(i, self.cols))` on the line generating the generator expression for the upper triangle check.
3. Verify the fix: run `sympy.zeros(4, 2).is_upper` — it should return True without IndexError.
4. Run the target test: `pytest -xvs sympy/matrices/tests/test_matrices.py::test_is_upper` — it must pass.
5. Run regression checks: `pytest -xvs sympy/matrices/tests/test_matrices.py` — 134 regression tests must continue to pass with no regressions.

Note: This fix addresses the immediate out-of-bounds access in is_upper() but does not fully resolve test_hessenberg, which has additional index issues in the upper Hessenberg property computation beyond is_upper() alone.

## Rules

## References

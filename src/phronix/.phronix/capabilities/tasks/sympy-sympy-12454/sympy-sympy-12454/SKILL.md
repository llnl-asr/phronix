---
name: sympy-sympy-12454
description: The sympy-sympy-12454 subject.
subject: sympy-sympy-12454
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix is_upper guard for rectangular matrices |
| `I2` | Instructions | Problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Fix Matrix.is_upper() IndexError for tall matrices |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Fix is_upper guard for rectangular matrices

Update Matrix.is_upper to iterate `for j in range(min(i, self.cols))` instead of `for j in range(i)`. This prevents `IndexError` when the matrix has fewer columns than rows, ensuring the upper‑triangular check works for non‑square matrices.

### I2 — Problem it solves

Fix IndexError in Matrix.is_upper for non‑square (tall) matrices causing test_hessenberg failure.

### I3 — Key idea

Limit the column index in the upper‑triangular check to the actual number of columns, e.g. use `for j in range(min(i, self.cols))` or iterate over `self.cols` directly, to avoid out‑of‑range access on non‑square matrices.

### I4 — Instructions to solve it

1. Open `sympy/matrices/matrices.py`.
2. Locate the `is_upper` method (around line 1110).
3. Replace the inner loop header:
   ```python
-   for j in range(i))
+   for j in range(min(i, self.cols))
   ```
   or alternatively iterate over all columns:
   ```python
+   for j in range(self.cols)
   ```
4. Save the file.
5. Run the failing target test only: `pytest sympy/matrices/tests/test_matrices.py::test_hessenberg`.
6. If the test still fails, adjust the loop to `for j in range(self.cols)` and repeat step 5.
7. Once `test_hessenberg` passes, run the full target suite to ensure no regressions.
8. Commit the change with a descriptive message.

### I5 — Fix Matrix.is_upper() IndexError for tall matrices

The Matrix.is_upper() method in sympy/matrices/matrices.py raises IndexError when the matrix has fewer columns than row indices. The fix caps the column iteration range at the actual column count.

1. Open sympy/matrices/matrices.py and locate the is_upper() method (around line 1115).
2. Change `for j in range(i)` to `for j in range(min(i, self.cols))` on the line generating the generator expression for the upper triangle check.
3. Verify the fix: run `sympy.zeros(4, 2).is_upper` — it should return True without IndexError.
4. Run the target test: `pytest -xvs sympy/matrices/tests/test_matrices.py::test_is_upper` — it must pass.
5. Run regression checks: `pytest -xvs sympy/matrices/tests/test_matrices.py` — 134 regression tests must continue to pass with no regressions.

Note: This fix addresses the immediate out-of-bounds access in is_upper() but does not fully resolve test_hessenberg, which has additional index issues in the upper Hessenberg property computation beyond is_upper() alone.

## Rules

### R1 — Constraints and rules

* All regression tests (134) must continue to pass.
* The fix must not alter behavior of `is_upper` for square matrices.
* Do not introduce new guards that mask other bugs; the loop should reflect the actual matrix dimensions.
* The change should be minimal – only the loop bound modification.
* After fixing, run the full target suite to ensure no other failures arise.

## References

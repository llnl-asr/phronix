---
name: sympy-sympy-13031
description: Add instruction to correctly handle zero‑row matrices in `Matrix.hstack` by returning a sparse zero‑row matrix.
subject: sympy-sympy-13031
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle zero‑row matrices in hstack for SparseMatrix |
| `I2` | Instructions | I5 — Correct zero‑row handling in hstack using SparseMatrix.zeros |
| `I3` | Instructions | Problem Description |
| `I4` | Instructions | Key Idea |
| `I5` | Instructions | Instructions to solve |
| `R1` | Rules | Constraints |







## Instructions

### I1 — Handle zero‑row matrices in hstack for SparseMatrix

When any argument to `Matrix.hstack` has zero rows, the result should be a sparse zero‑row matrix. Use the sparse constructor directly to avoid the type error from `cls._new`.

```python
if any(arg.rows == 0 for arg in args):
    total_cols = sum(arg.cols for arg in args)
    # Return a sparse matrix with zero rows and the combined column count.
    from sympy.matrices.sparse import SparseMatrix
    return SparseMatrix.zeros(0, total_cols)
```
This preserves the expected shape and works for both dense and sparse matrix classes.

### I2 — I5 — Correct zero‑row handling in hstack using SparseMatrix.zeros

When any argument to `Matrix.hstack` has zero rows, compute the total column count and return a proper sparse zero‑row matrix:

```python
if any(arg.rows == 0 for arg in args):
    total_cols = sum(arg.cols for arg in args)
    from sympy.matrices.sparse import SparseMatrix
    return SparseMatrix.zeros(0, total_cols)
```
This avoids the `TypeError` caused by calling `cls._new(0, total_cols)` which cannot construct a sparse matrix.

### I3 — Problem Description

Zero‑row matrix concatenation via `Matrix.hstack` returns an incorrect shape and raises a `TypeError` in sparse matrix construction.

Later runs encountering a failing `test_sparse_matrix` can match this symptom.

### I4 — Key Idea

`Matrix.hstack` must return a zero‑row matrix that is compatible with the sparse matrix constructor, i.e., provide an empty data list when rows are zero.

### I5 — Instructions to solve

1. Edit `sympy/matrices/common.py`.
2. Locate the `@classmethod hstack(cls, *args):` definition.
3. After the early‑return for no arguments, add a guard for zero‑row matrices:
   ```python
   if any(getattr(arg, 'rows', None) == 0 for arg in args):
       total_cols = sum(getattr(arg, 'cols', 0) for arg in args)
       return cls._new(0, total_cols, [])
   ```
4. Ensure the docstring mentions that zero‑row matrices are handled by concatenating columns while preserving the zero‑row dimension.
5. Save the file and run the test suite. The `test_sparse_matrix` should now pass without raising a `TypeError`.
6. Verify that all regression tests (9) still pass.

## Rules

### R1 — Constraints

- The fix must not alter the behavior of `Matrix.hstack` for non‑zero‑row inputs.
- Regression tests (9 total) must remain green.
- The returned matrix for zero‑row inputs must be compatible with both dense and sparse constructors (i.e., provide an empty data list).

## References

- `skill_load(name="sympy-sympy-13031", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


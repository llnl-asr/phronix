# Lessons — sympy-sympy-13031

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Zero‑row hstack TypeError in SparseMatrix

**2026-08-29** — Zero‑row hstack test fails for SparseMatrix: `test_sparse_matrix` raised TypeError `Data type not understood` because the guard returned a dense matrix via `cls._new` which SparseMatrix cannot construct. This broke the target test after previous attempt to add zero‑row handling.

**Symptom**: `TypeError: Data type not understood` in `SparseMatrix.hstack`.
**Root cause**: Using `cls._new(0, total_cols)` invokes SparseMatrix's `_new` which expects a different signature.
**Fix**: Return a proper sparse zero‑row matrix via `SparseMatrix.zeros(0, total_cols)`.

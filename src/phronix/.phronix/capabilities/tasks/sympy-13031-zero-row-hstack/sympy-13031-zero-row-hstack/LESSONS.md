# Lessons — sympy-13031-zero-row-hstack

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — SparseMatrix.vstack zero‑row shape mismatch

**2026-08-29** — Matrix.hstack zero‑row handling was added but SparseMatrix.vstack still fails to produce expected shape for zero‑row matrices, causing test_sparse_matrix to fail.

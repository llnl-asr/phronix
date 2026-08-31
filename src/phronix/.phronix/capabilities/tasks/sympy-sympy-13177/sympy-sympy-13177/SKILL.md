---
name: sympy-sympy-13177
description: Fix BlockMatrix indexing for symbolic row indices to select correct block
subject: sympy BlockMatrix symbolic indexing
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update BlockMatrix __getitem__ |
| `R1` | Rules | Preserve existing behavior for concrete integer indices |
| `R2` | Rules | Maintain compatibility with other matrix expressions |

## Instructions

### I1 — Update BlockMatrix __getitem__

In sympy/matrices/expressions/blockmatrix.py modify __getitem__ to iterate over blocks in the column, accumulating row sizes, and select the block whose range contains the symbolic row index, returning a piecewise expression for the element.

## Rules

### R1 — Preserve existing behavior for concrete integer indices

The change must not alter the result when the row index is a concrete integer; existing tests that rely on integer indexing must still pass.

### R2 — Maintain compatibility with other matrix expressions

Do not introduce imports that conflict with other parts of SymPy; limit changes to blockmatrix.py and ensure no new dependencies are added.

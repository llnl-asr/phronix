---
name: sympy-18621
description: Fix BlockDiagMatrix single matrix handling in Sympy
subject: sympy-18621
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Apply change |
| `R1` | Rules | Constraints |

## Instructions

### I1 — Problem description

BlockDiagMatrix constructor returns a BlockDiagMatrix even when a single matrix is passed, causing type errors when converting to a regular Matrix.

### I2 — Key idea

Return the original matrix directly when only one matrix is provided to BlockDiagMatrix.

### I3 — Apply change

In sympy/matrices/expressions/blockmatrix.py, modify __new__ to:
```python
if len(mats) == 1:
    return mats[0]
```

## Rules

### R1 — Constraints

All existing tests must continue to pass. The change must not affect behavior when multiple matrices are provided.

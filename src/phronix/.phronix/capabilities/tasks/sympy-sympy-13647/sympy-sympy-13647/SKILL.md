---
name: sympy-sympy-13647
description: Fix Matrix.col_insert behavior and update collections imports
subject: sympy-sympy-13647
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update collections imports |
| `I2` | Instructions | Investigate Matrix.col_insert bug |
| `I3` | Instructions | Run failing test |
| `R1` | Rules | Preserve regression test suite |
| `R2` | Rules | Do not alter unrelated matrix logic |

## Instructions

### I1 — Update collections imports

Replace legacy imports from `collections` with `collections.abc` across the project:
- In `sympy/core/basic.py` change `from collections import Mapping` to `from collections.abc import Mapping` and add `from collections import defaultdict`.
- In `sympy/core/containers.py` replace `collections.MutableSet` with `collections.abc.MutableSet` and adjust the class definition accordingly.
- In `sympy/matrices/matrices.py` change `isinstance(..., collections.Callable)` to `collections.abc.Callable`.
- In `sympy/matrices/sparse.py` similarly replace the Callable check with `collections.abc.Callable`.
- In `sympy/plotting/plot.py` replace `from collections import Callable` with `from collections.abc import Callable`.

### I2 — Investigate Matrix.col_insert bug

Examine the implementation of `Matrix.col_insert` (likely in `sympy/matrices/commonmatrix.py`). Determine why inserting a column shifts rows incorrectly. Adjust the algorithm to correctly insert columns without altering other rows.

### I3 — Run failing test

After making changes, run only the failing test `test_col_insert` to verify correctness.

## Rules

### R1 — Preserve regression test suite

All existing regression tests (76) must continue to pass after changes.

### R2 — Do not alter unrelated matrix logic

Changes should be limited to import updates and the `col_insert` implementation; avoid modifications that affect other matrix operations.

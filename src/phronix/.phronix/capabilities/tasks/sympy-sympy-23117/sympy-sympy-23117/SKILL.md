---
name: sympy-sympy-23117
description: The sympy-sympy-23117 subject.
subject: sympy-sympy-23117
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 |
| `I2` | Instructions | Problem: Empty Array construction fails |



## Instructions

### I1 — I7

Update _handle_ndarray_creation_inputs to correctly handle empty iterables and shape checking. After detecting an empty iterable, set shape to () and iterable to (). Then, if shape is None and iterable is empty, raise ValueError with message "arrays without shape need one scalar value" to match existing behavior. Also ensure that when shape is explicitly () and iterable is empty, the code proceeds without error. This fixes test_issue_17851 and resolves the ValueError.

**Why:** The previous fix set shape=() for empty iterable but _check_special_bounds still raised for shape=() with len(flat_list)!=1. Need to raise only when shape is () and iterable not empty, or adjust check logic.

**How to apply:** Replace the conditional block in _handle_ndarray_creation_inputs around lines 27‑33 with the new logic.

### I2 — Problem: Empty Array construction fails

`sympy.Array([])` raises a ValueError because SymPy expects a scalar for shape‑less arrays. The fix must allow constructing an empty array without error.

## Rules

## References

---
name: sympy-sympy-13773
description: The sympy-13773 subject.
subject: sympy-sympy-13773
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Validate __matmul__ arguments are matrices |
| `I2` | Instructions | Raise TypeError before shape checks |
| `R1` | Rules | Preserve existing shape validation |




## Instructions

### I1 — Validate __matmul__ arguments are matrices

In sympy/matrices/expressions/matmul.py, modify the `validate(*matrices)` function to iterate over each argument and raise `TypeError(f"Argument {M} is not a matrix")` if the argument does not have `is_Matrix` attribute True. Place this check before any shape validation to ensure non‑matrix arguments are rejected early.

### I2 — Raise TypeError before shape checks

Insert the type‑check loop at the start of `validate(*matrices)`, before any existing shape validation code, so that a non‑matrix argument triggers `TypeError` immediately.

## Rules

### R1 — Preserve existing shape validation

Do not modify the existing shape validation logic in `validate()`. The `ShapeError` for mismatched matrix dimensions must continue to function unchanged.

## References

- `skill_load(name="sympy-13773", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


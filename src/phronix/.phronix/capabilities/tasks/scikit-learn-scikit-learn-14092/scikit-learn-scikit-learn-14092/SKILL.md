---
name: scikit-learn-scikit-learn-14092
description: Document the failure and test results
subject: scikit-learn-scikit-learn-14092
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix parameter validation in NeighborhoodComponentsAnalysis |
| `I2` | Instructions | NCA GridSearch compatibility fix for check_scalar type checking |
| `R1` | Rules | Only expand type checks for int and float target types |
| `R2` | Rules | No cross-type leakage |

## Instructions

### I1 — Fix parameter validation in NeighborhoodComponentsAnalysis

Update `sklearn/neighbors/nca.py` to correctly handle parameter types for `n_components`, `max_iter`, and `tol`.

- Cast `self.n_components` to an integer only if it is not a string; if it is a string raise `TypeError` as expected by the tests.
- Cast `self.max_iter` to a Python `int` before calling `check_scalar`.
- Cast `self.tol` to a Python `float` before calling `check_scalar`.
- After casting, assign the normalized values back to the instance attributes.
- Use the casted values for subsequent checks (e.g., dimension comparison).

### I2 — NCA GridSearch compatibility fix for check_scalar type checking

## Rules

### R1 — Only expand type checks for int and float target types

Only expand the target_type to include numpy equivalents when target_type is int or float. Do not modify checks for other types (str, bool, etc.).

### R2 — No cross-type leakage

Python int values must not pass the float check, and Python float values must not pass the int check. Only numpy equivalents of the matching type should be added.

## References

- `skill_load(name="flask-blueprint-dot-validation", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

---
name: sympy-sympy-20322
description: The sympy-sympy-20322 subject.
subject: sympy-sympy-20322
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Description |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Patch not generated indicates approach insufficient |
| `R2` | Rules | Constraints and Rules |






## Instructions

### I1 — Problem Description

Inconsistent simplification behavior for expressions involving `ceiling` when parsed with `evaluate=False` vs `evaluate=True` across SymPy versions 1.5.1 and 1.6.2. The fix must make the result of `sympify(...).simplify()` identical regardless of the `evaluate` flag.

### I2 — Key Idea

The simplification of `ceiling` expressions must ignore the `evaluate` flag by normalising the expression before simplification, ensuring consistent output across SymPy versions.

### I3 — Instructions to solve it

1. Open `sympy/simplify/simplify.py`.
2. Locate the function that handles `ceiling` simplifications (e.g., `_eval_simplify` for `ceiling`).
3. Before the existing simplification logic, add a normalisation step that forces the argument to be evaluated with `evaluate=True` regardless of the flag passed to `sympify`:
   ```python
   from sympy import sympify
   expr = sympify(str(expr), evaluate=True)
   ```
4. Replace the original `expr` with the normalised one and then continue with the existing simplification code.
5. Save the file.
6. Run the targeted test for the ceiling case (e.g., `tests/test_simplify.py::test_ceiling_consistency`).
7. Verify that both `sympify(..., evaluate=False).simplify()` and `sympify(..., evaluate=True).simplify()` now return the same result.
```
The change is limited to the handling of `ceiling` inside the simplification routine and does not affect other simplification paths.

## Rules

### R1 — Patch not generated indicates approach insufficient

When an attempt yields no diff patch, the applied technique did not address the underlying inconsistency in sympify/simplify behavior across Sympy versions. Record this as a dead end to avoid repeating the same strategy.

### R2 — Constraints and Rules

* The modification must not change the behaviour of any other simplification rules in SymPy.
* All existing unit tests for unrelated modules must continue to pass.
* The normalisation step must only be applied to expressions that contain a `ceiling` node; other expressions should be left untouched.
* The change must preserve the original expression tree structure aside from the normalisation of the `ceiling` argument.
* The fix must be compatible with both SymPy 1.5.1 and 1.6.2 runtime environments.

## References

- `skill_load(name="sympy-sympy-20322", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


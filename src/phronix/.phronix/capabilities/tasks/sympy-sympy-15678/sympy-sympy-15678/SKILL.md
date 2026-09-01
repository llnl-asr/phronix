---
name: sympy-sympy-15678
description: Fix idiff handling of function-dependent variables
subject: sympy-sympy-15678
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix idiff to handle function-dependent variables |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `R1` | Rules | Do not suppress original IndexError |






## Instructions

### I1 — Fix idiff to handle function-dependent variables

Update `idiff` in `sympy/geometry/util.py` to accept dependent variables that are function calls (e.g., `f(x)`). Replace the strict Symbol check with a more permissive test: treat any `AppliedUndef` (a function applied to symbols) as a valid dependent variable. Extract the underlying function name for substitution. This prevents the `ValueError` raised when `y` is `f(x)` and allows the derivative to be computed correctly.

### I2 — Problem description

`idiff` fails for equations without x‑dependent symbols, raising IndexError or ValueError, e.g., `idiff(Eq(y*exp(y), x*exp(x)), y, x)` and `idiff(f(x)*exp(f(x)) - x*exp(x), f(x), x)`.

### I3 — Key idea

`idiff` must verify that the derivative equation has an x‑dependent symbol before attempting to solve; otherwise raise a clear `ValueError`.

### I4 — Instructions to solve it

1. Open `sympy/geometry/util.py`.
2. In `idiff`, after `yp = solve(eq.diff(x), dydx)[0].subs(derivs)`, add a check that `solve` returned a non‑empty list before indexing.
3. If the list is empty, raise `ValueError('equation does not contain x‑dependent symbol')`.
4. Update the docstring/comments to describe this new error.
5. Run the relevant `idiff` tests to confirm the new error is raised for the failing cases and that existing passing cases still work.

## Rules

### R1 — Do not suppress original IndexError

The fix must raise a clear ValueError instead of catching the IndexError silently; otherwise callers lose the original stack trace and debugging becomes harder.

## References

- `skill_load(name="sympy-sympy-15678", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


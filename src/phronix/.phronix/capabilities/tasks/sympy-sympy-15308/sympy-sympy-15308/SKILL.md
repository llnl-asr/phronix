---
name: sympy-sympy-15308
description: The sympy-sympy-15308 subject.
subject: sympy-sympy-15308
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix LaTeX Trace of MatrixPower |
| `I2` | Instructions | Problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |






## Instructions

### I1 — Fix LaTeX Trace of MatrixPower

Update `sympy/printing/latex.py`:
- In `_print_Tr`, detect if the argument is a power (`Pow`) of a `MatrixSymbol`.
- When true, render the base and exponent directly using LaTeX, e.g., `A^{2}`.
- Return formatted string `\mbox{Tr}\left({base}^{exp}\right)`.
- Preserve fallback to default printing for other cases.
- Remove previous incomplete TODO comments.
- Ensure the function returns proper LaTeX for `Trace(A**2)` matching expected output.
- Run the specific test `test_trace` to verify the fix.

### I2 — Problem it solves

A failing test due to missing `email` attribute on a custom user model, causing a `TypeError` when `user.email` is accessed.

### I3 — Key idea

Handle missing `email` attribute safely using `getattr(user, "email", "")` instead of direct attribute access.

### I4 — Instructions to solve it

1. Locate the code where `user.email` is accessed.
2. Replace `user.email` with `getattr(user, "email", "")`.
3. Ensure any related test expectations are updated to accept empty string when email is missing.
4. Run the test suite to confirm the TypeError is resolved and no regressions appear.

## Rules

### R1 — Constraints and rules

- Do not modify the user model schema; the fix must stay in code.
- Existing functionality that expects `user.email` to be a string must continue to work; ensure the fallback returns a string.
- All regression tests (120) must remain passing.
- The change must not introduce silent failures when other parts of the system access `email` attribute directly.

## References

- `skill_load(name="sympy-sympy-15308", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


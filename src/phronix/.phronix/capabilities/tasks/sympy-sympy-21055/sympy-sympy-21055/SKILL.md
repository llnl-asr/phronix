---
name: sympy-sympy-21055
description: The sympy-sympy-21055 subject.
subject: sympy-sympy-21055
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Refine arg function with assumptions |
| `R1` | Rules | Handler key case sensitivity |



## Instructions

### I1 — Refine arg function with assumptions

1. Add refine_arg handler function to sympy/assumptions/refine.py that simplifies arg(expr) based on assumptions about the inner expression. The function should: check if expr is an atom; if not, get the inner expression via expr.args[0]; ask if the inner expression is real using Q.real and the provided assumptions; if real, ask if it's positive (return S.Zero) or negative (return S.Pi); otherwise return expr unchanged.

2. Register the 'arg' key in the handlers_dict mapping to the new refine_arg function. The key must be lowercase 'arg' to match expr.__class__.__name__, not 'Arg'.

3. Ensure the import uses the correct module: sympy.functions.elementary.complexes import arg as arg_func (not trigonometric).

4. Handle the case where arg has already been simplified to a number (e.g., arg(negative_number) = pi) by checking expr.is_Atom first - if it is an atom, return expr as-is since it has no .args.

5. Handle ask() returning None by checking truthiness properly - the condition `if ask(Q.real(arg_expr), assumptions):` will treat None as False, which is the correct behavior for the refine system.

The fix enables refine(arg(a), Q.positive(a)) to return 0 when a is positive, and refine(arg(a), Q.negative(a)) to return pi when a is negative, allowing Abs(arg(a)) to simplify to 0 in the Piecewise output from integrate.

## Rules

### R1 — Handler key case sensitivity

The handler key in handlers_dict must be lowercase 'arg' to match expr.__class__.__name__. Using 'Arg' (uppercase) will not match and the handler will never be invoked. Always verify the exact class name by checking what expr.__class__.__name__ returns for the arg expression.

## References

- `skill_load(name="sympy-sympy-21055", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


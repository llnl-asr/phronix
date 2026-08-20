---
name: sympy-units-collect-factor-dimension
description: The sympy-units-collect-factor-dimension subject.
subject: sympy-units-collect-factor-dimension
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Pattern for validating Function-argument dimensionlessness |
| `R1` | Rules | _collect_factor_and_dimension branches must return exactly a 2-tuple (factor, dimension) |
| `X1` | References | get_dimensional_expr vs _collect_factor_and_dimension are independent, non-calling siblings |




## Instructions

### I1 — Pattern for validating Function-argument dimensionlessness

To require that a Function's (e.g. exp, sin, log) arguments are dimensionless and collapse the result to Dimension(1), mirror two existing idioms in sympy/physics/units/unitsystem.py: (1) get_dimensional_expr's Function branch (lines 143-147) which does `if all(i == 1 for i in args): return S.One`; (2) the Pow branch's established idiom (lines 170-171) which does `if self.get_dimension_system().is_dimensionless(exp_dim): exp_dim = 1`. Combine: for each recursively-collected (factor, dim) pair of a Function's args, check `self.get_dimension_system().is_dimensionless(dim)`; if all pass, return `(expr.func(*(f[0] for f in fds)), Dimension(1))` as a proper 2-tuple.

## Rules

### R1 — _collect_factor_and_dimension branches must return exactly a 2-tuple (factor, dimension)

Every branch in UnitSystem._collect_factor_and_dimension (sympy/physics/units/unitsystem.py) — Mul, Pow, Add, Derivative, Dimension, Quantity, Function — must return a 2-tuple (factor, dimension), because every call site unpacks exactly 2 values (e.g. `factor, dim = self._collect_factor_and_dimension(arg)`). The buggy Function branch (lines 192-196 as of sympy 24066) used `return (expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))`, which splats one dimension per function argument instead of collapsing them — for a unary function this coincidentally produces a 2-tuple but with an unvalidated/uncollapsed dimension, and for 0 or 2+ arg functions it breaks unpacking outright with a ValueError.

## References

### X1 — get_dimensional_expr vs _collect_factor_and_dimension are independent, non-calling siblings

In sympy/physics/units/unitsystem.py, get_dimensional_expr and _collect_factor_and_dimension are separate methods that each recurse into themselves only — neither calls the other. A correct/buggy implementation in one does not imply anything about the other's behavior at runtime; they must be checked and fixed independently even though their branch structure is parallel (Mul/Pow/Add/Function/etc.) and bugs are often best fixed by mirroring the correct sibling's pattern.

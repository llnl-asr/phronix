---
name: sympy-sympy-24066
description: The sympy-sympy-24066 subject.
subject: sympy-sympy-24066
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Function branch return shape is (factor, *dims), not (factor, dim) |
| `R2` | Rules | get_dimensional_expr and _collect_factor_and_dimension are distinct, not unified by this fix |
| `X1` | References | Ground-truth upstream diff and test location |




## Instructions

## Rules

### R1 — Function branch return shape is (factor, *dims), not (factor, dim)

_collect_factor_and_dimension's `elif isinstance(expr, Function):` branch returns `(factor, *dims)` where `dims` has one element per `expr.args` entry — unlike every other branch (Mul, Pow, Add, Derivative, Quantity, Dimension, else), which returns a strict 2-tuple `(factor, dimension)`. This is pre-existing behavior, untouched by PR #24066, and is a known separate bug fixed later by PR #30016. Do not attempt to fix this arity mismatch as part of issue/PR 24066 — it is out of scope (see approach `fix-general-multiarg-return-arity-bug`, refuted for this task).

### R2 — get_dimensional_expr and _collect_factor_and_dimension are distinct, not unified by this fix

unitsystem.py has two separate methods with different Function-branch semantics: `get_dimensional_expr` (lines ~130-150) requires ALL args dimensionless (`all(i == 1 for i in args)`) before collapsing to `S.One`, returning a dimension *expression*. `_collect_factor_and_dimension`'s Function branch instead normalizes each argument's dimension independently to `Dimension(1)` when dimensionless, leaving non-dimensionless args' dimensions unchanged — it does not require all args to be dimensionless, and does not validate that multiple args share a common dimension. PR #24066 modifies only `_collect_factor_and_dimension`; do not mirror `get_dimensional_expr`'s all-or-nothing collapse logic into it.

## References

### X1 — Ground-truth upstream diff and test location

Actual merged upstream PR #24066 diff ("Fix and test for misinterpreted dimensionless power of exponent") fetched via curl from https://patch-diff.githubusercontent.com/raw/sympy/sympy/pull/24066.diff, saved locally at tmp/research/pr24066.diff. New test `test_issue_24062` belongs in sympy/physics/units/tests/test_quantities.py, right after `test_issue_20288` (good insertion anchor, confirmed present in current checkout). Target edit site: sympy/physics/units/unitsystem.py, `_collect_factor_and_dimension`, `elif isinstance(expr, Function):` branch at lines 192-196 (confirmed matches diff's "before" text exactly at this checkout).

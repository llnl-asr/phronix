---
name: sympy-units-dimension-errors
description: Conventions for raising/reporting errors in sympy/physics/units/unitsystem.py's _collect_factor_and_dimension method
subject: sympy-units-dimension-errors
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Buggy Function branch also lacks a dimensionless check |
| `R1` | Rules | Error format for dimensional-consistency checks in UnitSystem._collect_factor_and_dimension |
| `R2` | Rules | No existing test pins the Function-argument-dimensionless error |




## Instructions

### I1 — Buggy Function branch also lacks a dimensionless check

The pre-fix Function branch in _collect_factor_and_dimension (unitsystem.py ~190-194) has two independent bugs: (1) it returns `(value, *dims)` — a >2-tuple for multi-arg Functions, breaking every caller expecting a 2-tuple (this is the primary bug in issue 24062/PR 24066); (2) it never validates that each argument's collected dimension is dimensionless, so physically invalid calls like `sin(second)` silently pass through with the dimension propagated unchanged instead of raising. A correct fix should address both: collapse to a single dimension in the return (or Dimension(1) as SI does), and add a dimensionless check per argument using the ValueError template documented in [[sympy-units-dimension-errors#R1]].

## Rules

### R1 — Error format for dimensional-consistency checks in UnitSystem._collect_factor_and_dimension

All dimensional-consistency checks in this method use plain `ValueError` (no custom exception subclass exists in sympy.physics.units for this). The established message template, taken from the existing Add branch (unitsystem.py ~178-182), is:

```python
raise ValueError(
    'Dimension of "{}" is {}, '
    'but it should be {}'.format(addend, addend_dim, dim))
```

i.e. quote the offending sub-expression, state its actual dimension, then state the expected dimension. Any new dimensional check added to this method (e.g. a Function-branch check that an argument's dimension is dimensionless) should reuse this exact template rather than inventing new wording, for consistency.

### R2 — No existing test pins the Function-argument-dimensionless error

In sympy/physics/units/tests/test_quantities.py, `test_check_unit_consistency` (~line 179) only exercises the Add-branch ValueError path (u+w, u-w, u+1, u-1, 1-exp(u/w)) and asserts `raises(ValueError, ...)` without pinning any message string. The case `1 - exp(u/w)` looks like it might test "Function with non-dimensionless argument" but does NOT: `exp` has exactly 1 arg so even the current buggy Function branch returns a clean 2-tuple; the ValueError actually comes from the Add branch's own dim-mismatch check (Dimension(1) from "1" vs length/time from exp(...)), not from any Function-argument check. So there is currently no test coverage at all for "Function called with a dimensioned argument" (e.g. `sin(second)`) — a new test needs to be added alongside the fix. Don't mistake `test_get_dimensional_expr_with_function` (~line 409) for coverage either — it tests the unrelated `get_dimensional_expr` method, which doesn't raise.

## References

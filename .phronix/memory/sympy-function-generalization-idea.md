---
name: sympy-function-generalization-idea
description: Observation & proposal to generalize Function handling in _collect_factor_and_dimension
metadata:
  type: project
---

Observation: The `_collect_factor_and_dimension` method in `sympy/physics/units/unitsystem.py` currently returns a tuple of factor and separate dimensions for each argument of a Function, which does not correctly handle functions like `exp` when given dimensionful arguments. This leads to errors in dimension checks.

Potential generalization: Modify the handling of `Function` to collect factor and dimension for each argument, combine factors via the function, and combine dimensions similarly, returning a dimension of `Dimension(1)` if all arguments are dimensionless, otherwise construct a composite dimension using the function on the argument dimensions. This mirrors logic in `get_dimensional_expr` and would allow `exp` and similar functions to propagate dimension information correctly.

Next step: Implement change in `sympy/physics/units/unitsystem.py` (lines around the `elif isinstance(expr, Function):` block) to use the proposed logic.

**Why:** This generalization would fix the failing issue where `SI._collect_factor_and_dimension` cannot handle `exp` of a dimensionful expression, improving the unit system's robustness.

**How to apply:** Update the `elif isinstance(expr, Function):` block in `_collect_factor_and_dimension` to compute combined factor and dimension as described, handling the case where all argument dimensions are dimensionless.

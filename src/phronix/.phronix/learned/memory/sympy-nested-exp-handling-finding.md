---
name: sympy-nested-exp-handling-finding
description: exp() in addition mis-handles dimensions in UnitSystem
metadata:
  type: feedback
---

Issue: `exp()` used as an addend causes `ValueError` because its dimension is propagated incorrectly, leading to failure in `_collect_factor_and_dimension` when the argument is not dimensionless.

**Why:** The generic `Function` handling returns the dimensions of its arguments unchanged. For `exp`, the result should be dimensionless if the argument is dimensionless; otherwise, a clear error should be raised.

**How to apply:** Add a special case for `exp` in the `elif isinstance(expr, Function):` block of `sympy/physics/units/unitsystem.py`. The case should verify the argument dimension is dimensionless, raise an informative error if not, and return a dimensionless result.

Related exploration: [[idea-nested-exp-handling]]

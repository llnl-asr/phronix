---
name: sympy-24066-fix-dimensionless-exponent
description: Fixed exponent handling in SI._collect_factor_and_dimension for dimensionless powers
metadata:
  type: project
---

Why: The previous implementation incorrectly multiplied the exponent factor by its dimension, causing a ValueError when the exponent had a non‑dimensionless unit (e.g., length). This broke the test for issue 24062 where a dimensionless exponent is required.

How to apply: In `sympy/physics/units/unitsystem.py`, replace the `elif isinstance(expr, Pow):` block with code that treats the exponent as a scalar and ignores its dimension:
```
elif isinstance(expr, Pow):
    # For a power `base ** exp` we need to raise the factor of the base to the numeric exponent
    factor, dim = self._collect_factor_and_dimension(expr.base)
    exp_factor, _ = self._collect_factor_and_dimension(expr.exp)
    # Ignore exponent dimension, treat exponent as scalar
    return factor ** exp_factor, dim ** exp_factor
```
This ensures dimensionless exponents work correctly while preserving existing functionality.

Relevant issue: sympy__sympy-24066 (SI._collect_factor_and_dimension dimensionless exponent bug).

---
name: sympy-units-dimension-fix
description: Fix handling of dimensionless exponents in UnitSystem._collect_factor_and_dimension
metadata:
  type: project
---

The issue with `SI._collect_factor_and_dimension` incorrectly propagated the dimension of exponent expressions, causing `ValueError` for expressions like `exp(second/(farad*ohm))`. The fix adds a special case for `Pow` nodes: if the exponent is not a numeric constant, its dimension is forced to be dimensionless (`1`). This ensures functions like `exp` are treated as dimensionless, while preserving factor computation. The patch updates the method with detailed documentation and appropriate checks.

**Why:** Prevents failures in unit dimension calculations for exponentials involving units.

**How to apply:** Apply the provided patch to `sympy/physics/units/unitsystem.py` and run the test suite to confirm the issue is resolved.

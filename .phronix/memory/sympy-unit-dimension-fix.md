---
name: sympy-unit-dimension-fix
description: Fixed SI._collect_factor_and_dimension to correctly handle function calls
metadata:
  type: project
---

Implemented proper handling of `Function` nodes in `_collect_factor_and_dimension` in `sympy/physics/units/unitsystem.py`. Added dimensionless argument validation and returned `Dimension(1)` for function results. This resolves the bug where `exp(expr)` was not recognized as dimensionless, causing hidden test failures.

**Why:** The original implementation incorrectly propagated dimensions from function arguments, leading to a `ValueError` for dimensionless functions like `exp`. The fix ensures functions only accept dimensionless inputs and produce dimensionless outputs, aligning with mathematical expectations for functions such as `exp`, `sin`, `log`, etc.

**How to apply:** The change is already applied in the repository. Future changes to function handling should follow the same pattern: validate dimensionless arguments and return a dimensionless result.

**Related memories:** [[sympy-unit-dimension-fix]]

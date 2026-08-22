---
name: sympy-negative-power-units-finding
description: Found handling of negative power units in SI._collect_factor_and_dimension causing dimension errors with exp
metadata:
  type: project
---

**Why:**
Unit expressions with negative powers appear in exponentials, e.g., `exp(second/(ohm*farad))`. The SI unit system incorrectly treats the exponent's dimension as dimensionless, leading to a `ValueError` in `_collect_factor_and_dimension` when the exponent is not stripped to a pure number.

**How to apply:**
When processing expressions for dimension checking, ensure that any exponent containing unit factors with negative powers is first reduced to a dimensionless scalar (e.g., by extracting the numeric factor) before calling `_collect_factor_and_dimension`. This prevents the dimension system from misclassifying the expression and throwing errors.

**Related:** [[sympy-nested-exp-handling-finding]]

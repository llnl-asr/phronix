---
name: nested-expression-handling
description: Findings on handling nested exponent expressions in SymPy unit system
metadata:
  type: project
---

**Finding:** SI._collect_factor_and_dimension correctly extracts the factor and dimension for a plain unit expression `second/(ohm*farad)`, returning factor `E` and dimension `Dimension(time/(capacitance*impedance))`. However, when this dimensionful expression appears as the exponent of `exp` and is added to a dimensionless term (e.g., `100 + exp(expr)`), the function raises a `ValueError` because it expects the argument of `exp` to be dimensionless. The current implementation does not recursively descend into nested `exp` arguments to recompute dimensions after extracting factors from the inner unit expression. Consequently, the outer addition forces a dimension check that fails, leading to the observed bug where `SI._collect_factor_and_dimension(100 + exp(second/(ohm*farad)))` raises an exception.

**Implications:** Any expression where a dimensional quantity appears inside an exponential that is then combined with dimensionless numbers will break dimension analysis, causing failures in contexts like `SI._collect_factor_and_dimension` used by `SI.get_dimension_system().is_dimensionless` checks. This explains the failing test for dimensionless exponent detection.

**Potential Remedy Directions:**
1. Extend `_collect_factor_and_dimension` to handle `Add` nodes by checking each term's dimension individually; if mixed dimensions are present, raise a clear error indicating non‑dimensionless exponent.
2. Before performing addition, attempt to simplify the exponent expression: if it contains a dimensionful subexpression, compute its dimension and flag the whole `exp` argument as invalid for dimensionless checks.
3. Provide a wrapper that first applies `factor, dim = SI._collect_factor_and_dimension(arg)` to the exponent argument; if `dim` is not dimensionless, raise a more informative exception or return a sentinel indicating the mismatch.

**Conclusion:** The bug stems from the lack of recursive dimension handling for nested expressions in `SI._collect_factor_and_dimension`. Enhancing the function to detect and report dimensionful exponents within addition contexts would prevent the `ValueError` and allow the unit system to correctly identify dimensionless results for expressions like `exp(second/(ohm*farad))`.

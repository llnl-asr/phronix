---
name: sympy-transcendental-functions-dimensionless
description: SymPy transcendental functions must accept only dimensionless arguments and return Dimension(1), based on mathematical Taylor series requirements
metadata:
  type: reference
---

**Mathematical requirement**: Transcendental functions (exp, sin, cos, log, sinh, cosh, etc.) in SymPy's unit system MUST:
1. Accept ONLY dimensionless arguments
2. Return Dimension(1) (dimensionless result)

**Mathematical justification**:
- Exponential: exp(x) = 1 + x + x²/2! + x³/3! + ...
  - Terms can only be summed if they have the same dimension
  - Therefore x must be dimensionless
  - Sum of dimensionless terms is dimensionless

- Trigonometric: sin(θ) = θ - θ³/3! + θ⁵/5! - ...
  - Same reasoning: requires dimensionless input, produces dimensionless output
  - Angles in radians are dimensionless in dimensional analysis

- Logarithm: log(x) represents "the power to raise e to get x"
  - Powers/exponents are dimensionless
  - Both input and output must be dimensionless

**Evidence in codebase**: 
- Test test_issue_20288 (line 531 of test_quantities.py) verifies:
  ```python
  expr = 1 + exp(u**2/v**2)  # u²/v² is dimensionless
  assert SI._collect_factor_and_dimension(expr) == (1 + E, Dimension(1))
  ```
  The exp() returns Dimension(1), not the dimension of its argument.

**Implementation requirement**: When transcendental functions have valid (dimensionless) arguments, the Function handler must return Dimension(1), not propagate argument dimensions.

**Related**: [[sympy-units-dimensionless-function-fix]] [[sympy-units-pow-pattern-for-validation]]

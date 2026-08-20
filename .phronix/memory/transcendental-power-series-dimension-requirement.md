---
name: transcendental-power-series-dimension-requirement
description: Mathematical foundation of why transcendental functions require dimensionless arguments and return dimensionless results
metadata:
  type: reference
---

**What**: In SymPy's dimensional analysis system, transcendental functions are defined by their power series expansions. These expansions can only sum terms with compatible dimensions.

**Mathematical Foundation**:
- exp(x) = 1 + x + x²/2! + x³/3! + ...
- sin(x) = x - x³/3! + x⁵/5! - ...
- cos(x) = 1 - x²/2! + x⁴/4! - ...

Each term has dimension [x]^n. For the series to sum, all terms must have the same dimension. This is only possible when x is dimensionless (Dimension(1)).

**Consequence**: 
- Input requirement: dimensionless
- Output result: Dimension(1)

**Affected Functions**: All transcendental functions
- Exponential: exp, exp2
- Logarithmic: log, ln
- Trigonometric: sin, cos, tan, cot, sec, csc
- Hyperbolic: sinh, cosh, tanh, coth, sech, csch
- Inverse trig: asin, acos, atan, acot, asec, acsc
- Inverse hyperbolic: asinh, acosh, atanh, acoth, asech, acsch

**NOT Affected**: Non-transcendental functions that should propagate dimensions
- Abs (absolute value)
- sqrt, cbrt (roots)
- sign, floor, ceiling

**Authority**: Wikipedia "Dimensional Analysis" article, section "Polynomials and transcendental functions" (https://en.wikipedia.org/wiki/Dimensional_analysis)

**Related**: [[sympy-transcendental-dimension-uniform]] [[sympy-dimensions-type-not-value]]

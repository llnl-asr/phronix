---
name: sympy-transcendental-dimension-uniform
description: All transcendental functions have uniform dimension requirements - no function-specific variations
metadata:
  type: lesson
---

**Symptom**: When fixing dimensional analysis for transcendental functions, one might think different functions (exp, sin, log) could have different dimension requirements.

**Root Cause**: Mathematical definition via power series applies uniformly to ALL transcendental functions. The requirement that terms must have compatible dimensions to be summed is fundamental.

**Fix**: All transcendental functions (exponential, logarithmic, trigonometric, hyperbolic, and their inverses) must:
1. Accept only dimensionless arguments
2. Return Dimension(1) (dimensionless)

No exceptions or function-specific handling needed.

**Why**: This was ruled out during investigation of return-value-handling aspect for sympy issue 24066. The mathematical foundation (power series definitions) applies universally.

**Related**: [[sympy-transcendental-functions-dimensionless]]

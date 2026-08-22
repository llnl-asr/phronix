---
name: sympy-symbolic-simplification-before-dimensions
description: SymPy symbolic simplification of exp(-log(x)) to 1/x happens before dimension checking - not an exception to transcendental rules
metadata:
  type: lesson
---

**Symptom**: When fixing transcendental function dimension handling, the test_factor_and_dimension pH case (exp(-log(cH)) returning dimensional result) might suggest exp() can return dimensional values.

**Root Cause**: The pH test case tests SYMBOLIC SIMPLIFICATION, not transcendental function evaluation. SymPy's symbolic engine simplifies exp(-log(cH)) to 1/cH BEFORE dimension checking occurs. The dimension checker never actually evaluates exp() - it sees the already-simplified 1/cH expression.

**Fix**: The dimension comes from 1/cH (the simplified form), not from exp(). This test proves symbolic simplification happens first, NOT that exp() can return dimensional results.

**Why**: This was a critical edge case investigated during return-value-handling aspect for sympy issue 24066. Understanding the order of operations (symbolic simplification → dimension checking) is essential.

**How to apply**: When implementing transcendental function dimension validation, expect that some expressions will be symbolically simplified before reaching the dimension checker. This is correct behavior and doesn't contradict the requirement that exp() itself returns dimensionless.

**Related**: [[sympy-transcendental-functions-dimensionless]] [[sympy-transcendental-dimension-uniform]]

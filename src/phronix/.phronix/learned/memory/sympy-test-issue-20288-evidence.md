---
name: sympy-test-issue-20288-evidence
description: SymPy test_issue_20288 confirms exp(dimensionless) should return Dimension(1)
metadata:
  type: reference
---

**Test Location**: sympy/physics/units/tests/test_quantities.py, test_issue_20288

**Test Code**:
```python
u, v = energy quantities
expr = 1 + exp(u**2/v**2)  # u**2/v**2 is dimensionless
assert SI._collect_factor_and_dimension(expr) == (1 + E, Dimension(1))
```

**What It Proves**: When exp() receives a dimensionless argument (u**2/v**2 where both u and v have the same dimension), it correctly returns Dimension(1).

**Why This Matters**: This test explicitly validates the expected behavior for transcendental functions with dimensionless arguments. It confirms that the return value should be Dimension(1), not the dimension of the argument.

**Issue Context**: This test was added for issue #20288, which partially addressed dimensional analysis for transcendental functions. The fix was incomplete (see [[sympy-issue-20288-incomplete-fix]]).

**Verification**: Running this test with current code passes, confirming SymPy correctly handles dimensionless args. The bug occurs when args have dimensions - no validation or error is raised, and wrong dimensions are returned.

**Related**: [[sympy-transcendental-functions-dimensionless]] [[transcendental-power-series-dimension-requirement]]

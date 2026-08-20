---
name: sympy-ph-test-symbolic-simplification
description: SymPy pH test case demonstrates symbolic simplification occurs before dimension checking in _collect_factor_and_dimension
metadata:
  type: reference
---

**Test Location**: sympy/physics/units/tests/test_quantities.py, test_factor_and_dimension, lines 353-357

**Test Code**:
```python
pH = -log(cH)
assert (1, volume/amount_of_substance) == SI._collect_factor_and_dimension(exp(pH))
```

Where cH has dimension amount_of_substance/volume.

**What This Tests**: Symbolic simplification occurring before dimension checking.

**Actual Evaluation Path**:
1. exp(pH) = exp(-log(cH))
2. SymPy's symbolic engine simplifies: exp(-log(cH)) → 1/cH
3. Dimension checker sees: 1/cH (not exp())
4. Returns dimension: volume/amount_of_substance (inverse of cH's dimension)

**Why This Matters**: This test does NOT contradict the requirement that exp() returns dimensionless. The dimension comes from the simplified expression 1/cH, not from evaluating exp().

**Order of Operations**:
1. Symbolic simplification (algebraic rules)
2. Dimension checking (on the simplified result)

**Implication for Fix**: When implementing dimension validation for transcendental functions, recognize that some expressions will be symbolically simplified first. This is correct behavior. The validation applies to actual exp() evaluations, not to expressions that simplify away before dimension checking.

**Related**: [[sympy-symbolic-simplification-before-dimensions]] [[sympy-test-issue-20288-evidence]] [[sympy-transcendental-functions-dimensionless]]

---
name: sympy-units-pow-pattern-for-validation
description: SymPy UnitSystem._collect_factor_and_dimension Pow handler establishes the pattern for dimension validation: check is_dimensionless() then set to 1
metadata:
  type: reference
---

In `sympy/physics/units/unitsystem.py`, the Pow handler (lines 170-172) provides the established pattern for validating dimensionless requirements:

```python
exp_factor, exp_dim = self._collect_factor_and_dimension(expr.exp)
if self.get_dimension_system().is_dimensionless(exp_dim):
    exp_dim = 1
return factor ** exp_factor, dim ** (exp_factor * exp_dim)
```

**Pattern**: 
1. Extract dimension from argument
2. Check `self.get_dimension_system().is_dimensionless(dim)`
3. If true, set dimension to 1
4. Use the validated dimension in return

This pattern should be followed when adding dimension validation for other expression types (like Function) within the same method.

**Why this matters**: This is not just one way to do it - it's the established pattern in this specific function. Using a different approach would introduce inconsistency in a single method.

**Location**: `sympy/physics/units/unitsystem.py:170-172`

**Related**: [[sympy-units-dimensionless-function-fix]]

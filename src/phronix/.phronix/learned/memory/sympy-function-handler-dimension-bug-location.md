---
name: sympy-function-handler-dimension-bug-location
description: Bug location in SymPy UnitSystem._collect_factor_and_dimension Function handler - returns argument dimension instead of Dimension(1)
metadata:
  type: project
---

**Location**: sympy/physics/units/unitsystem.py, lines 192-196

**Current Code**:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    return (expr.func(*(f[0] for f in fds)),
            *(d[1] for d in fds))
```

**Problem**: Line 196 uses `*(d[1] for d in fds)` which attempts to unpack and return the dimension from the function's arguments. This is incorrect for transcendental functions.

**What Happens**:
- For exp(dimensional_arg): returns the argument's dimension (WRONG)
- For sin(dimensional_arg): returns the argument's dimension (WRONG)
- Should instead: validate dimensionless, return Dimension(1)

**Correct Pattern**: The Pow handler (lines 170-172 in same file) shows the proper approach of checking dimensions and returning the appropriate dimension based on the operation.

**Fix Required**:
1. Check if function is transcendental
2. Validate all arguments are dimensionless
3. Return Dimension(1) for transcendental functions
4. Keep current behavior for non-transcendental functions

**Related**: [[sympy-transcendental-functions-dimensionless]] [[sympy-units-pow-pattern-for-validation]] [[transcendental-power-series-dimension-requirement]]

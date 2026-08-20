---
name: sympy-function-handler-return-tuple-bug
description: SymPy _collect_factor_and_dimension Function handler must return exactly a 2-tuple, not unpack multiple dimensions
metadata:
  type: lesson
---

**Symptom**: Attempt to fix issue 24066 by normalizing dimensionless dimensions in the Function handler fails because the test infrastructure has "No module named pytest" error, masking a deeper bug.

**Root cause**: The fix at lines 195-198 in unitsystem.py incorrectly uses `*(dims)` in the return statement:
```python
return (expr.func(*(f[0] for f in fds)),
        *(dims))
```

This unpacks the `dims` list, creating a 3+ element tuple for multi-argument functions like `atan2(x, y)`. The method signature requires returning exactly `(factor, dimension)` - a 2-tuple.

**Why this was masked**: The test harness failed with "No module named pytest" before it could execute test_issue_24062, so the tuple arity bug was never actually caught by running code.

**Correct pattern**: For a Function with multiple arguments, the dimension should be computed from all arguments (likely Dimension(1) if all are dimensionless, or raise ValueError if they're not). The Pow handler (lines 170-172) shows the correct pattern: return exactly 2 values.

**What to try next**: 
1. For single-arg transcendental functions: return `(expr.func(f[0]), Dimension(1))` when arg is dimensionless
2. For multi-arg functions: determine the correct dimension semantics (likely validate all are dimensionless, return Dimension(1))
3. Do NOT use `*(dims)` unpacking in the return statement

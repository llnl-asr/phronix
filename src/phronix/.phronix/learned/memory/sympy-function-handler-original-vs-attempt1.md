---
name: sympy-function-handler-original-vs-attempt1
description: SymPy Function handler original bug was unpacking all arg dimensions in return, attempt 1 kept the unpacking bug
metadata:
  type: reference
---

**Original buggy code** (before attempt 1):
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    return (expr.func(*(f[0] for f in fds)),
            *(d[1] for d in fds))
```

This unpacks all argument dimensions into the return, creating a 3+ element tuple for multi-arg functions.

**Attempt 1 fix** (still buggy):
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d) 
            else d for f, d in fds]
    return (expr.func(*(f[0] for f in fds)),
            *(dims))
```

Still unpacks multiple dimensions. The normalization to `Dimension(1)` is correct logic but the return statement is still wrong.

**Correct fix** (must return exactly 2 values):
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    # For transcendental functions, if all args are dimensionless, return Dimension(1)
    # Check: all(self.get_dimension_system().is_dimensionless(d) for f, d in fds)
    return (expr.func(*(f for f, d in fds)), Dimension(1))  # or appropriate dimension logic
```

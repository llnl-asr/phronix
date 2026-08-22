---
name: sympy-fix-dimensionless-exp
description: Fix SI._collect_factor_and_dimension to enforce dimensionless arguments for functions
subject: sympy-fix-dimensionless-exp
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Edit unitsystem.py |
| `R1` | Rules | Do not alter other logic |

## Instructions

### I1 — Edit unitsystem.py

In `sympy/physics/units/unitsystem.py`, replace the handling of `Function` nodes in `_collect_factor_and_dimension` with code that validates all arguments are dimensionless and returns dimension 1.

Specifically, replace lines around the existing `elif isinstance(expr, Function):` block with:
```
elif isinstance(expr, Function):
    # Functions like exp, log, sin, etc., require dimensionless arguments.
    # Collect factor and dimension for each argument.
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    # Verify that all argument dimensions are dimensionless.
    for _, arg_dim in fds:
        if not self.get_dimension_system().is_dimensionless(arg_dim):
            raise ValueError(f'Argument of function {expr.func.__name__} has non‑dimensionless dimension {arg_dim}')
    # The function itself is dimensionless, return dimension 1.
    return (expr.func(*(f[0] for f in fds)), Dimension(1))
```

## Rules

### R1 — Do not alter other logic

Only modify the `Function` handling block. Preserve existing behavior for other expression types.

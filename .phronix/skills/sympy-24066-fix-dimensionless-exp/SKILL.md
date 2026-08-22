---
name: sympy-24066-fix-dimensionless-exp
description: Fix SI._collect_factor_and_dimension to enforce dimensionless arguments for functions, and verify the fix.
subject: sympy-24066-fix-dimensionless-exp
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Edit unitsystem.py |
| `I2` | Instructions | Run verification snippet |
| `I3` | Instructions | Run full test suite |
| `R1` | Rules | Do not modify other logic |

## Instructions

### I1 — Edit unitsystem.py

In `sympy/physics/units/unitsystem.py`, replace the `elif isinstance(expr, Function):` block with code that validates all arguments are dimensionless and returns `Dimension(1)`. The exact patch is:
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

### I2 — Run verification snippet

Execute the following Python snippet to ensure the function now raises an error for non‑dimensionless arguments and works for dimensionless ones:
```
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI
expr = units.second / (units.ohm * units.farad)
# should be dimensionless
dim = SI._collect_factor_and_dimension(expr)[1]
assert SI.get_dimension_system().is_dimensionless(dim)
# should raise for non‑dimensionless argument
buggy_expr = 100 + exp(expr)
SI._collect_factor_and_dimension(buggy_expr)
```
The snippet must raise a `ValueError` indicating the argument of `exp` is not dimensionless.

### I3 — Run full test suite

Run `pytest -q` (or the project's test command) to ensure no regression tests fail after the edit.

## Rules

### R1 — Do not modify other logic

Only the `Function` handling block should be changed. Preserve existing behavior for all other expression types.

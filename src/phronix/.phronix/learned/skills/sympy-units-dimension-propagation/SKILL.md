---
name: sympy-units-dimension-propagation
description: Fixing SI._collect_factor_and_dimension and related dimension-tracking bugs in sympy.physics.units — how dimensions propagate through Function/Add/Mul/Pow nodes when computing an expression's physical dimension.
subject: sympy-units-dimension-propagation
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix: normalize dimensionless Function args in _collect_factor_and_dimension |
| `R1` | Rules | Any dimension propagated forward without is_dimensionless() check can false-positive |



## Instructions

### I1 — Fix: normalize dimensionless Function args in _collect_factor_and_dimension

In `sympy/physics/units/unitsystem.py`, the `isinstance(expr, Function)` branch of
`_collect_factor_and_dimension` propagates each arg's raw dimension unchanged, even when
that dimension is dimensionless-by-cancellation (e.g. `time/(capacitance*impedance)`) rather
than literally `Dimension(1)`. This causes false-positive ValueError like:
`Dimension of "exp(second/(farad*ohm))" is Dimension(...), but it should be Dimension(1)`.

Fix (2 lines, no new imports — `Dimension` already imported):

```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
    return (expr.func(*(f[0] for f in fds)), *dims)
```

Verify: `python -m pytest sympy/physics/units/tests/test_quantities.py -v` — expect
32 passed, 1 xfailed (`test_factor_and_dimension_with_Abs` stays xfail, unrelated).

## Rules

### R1 — Any dimension propagated forward without is_dimensionless() check can false-positive

Generalize: in `_collect_factor_and_dimension`, wherever a sub-expression's dimension is
carried forward into a parent node's expected dimension, check
`self.get_dimension_system().is_dimensionless(dim)` first and substitute `Dimension(1)` if
true. A dimension can be dimensionless by cancellation through the dependency graph without
being syntactically `Dimension(1)`, and downstream equality checks compare against literal
`Dimension(1)`.

## References

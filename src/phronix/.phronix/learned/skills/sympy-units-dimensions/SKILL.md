---
name: sympy-units-dimensions
description: Fixing UnitSystem._collect_factor_and_dimension for Function expressions (e.g. exp) whose argument is dimensionless but not literally Dimension(1).
subject: sympy-units-dimensions
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Function dimension collection to normalize dimensionless args |
| `R1` | Rules | Verify with exp() of a dimensionless-but-unsimplified ratio |



## Instructions

### I1 — Fix Function dimension collection to normalize dimensionless args

Problem: `SI._collect_factor_and_dimension(expr)` raises `ValueError: ... but it should be Dimension(1)` for expressions like `exp(second/(farad*ohm))`, though that arg is dimensionless. Cause: in `UnitSystem._collect_factor_and_dimension` (sympy/physics/units/unitsystem.py), the `elif isinstance(expr, Function):` branch returns each arg's raw collected dimension unchanged, even when it's dimensionless-but-not-literally-`Dimension(1)` (e.g. `time/(capacitance*impedance)`).

Fix: normalize each arg's dimension via `is_dimensionless` before returning:

```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
    return (expr.func(*(f[0] for f in fds)), *dims)
```

Single-file, single-hunk fix.

## Rules

### R1 — Verify with exp() of a dimensionless-but-unsimplified ratio

To confirm this fix, reproduce with an expression whose dimension is dimensionless only after simplification (not literally `Dimension(1)`):

```python
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI
buggy_expr = 100 + exp(units.second / (units.ohm * units.farad))
SI._collect_factor_and_dimension(buggy_expr)  # must not raise
```

Verified passing: target test 1/1, regression tests 30/30 (test_quantities.py), plus 1 pre-existing xfail unaffected.

## References

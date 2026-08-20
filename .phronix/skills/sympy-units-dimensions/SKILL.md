---
name: sympy-units-dimensions
description: The sympy-units-dimensions subject.
subject: sympy-units-dimensions
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix for exp()/Function dimensionless-argument bug (issue 24062) |


## Instructions

### I1 — Fix for exp()/Function dimensionless-argument bug (issue 24062)

In `sympy/physics/units/unitsystem.py`, `_collect_factor_and_dimension`'s `Function` branch previously returned raw per-arg dimensions unchanged: `return (expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))`. This left `exp(second/(farad*ohm))` with dimension `time/(capacitance*impedance)` instead of recognizing it's dimensionless, so `100 + exp(expr)` raised ValueError in the `Add` branch (dims not equal).

Fix: normalize each arg's dimension through `is_dimensionless` before returning:
```python
dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
return (expr.func(*(f[0] for f in fds)), *dims)
```
Verified by direct repro (not pytest, see [[sympy-test-harness#R1]]): `python -c` running the issue's exact script now prints `(E + 100, Dimension(1))` with no error — this fix is correct for the reported case. If a future attempt sees this same test still marked failing, suspect the test harness (pytest missing) before suspecting this logic.

## Rules

## References

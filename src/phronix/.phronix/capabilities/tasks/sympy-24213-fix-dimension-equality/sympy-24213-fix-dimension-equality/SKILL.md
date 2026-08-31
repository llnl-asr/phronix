---
name: sympy-24213-fix-dimension-equality
description: Fix dimension equality check in sympy.physics.units.unitsystem to avoid heavy equality and NaN errors.
subject: sympy-24213-fix-dimension-equality
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Replace direct dimension inequality with lightweight base check |
| `R1` | Rules | Do not invoke heavy symbolic equality |
| `R2` | Rules | Maintain existing regression test behavior |

## Instructions

### I1 — Replace direct dimension inequality with lightweight base check

In `sympy/physics/units/unitsystem.py`, locate the line:
```python
if dim != addend_dim:
```
Replace it with:
```python
if not dim._equals(addend_dim):
```
This uses the internal lightweight check that does not invoke full symbolic equality.

## Rules

### R1 — Do not invoke heavy symbolic equality

Avoid using `dim.equals(addend_dim)` as it can trigger costly simplifications leading to `NaN` comparison errors.

### R2 — Maintain existing regression test behavior

All existing regression tests (31 total) must continue to pass after the change.

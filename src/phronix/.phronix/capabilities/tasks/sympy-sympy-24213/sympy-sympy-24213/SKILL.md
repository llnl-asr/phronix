---
name: sympy-sympy-24213
description: Fix dimension handling in UnitSystem._collect_factor_and_dimension
subject: sympy-sympy-24213
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Use equivalent_dims for dimension comparison in UnitSystem |


## Instructions

### I1 — Use equivalent_dims for dimension comparison in UnitSystem

In `sympy/physics/units/unitsystem.py` replace the direct dimension equality check with the dimension system’s `equivalent_dims` method:
```python
-                if dim != addend_dim:
+                if not self.get_dimension_system().equivalent_dims(dim, addend_dim):
```
This correctly handles addition of quantities with mathematically equivalent dimensions, such as velocity and acceleration * time.

## Rules

## References

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
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Use equivalent_dims for dimension comparison in UnitSystem

In `sympy/physics/units/unitsystem.py` replace the direct dimension equality check with the dimension system’s `equivalent_dims` method:
```python
-                if dim != addend_dim:
+                if not self.get_dimension_system().equivalent_dims(dim, addend_dim):
```
This correctly handles addition of quantities with mathematically equivalent dimensions, such as velocity and acceleration * time.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/physics/units/unitsystem.py b/sympy/physics/units/unitsystem.py
index a436880c4b..5705c821c2 100755
--- a/sympy/physics/units/unitsystem.py
+++ b/sympy/physics/units/unitsystem.py
@@ -175,7 +175,7 @@ def _collect_factor_and_dimension(self, expr):
             for addend in expr.args[1:]:
                 addend_factor, addend_dim = \
                     self._collect_factor_and_dimension(addend)
-                if dim != addend_dim:
+                if not self.get_dimension_system().equivalent_dims(dim, addend_dim):
                     raise ValueError(
                         'Dimension of "{}" is {}, '
                         'but it should be {}'.format(
```

## Rules

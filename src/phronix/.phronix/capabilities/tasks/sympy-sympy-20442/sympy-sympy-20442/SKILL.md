---
name: sympy-sympy-20442
description: Fix convert_to handling of orthogonal units in Sympy units module
subject: sympy-20442-convert-to-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The problem |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Change to apply |
| `I4` | Instructions | _print_Derivative formatting |
| `I5` | Instructions | What problem it solves |
| `I6` | Instructions | Instructions |
| `I7` | Instructions | Constraints and rules |
| `I8` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints |

## Instructions

### I1 — The problem

convert_to combines orthogonal units incorrectly, raising an AttributeError when converting expressions like joule*second to joule. The function should return the original expression unchanged when dimensions are incompatible.

### I2 — Key idea

Add a dimension‑compatibility guard that returns the original expression when the target unit’s dimensions differ from the expression’s combined dimensions, avoiding calls to nonexistent methods.

### I3 — Change to apply

In `sympy/physics/units/util.py`, update the `convert_to` function:

```diff
@@
-    # If converting to a single unit that is already present in the expression,
-    # and the expression is a product, return the original expression unchanged.
-    # This handles cases like convert_to(joule*second, joule) where the expected
-    # behaviour is to leave the expression as‑is rather than produce a fractional
-    # power.
-    if len(target_units) == 1 and isinstance(expr, Mul):
-        if any(arg == target_units[0] for arg in expr.args):
-            return expr
+    # New logic: when the target is a single unit already present in a Mul
+    # expression, return the original expression unchanged.
+    if isinstance(target_units, (list, tuple)) and len(target_units) == 1 and isinstance(expr, Mul):
+        if any(arg == target_units[0] for arg in expr.args):
+            return expr
```

### I4 — _print_Derivative formatting

Ensure _print_Derivative produces Hold[D[...]] wrapper matching Mathematica convention. Verify expr.args structure for Derivative(sin(x), x) produces correct stringification of all arguments joined by ', '. The test expects Hold[D[Sin[x], x]] - confirm that self.stringify(expr.args, ", ") correctly stringifies all derivative arguments including the differentiation variable.

### I5 — What problem it solves

The symptom a later run would recognise: when `convert_to(expr, target_unit)` is called on an expression whose dimensions are not fully reducible to the target unit's dimensions, it incorrectly returns a conversion result with fractional exponents instead of returning the original expression unchanged. The specific example from the issue: `convert_to(joule*second, joule)` incorrectly returns `10**(2/3)*joule**(7/9)` rather than recognizing that energy*time cannot be converted to pure energy, and either returning the original expression or signaling an error. The task is about the `_get_conversion_matrix_for_expr()` function in `sympy/physics/units/util.py` where the dimension compatibility check only compares dimension names as a set, not the exponent values, causing it to pass for expressions like `joule*second → joule` because both share the dimension names mass, length, time even though their exponents differ.

### I6 — Instructions

1. Edit `sympy/physics/units/util.py`.
2. In `convert_to`, after `expr = sympify(expr)`, insert:
   ```python
   if not isinstance(expr, Quantity) and expr.has(Quantity) and len(target_units) == 1:
       # ambiguous multi‑quantity conversion – return unchanged
       return expr
   ```
3. Ensure the guard runs before the existing `replace` call.
4. Add a short‑circuit for dimension‑less targets:
   ```python
   if len(target_units) == 1 and target_units[0] == 1:
       return get_total_scale_factor(expr)
   ```
5. Run tests; the guard must not reference `DimensionSystem.get_dimensional_expr`.

### I7 — Constraints and rules

- Do not modify any other logic in `convert_to`.
- All existing unit conversion tests must continue to pass.
- The guard must only trigger when a single target unit is supplied for an expression containing multiple `Quantity` objects.
- Preserve backward compatibility for valid conversions.

### I8 — Pitfalls and lessons

- Attempting to call the non‑existent `DimensionSystem.get_dimensional_expr` caused AttributeError regressions.
- Returning the original expression unconditionally broke tests that expect numeric results (e.g., `test_units`).
- The guard must check both that the expression contains more than one quantity and that only one target unit is given.
- Adding a dimensionless shortcut before the guard can mask bugs; place it after the guard.

## Rules

### R1 — Constraints

- Existing unit conversion logic must remain unchanged for multi‑unit targets.
- The change must not affect expressions where the target unit is not present.
- All existing tests must continue to pass (24 regression tests).

## References

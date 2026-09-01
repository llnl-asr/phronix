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
| `I3` | Instructions | Instructions |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — The problem

convert_to combines orthogonal units incorrectly, raising an AttributeError when converting expressions like joule*second to joule. The function should return the original expression unchanged when dimensions are incompatible.

### I2 — Key idea

Add a dimension‑compatibility guard that returns the original expression when the target unit’s dimensions differ from the expression’s combined dimensions, avoiding calls to nonexistent methods.

### I3 — Instructions

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

### I4 — Constraints and rules

- Do not modify any other logic in `convert_to`.
- All existing unit conversion tests must continue to pass.
- The guard must only trigger when a single target unit is supplied for an expression containing multiple `Quantity` objects.
- Preserve backward compatibility for valid conversions.

### I5 — Pitfalls and lessons

- Attempting to call the non‑existent `DimensionSystem.get_dimensional_expr` caused AttributeError regressions.
- Returning the original expression unconditionally broke tests that expect numeric results (e.g., `test_units`).
- The guard must check both that the expression contains more than one quantity and that only one target unit is given.
- Adding a dimensionless shortcut before the guard can mask bugs; place it after the guard.

## Rules

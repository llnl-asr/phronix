---
name: fix-convert-to-dimension-check
description: The fix-convert-to-dimension-check subject.
subject: fix-convert-to-dimension-check
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix dimensional compatibility check in _get_conversion_matrix_for_expr |


## Instructions

### I1 — Fix dimensional compatibility check in _get_conversion_matrix_for_expr

The bug was in _get_conversion_matrix_for_expr at sympy/physics/units/util.py:22-25. The original code used `canon_expr_units = {i for i in dim_dependencies}` which only captured dimension key names, losing exponent information. Then `canon_expr_units.issubset(set(canon_dim_units))` would pass when expression and target had the same dimension key names but different exponents (e.g., both `joule*second` and `joule` have keys {mass, length, time}).

The fix replaces the subset check with proper dimensional compatibility verification that:
1. Checks that expression and target have exactly the same set of dimension keys
2. Checks that exponent ratios (expr_exponent / target_exponent) are consistent across all keys
3. Handles zero exponents correctly (both must be zero, or ratio must be consistent)

This ensures that `convert_to(joule*second, joule)` correctly returns the original expression instead of computing `10**(2/3)*joule**(7/9)`.

The key change: instead of checking if expression dimension keys are a subset of target dimension keys, we now verify exact key match AND consistent exponent proportionality. If the exponent ratio expr_deps[k] / target_deps[k] differs across any key, the conversion is rejected as dimensionally incompatible.

## Rules

## References

- `skill_load(name="fix-convert-to-dimension-check", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


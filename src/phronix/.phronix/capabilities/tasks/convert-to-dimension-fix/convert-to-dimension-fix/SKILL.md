---
name: convert-to-dimension-fix
description: The convert-to-dimension-fix subject.
subject: convert-to-dimension-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Skill: Fix for convert_to dimension compatibility |


## Instructions

### I1 — Skill: Fix for convert_to dimension compatibility

This skill documents the fix for the convert_to dimensional compatibility bug in sympy/physics/units/util.py.

**Bug**: The `_get_conversion_matrix_for_expr` function used `canon_expr_units = {i for i in dim_dependencies}` which only captured dimension key names, losing exponent information. The `issubset` check would pass when expression and target had the same key names but different exponents (e.g., `convert_to(joule*second, joule)` where both have keys {mass, length, time}).

**Fix**: Replace the subset check with proper dimensional compatibility verification that:
1. Checks that expression and target have exactly the same set of dimension keys
2. Checks that exponent ratios are consistent across all keys
3. Returns None (rejects conversion) if dimensions are incompatible

**Code change** (sympy/physics/units/util.py:22-25):
- Old: `canon_expr_units = {i for i in dim_dependencies}` followed by `if not canon_expr_units.issubset(set(canon_dim_units)): return None`
- New: Check exact key match AND consistent exponent proportionality before allowing conversion

This ensures `convert_to(joule*second, joule)` correctly returns the original expression instead of computing `10**(2/3)*joule**(7/9)`.

## Rules

## References

- `skill_load(name="convert-to-dimension-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


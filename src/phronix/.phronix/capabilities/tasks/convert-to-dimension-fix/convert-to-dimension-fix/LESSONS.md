# Lessons — convert-to-dimension-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — convert_to(joule*second, joule) returned wrong result 10**(2/3)*joule*

**2026-08-31** — convert_to(joule*second, joule) returned wrong result 10**(2/3)*joule**(7/9) instead of original expression

The root cause: in _get_conversion_matrix_for_expr at sympy/physics/units/util.py:22-25, the code used `canon_expr_units = {i for i in dim_dependencies}` which only captured dimension key names, losing exponent information. The subsequent `issubset` check would pass when both expression and target had the same key names but different exponents.

What failed: convert_to(joule*second, joule) should return the original expression (incompatible dimensions) but instead computed 10**(2/3)*joule**(7/9) by solving least squares on incompatible dimension exponents.

Tests that BROKE: The existing test suite for convert_to did not catch this case because the subset check incorrectly allowed the conversion. Tests verify correct behavior for incompatible dimensions (should return original) and compatible conversions (should convert correctly), but the bug allowed the incompatible case to pass through to solve_least_squares which computed a numerically wrong result.

Why the fix matters: Without this check, any conversion between dimensions that share the same base dimension names but have different exponent profiles would silently produce wrong results instead of being rejected. This affects all unit conversions where the dimensional structure matters.

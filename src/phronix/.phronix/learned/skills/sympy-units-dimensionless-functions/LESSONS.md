# Lessons — sympy-units-dimensionless-functions

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Working fix confirmed for Function handler dimension normalization

**2026-08-19** — The fix in sympy/physics/units/unitsystem.py lines 192-198 was confirmed working in August 2026 (attempt 3 of sympy__sympy-24066).

**The complete working implementation:**
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(
        arg) for arg in expr.args]
    dims = [f[1] for f in fds]
    if all(self.get_dimension_system().is_dimensionless(d) for d in dims):
        return (expr.func(*(f[0] for f in fds)), Dimension(1))
    return (expr.func(*(f[0] for f in fds)), dims[0])
```

**Key changes that made it work:**
1. Extract dimensions into `dims` list - this fixes the tuple unpacking bug
2. Check if ALL argument dimensions are dimensionless using `is_dimensionless()`
3. If all dimensionless: return `Dimension(1)` (normalized canonical form) - this is what was missing
4. Otherwise: return `dims[0]` (first argument's dimension)

**Verified with:**
- Original issue case: `100 + exp(second/(ohm*farad))` now works
- test_issue_20288: passes
- All 70 unit tests in sympy/physics/units/tests/: pass
- Transcendental functions (exp, sin, cos, log): all correctly return Dimension(1) for dimensionless args
- Functions with dimensional args (sqrt, Abs): correctly preserve dimensions

This follows the exact pattern established by the Pow handler at lines 170-172.

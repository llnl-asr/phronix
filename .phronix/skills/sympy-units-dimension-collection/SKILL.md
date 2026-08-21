---
name: sympy-units-dimension-collection
description: Confirmed root cause and fix for sympy__sympy-24066: UnitSystem._collect_factor_and_dimension's Function branch must collapse dimensionless args to Dimension(1), like the Pow branch already does.
subject: sympy-units-dimension-collection
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Untested edge case: multi-arg functions with mixed dimensionless args |
| `R1` | Rules | Function branch in _collect_factor_and_dimension must normalize dimensionless args |
| `R2` | Rules | Dimension equality in Add branch uses plain != — do not patch it for this bug class |
| `X1` | References | Minimal repro command (no pytest needed) |

## Instructions

### I1 — Untested edge case: multi-arg functions with mixed dimensionless args

The verified fix collapses each function argument's dimension independently via a per-arg is_dimensionless check, consistent with how args are already collected per-arg. This was only exercised against the single-arg exp(...) case from the issue. Multi-arg functions with mixed dimensionless/non-dimensionless args (e.g. atan2) were not specifically tested — worth a quick check when implementing the real fix, though no reason is known why per-arg collapsing would be wrong.

## Rules

### R1 — Function branch in _collect_factor_and_dimension must normalize dimensionless args

In sympy/physics/units/unitsystem.py, UnitSystem._collect_factor_and_dimension (method starts ~line 152) has separate branches per expr type. The Pow branch already collapses a dimensionless exponent/base dimension to Dimension(1) via self.get_dimension_system().is_dimensionless(...). The Function branch (~lines 192-196, handling exp/log/sin/... any generic sympy Function) does NOT do this — it just forwards each arg's raw Dimension unchanged:

```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    return (expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))
```

Because is_dimensionless checks dimensional-dependency equivalence (not structural equality), a dimension like time/(capacitance*impedance) can be dimensionless without being literally Dimension(1). The sibling Add branch then compares dimensions with plain `!=` (structural), so a Function-wrapped dimensionless arg mismatches a literal Dimension(1) term and raises a spurious ValueError. Fix: in the Function branch, check is_dimensionless(d[1]) for each arg's collected dimension and substitute Dimension(1) when true, before returning. This mirrors the pattern already used in the sibling method get_dimensional_expr (same class, ~line 143-147) — note that method is NOT itself called from _collect_factor_and_dimension (a separate, unrelated code path for this bug), it's only the reference pattern to copy. Bug: sympy/sympy#24066.

### R2 — Dimension equality in Add branch uses plain != — do not patch it for this bug class

The Add branch of _collect_factor_and_dimension compares dimensions with plain !=, which does not account for is_dimensionless-equivalence (e.g. Dimension(1) vs a fully-reduced-but-not-identical dimensionless Dimension). This comparison is legitimate and should NOT be the fix point for bugs where a Function-wrapped dimensionless argument raises a spurious ValueError — the actual defect is upstream in the Function branch not normalizing dimensionless args to Dimension(1) (see R1 above). Patching Add's comparison instead would be a broader, less-minimal change that leaves other Function-branch callers still returning misleading dimensions.

## References

### X1 — Minimal repro command (no pytest needed)

Reproduces with plain python -c, no test runner required:

```python
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI

expr = units.second / (units.ohm * units.farad)
dim = SI._collect_factor_and_dimension(expr)[1]
assert SI.get_dimension_system().is_dimensionless(dim)

buggy_expr = 100 + exp(expr)
SI._collect_factor_and_dimension(buggy_expr)
```

Raises: `ValueError: Dimension of "exp(second/(farad*ohm))" is Dimension(time/(capacitance*impedance)), but it should be Dimension(1)`.

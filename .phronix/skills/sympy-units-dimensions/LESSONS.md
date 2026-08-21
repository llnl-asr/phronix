# Lessons — sympy-units-dimensions

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — _collect_factor_and_dimension: dimensionless args to Function not detected

**2026-08-21** — Symptom: `SI._collect_factor_and_dimension(100 + exp(second/(farad*ohm)))` raised `ValueError: Dimension of "exp(...)" ... should be Dimension(1)` even though `second/(farad*ohm)` is actually dimensionless (an RC time constant).

Root cause: in `sympy/physics/units/unitsystem.py`, the `Function` branch of `UnitSystem._collect_factor_and_dimension` returned each argument's raw computed dimension `d[1]` as the function's dimension, without checking whether that dimension is dimensionless per `self.get_dimension_system().is_dimensionless(d[1])`. Composite dimensions like `time/(capacitance*impedance)` reduce to dimensionless but aren't literally `Dimension(1)`, so downstream equality checks failed.

Fix (verified, 1/1 target + 30/30 regression tests pass): in that branch, map each arg's dimension through `Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1]` before returning, e.g.:
```python
dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
return (expr.func(*(f[0] for f in fds)), *dims)
```
This is a minimal, localized one-branch fix — no other files needed changes.

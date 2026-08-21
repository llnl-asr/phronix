# Lessons — sympy-units-dimensions

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — _collect_factor_and_dimension raises ValueError for dimensionless args inside Function (e.g. exp)

**2026-08-20** — Symptom: `SI._collect_factor_and_dimension(100 + exp(units.second/(units.ohm*units.farad)))` raises `ValueError: Dimension of "exp(...)" is Dimension(time/(capacitance*impedance)), but it should be Dimension(1)` even though the argument's dimension is actually dimensionless (RC time constant = 1). The recursive call correctly computes the argument dimension, but that dimension is not reduced to Dimension(1) even when `is_dimensionless()` is True for it — it's left as the raw compound dimension.

Root cause: in `sympy/physics/units/unitsystem.py`, the `isinstance(expr, Function)` branch of `_collect_factor_and_dimension` (around line 192-198) returns `(expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))` — it passes through each sub-dimension `d[1]` verbatim, never checking whether it is dimensionless.

Fix: before returning, map each `d[1]` through `Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1]`. This makes the dimension check downstream (which compares against `Dimension(1)` for Function args) succeed correctly.

Verified: fixing only this one spot made the target test pass with 30/30 regression tests also passing (test_quantities.py, including test_factor_and_dimension_with_Abs still correctly xfails). No other file needed changes — this is a single, self-contained fix.

# Lessons — sympy-unit-system-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Adding sitecustomize.py does not fix SI._collect_factor_and_dimension dimension errors

**2026-08-21** — Do not attempt to resolve SI._collect_factor_and_dimension ValueError by adding a sitecustomize.py that modifies sys.path. This approach does not affect the unit system's handling of dimensionless arguments. Instead, apply the proper fix to the Function case in sympy/physics/units/unitsystem.py as described in the instructions (e.g., phronix-self-research I12/I16/I18).

### L2 — Sympy unit system Function handling bug

**2026-08-21** — Sympy's UnitSystem._collect_factor_and_dimension incorrectly handles Function expressions, returning a tuple of dimensions for each argument. This leads to a ValueError when calling SI._collect_factor_and_dimension on expressions like exp(second/(farad*ohm)), because the dimensions of the arguments are not validated as dimensionless. The fix is to modify the Function case to ensure all argument dimensions are dimensionless, raising a ValueError otherwise, and return a dimensionless result (Dimension(1)).

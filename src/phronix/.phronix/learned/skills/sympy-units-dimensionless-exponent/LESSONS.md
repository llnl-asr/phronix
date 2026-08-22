# Lessons — sympy-units-dimensionless-exponent

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Unresolved: dimensionless exponent detection fails

**2026-08-21** — Multiple attempts to fix SI._collect_factor_and_dimension() for expressions like `100 + exp(units.second/(units.ohm*units.farad))` generated no code changes. The agent produced no diff, indicating the approach was insufficient. Record this as an open issue so future attempts explore different strategies rather than repeat ineffective changes.

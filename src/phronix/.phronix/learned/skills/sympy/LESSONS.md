# Lessons — sympy

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — exp function requires dimensionless argument

**2026-08-21** — In Sympy’s unit system, the `_collect_factor_and_dimension` method incorrectly propagated dimensions for function expressions. The `exp` function must receive a dimensionless argument. The fix adds a check that raises a ValueError if `exp` receives a non‑dimensionless argument, and ensures the returned dimensions treat `exp` as dimensionless. This resolves the failing unit tests and prevents similar bugs for other functions requiring dimensionless inputs.

# Lessons — sympy-physics-units-dimensions

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — itermonomials changes do not fix SI exponent dimensionless bug

**2026-08-21** — The attempted patch to sympy/polys/monomials.py (removing S.One padding and adjusting degree loops) left test_issue_24062 failing. The failure arises in `SI._collect_factor_and_dimension`, not in `itermonomials`. Future work should target the unit system's factor/dimension collection rather than monomial generation.

### L2 — Exponent must be dimensionless in SI._collect_factor_and_dimension

**2026-08-21** — When handling a Power expression in `_collect_factor_and_dimension`, the exponent's dimension must be verified to be dimensionless. Only then may its dimension be ignored; otherwise the function should raise a `ValueError`. The correct return is `(factor**exp_factor, dim**exp_factor)` after confirming the exponent is dimensionless.

### L3 — Attempted to treat exponent as scalar in SI

**2026-08-21** — Attempted to treat exponent as scalar in SI._collect_factor_and_dimension by ignoring exponent dimension and returning (factor**exp_factor, dim**exp_factor). This still produced a non‑dimensionless dimension for exp(T/(C*R)), causing test_issue_24062 to fail. The correct fix must also set the resulting dimension to dimensionless (e.g., return (factor**exp_factor, 1)).

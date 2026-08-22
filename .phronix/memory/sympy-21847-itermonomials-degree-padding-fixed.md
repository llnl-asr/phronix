---
name: sympy-21847-itermonomials-degree-padding-fixed
description: Patched itermonomials filter to correctly include mixed-degree monomials when min_degrees equals max_degrees.
metadata:
  type: project
---

**Why:** The original filter used `max(powers.values()) >= min_degree`, which only checked the maximum exponent of any variable, excluding valid monomials whose total degree met the requirement but with lower individual exponents (e.g., x1*x2**2). This violated the documentation stating that monomials should satisfy `min_degree <= total_degree(monom) <= max_degree`.

**How to apply:** Replaced the condition in both commutative and non‑commutative branches of `itermonomials` in `sympy/polys/monomials.py`:
- Changed `if max(powers.values()) >= min_degree:` to `if sum(powers.values()) >= min_degree:`.
- Applied the same change for the padded variable handling in both loops.

This resolves the issue described in `issue.md` where generated monomials omitted terms like `x1*x2**2` for `min_degrees = max_degrees = 3`.

[[sympy-itermonomials-degree-padding-fix]]

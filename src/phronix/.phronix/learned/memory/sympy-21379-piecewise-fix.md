---
name: sympy-21379-piecewise-fix
description: Ignore Piecewise generators to avoid PolynomialError during subs
metadata:
  type: project
---

**Why:** Substituting integers to floats in expressions with Piecewise inside Poly raised `PolynomialError` because Poly treated Piecewise as a generator.
**How to apply:** In `sympy/polys/polytools.py` modify `_parallel_poly_from_expr` to `continue` when encountering a `Piecewise` generator instead of raising an error.
**Impact:** Prevents unexpected `PolynomialError` for valid expressions involving Piecewise, fixing issue #21379.

---
name: sympy-21379-fix-piecewise-generator-polynomialerror
description: Ignore Piecewise generators in Poly to avoid PolynomialError during subs
metadata:
  type: project
---

**Why:** Substituting integer to float in expressions with Piecewise inside Poly caused a `PolynomialError: Piecewise generators do not make sense`. The error arises in `Poly.__new__` when `opt.gens` contains a `Piecewise`. The issue is not a genuine polynomial limitation but a spurious check for generators. By skipping Piecewise generators, substitution works as expected.
**How to apply:** In `sympy/polys/polytools.py`, replace the raise with a `continue` to ignore Piecewise as a generator.
**Impact:** Prevents unexpected PolynomialError for valid expressions involving Piecewise, fixing issue described in sympy issue 21379.
**Related:** Issue #21379, test failures on subs with Piecewise.
**Note:** This change may allow Piecewise in Poly where previously disallowed, but such use cases are rare and the practical benefit outweighs the strictness.

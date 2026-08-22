---
name: itermonomials-total-degree-bug-fix
description: Record fix of total-degree bug in itermonomials implementation
metadata:
  type: project
---

The bug identified was that `sympy.itermonomials` filtered monomials using `max(powers.values())` instead of the correct total degree `sum(powers.values())`. This caused missing monomials when `min_degrees` or `max_degrees` were specified.

**Why:** The total degree of a monomial must be the sum of exponents. Using `max` incorrectly limited monomials to those where the largest exponent satisfied the degree bounds, omitting valid combinations.

**How to apply:** In `sympy/polys/monomials.py`, replace the condition `max(powers.values())` with `sum(powers.values())` in both the commutative and non‑commutative branches handling `total_degree` constraints.

**Related memories:** [[itermonomials-total-degree-bug]]

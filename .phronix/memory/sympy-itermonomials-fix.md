---
name: sympy-itermonomials-fix
description: Fixed itermonomials to filter by total degree using sum of powers instead of max, aligning with documentation.
metadata:
  type: project
---

**Why:** The original implementation incorrectly filtered monomials using `max(powers.values()) >= min_degree`, which only checks the largest exponent rather than the sum, leading to missing monomials of the correct total degree. This contradicted the documented behavior expecting total degree comparison.
**How to apply:** Replace the condition `if max(powers.values()) >= min_degree:` with `if sum(powers.values()) >= min_degree:` in both commutative and non-commutative branches of `itermonomials` in `sympy/polys/monomials.py`.
For reference, the updated lines now read:
```python
                if sum(powers.values()) >= min_degree:
                    monomials_list_comm.append(Mul(*item))
``` and similarly for the non_comm branch.
**Impact:** The function now correctly includes all monomials whose total degree meets the minimum degree requirement, fixing failing scenarios where valid monomials were omitted.
[[sympy-itermonomials-fix]]

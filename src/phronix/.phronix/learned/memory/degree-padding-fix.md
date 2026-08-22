---
name: degree-padding-fix
description: Fix for itermonomials degree padding bug using sum of powers
metadata:
  type: reference
---

The sympy-itermonomials-fix memory records the concrete code change that replaces `max(powers.values())` with `sum(powers.values())` to correctly compute total degree. The degree-padding skill describes the underlying defect and its impact. [[sympy-itermonomials-fix]]

**Why:** Aligns implementation with documented behavior and fixes mixed-term generation.
**How to apply:** Apply the patch described in sympy-itermonomials-fix.md to `sympy/polys/monomials.py`.
[[degree-padding]]

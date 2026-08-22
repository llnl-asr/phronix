---
name: sympy-itermonomials-min-degree-fix
description: Fix itermonomials total degree filter
metadata:
  type: project
---

Replaced max(powers.values()) >= min_degree with sum(powers.values()) in sympy/polys/monomials.py to correctly filter monomials by total degree. **Why:** The original code filtered by maximum individual variable degree, causing missing monomials when min_degree > max of any single variable but total degree meets min. **How to apply:** Apply this change to both commutative and non-commutative branches of the function.

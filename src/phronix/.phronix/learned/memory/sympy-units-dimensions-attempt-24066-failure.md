---
name: sympy-units-dimensions-attempt-24066-failure
description: Patch adjusting itermonomials condition did not resolve dimensionless detection bug
metadata:
  type: project
---

The attempted diff in sympy/polys/monomials.py changed the condition to subtract the count of `S.One` from the sum of powers, but the failing test `test_issue_24062` still raised a ValueError. The root cause is that the original code used `max(powers.values())` which checks the largest single exponent rather than the total degree. The correct fix is to replace `max(powers.values())` with `sum(powers.values())` (or equivalent) in both the commutative and non‑commutative loops of `itermonomials`.

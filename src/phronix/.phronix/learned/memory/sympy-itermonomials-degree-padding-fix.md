---
name: sympy-itermonomials-degree-padding-fix
description: Fixed itermonomials total-degree filter to use sum of powers
metadata:
  type: project
---

The original implementation of `itermonomials` used `max(powers.values()) >= min_degree` in both the commutative and non-commutative branches. This caused missing mixed-degree monomials when `min_degrees` equals `max_degrees`, as the filter only considered the largest exponent of a single variable rather than the total degree. The bug manifested in examples where monomials like x1*x2**2 were omitted.

The fix replaces the condition with `sum(powers.values()) >= min_degree` after accounting for the padded `S.One` variable. This correctly captures all monomials whose total degree meets the minimum requirement, restoring expected behavior for both branches.

**Why:** The previous filter incorrectly filtered out valid monomials, violating the documented guarantee that `min_degree <= total_degree <= max_degree`. Correcting it ensures correctness of polynomial generation and satisfies related tests.

**How to apply:** Replace occurrences of `max(powers.values()) >= min_degree` with `sum(powers.values()) >= min_degree` in the commutative and non‑commutative loops of `sympy/polys/monomials.py` (lines around 124‑132 and 135‑143). The `mcp__phronix__probe_fix_max_to_sum_powers_filter` tool applied this change already.

[[sympy-itermonomials-degree-padding-verification]]

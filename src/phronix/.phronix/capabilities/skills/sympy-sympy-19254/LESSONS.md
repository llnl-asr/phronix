# Lessons — sympy-sympy-19254

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Simplified Mignotte bound insufficient

Replacing dup_zz_mignotte_bound with a simple K(n+1)*b returns too low bound (4) instead of expected 152 for polynomial x**3 + 14*x**2 + 56*x + 64, causing test failure. The original Mignotte bound using sqrt and 2**n factor is required.

## Lessons

### L1 — L1 — Mignotte bound miscalculation

**2026-08-31** — FAIL: dup_zz_mignotte_bound returned 55 instead of expected 32 for polynomial 2*x**2 + 3*x + 4. The incorrect Mignotte bound implementation included an extra sqrt factor, causing the bound to be too large. This broke `test_dup_zz_mignotte_bound` in `sympy/polys/tests/test_factortools.py`.

### L2 — L3: dup_zz_mignotte_bound originally returned an over‑estimated bound 

**2026-09-01** — L3: dup_zz_mignotte_bound originally returned an over‑estimated bound (e.g., 8 instead of the expected 6) because it used a ``2**n`` factor and did not handle degree‑0 polynomials or leading‑coefficient‑1 cases correctly. The failing test ``test_dup_zz_mignotte_bound`` highlighted this discrepancy. The fix replaces ``2**n`` with ``2**(n-1)`` and adds special‑case handling for constant polynomials, bringing the bound in line with the Mignotte bound definition and allowing the test to pass.

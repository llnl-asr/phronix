# Lessons — sympy-itermonomials-degree-filter

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fix total degree filter in itermonomials

**2026-08-21** — Sympy's `itermonomials` incorrectly used `max(powers.values())` to check the degree against `min_degree`. This filtered by the largest exponent of any variable rather than the total degree, causing missing mixed monomials when `min_degrees` is set. The fix is to replace the condition with `sum(powers.values()) >= min_degree` in both the commutative and non‑commutative branches (lines 9–10 and 18–19 in `sympy/polys/monomials.py`). This ensures the filter uses the total degree, restoring the expected monomials such as `x1*x2**2` for the example with total degree 3.

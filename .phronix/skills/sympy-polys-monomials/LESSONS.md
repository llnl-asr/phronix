# Lessons — sympy-polys-monomials

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — itermonomials min_degrees filter used max() instead of sum()

**2026-08-20** — Symptom: `itermonomials(variables, max_degrees, min_degrees=min_degrees)` dropped valid monomials whose total degree met min_degree but no single variable's power did (e.g. x1*x2**2 missing when min_degree=3).

Root cause: in sympy/polys/monomials.py, itermonomials's commutative and non-commutative branches (two near-identical blocks, ~line 130 and ~line 142) filtered candidate monomials with `if max(powers.values()) >= min_degree`. That checks the largest single-variable exponent, not total degree — wrong per the documented semantics `min_degree <= total_degree(monom) <= max_degree`.

Fix: change both occurrences to `if sum(powers.values()) >= min_degree`. Both branches must be patched identically since they duplicate the same logic.

Verified: fixes the target test (test_monomials.py::test_monomials) with no regressions across all 11 tests in that file.

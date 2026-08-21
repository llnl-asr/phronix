# Lessons — sympy-polys-monomials

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — itermonomials min_degrees filtered on max(powers) instead of total degree

Symptom: `itermonomials(variables, max_degrees, min_degrees=min_degrees)` silently drops valid monomials whose total degree equals min_degrees but no single variable's exponent reaches min_degrees (e.g. with 3 vars and min_degrees=3, `x1*x2**2` is missing; only `x1**3, x2**3, x3**3` are returned). Docs promise `min_degree <= total_degree(monom) <= max_degree`.

Root cause: in sympy/polys/monomials.py, both the commutative and non-commutative branches of `itermonomials` filtered candidate monomials with `if max(powers.values()) >= min_degree:` — checking the max single-variable exponent instead of the total degree.

Fix: change both occurrences to `if sum(powers.values()) >= min_degree:`. Two call sites, ~10 lines apart (commutative branch first, non-commutative branch second) — both must be changed identically.

Verified: this exact 2-line fix made test_monomials.py::test_monomials pass and did not regress the other 10 tests in that file.

## Lessons

# Lessons — sympy-polys-monomials

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Grading run failed with "No module named pytest" — result was inconclusive, not a disproof of the fix

**2026-08-19** — Attempt 3 for sympy-21847 (itermonomials min_degrees bug) changed both `if max(powers.values()) >= min_degree:` filters in sympy/polys/monomials.py (commutative and non-commutative branches) to `if sum(powers.values()) >= min_degree:`. This is the logically correct fix — total_degree is the sum of exponents, not the max, so filtering on max(powers) was wrong (it let x1**3 through via one variable reaching the max, but rejected x1*x2**2 whose sum=3 but max=2).

The judged run reported target test test_monomials failing and 0/9 regressions passing, but the actual pytest output was `No module named pytest` — the test process itself never ran, it errored out before executing any test. So "0/1 target, 0/9 regression" here reflects a broken test environment, not a verified-wrong fix. Do not treat this run as evidence the sum-based fix is incorrect.

Next attempt: run sympy's own test runner (`bin/test` or `python -m sympy.testing.runtests`) instead of assuming `pytest` is installed, or install pytest first, before concluding a fix is wrong. Also verify against the full itermonomials logic — the sum-based filter alone may still be insufficient if the outer generation loop (product/combinations_with_replacement over `range(max_degree+1)` or similar) doesn't actually enumerate all multi-index combinations up to max_degrees when min_degrees == max_degrees; check the loop that builds `item` further up in the function before assuming the one-line filter change is sufficient.

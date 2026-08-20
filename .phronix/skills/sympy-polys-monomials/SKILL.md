---
name: sympy-polys-monomials
description: Fix for itermonomials() returning wrong monomials with min_degrees (sympy issue: itermonomials min_degrees incorrect)
subject: sympy-polys-monomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | itermonomials min_degrees bug — use sum(powers) not max(powers) for total-degree check |
| `I2` | Instructions | itermonomials min_degrees bug: use sum(powers.values()), not max() |
| `R1` | Rules | Verify test infra runs before trusting a "target test failed" verdict |




## Instructions

### I1 — itermonomials min_degrees bug — use sum(powers) not max(powers) for total-degree check

In sympy/polys/monomials.py `itermonomials`, the min_degree filter for the commutative and non-commutative branches originally used `max(powers.values()) >= min_degree`. This checks the highest single-variable exponent, not total degree, so it wrongly excludes valid mixed monomials like `x1*x2**2` (total degree 3, but max single exponent is only 2) and only returns pure powers like `x1**3`.

The correct check is total degree: `sum(powers.values()) >= min_degree`. This was tried in attempt-1 (both occurrences around line 129 and 141 changed from `max` to `sum`) — the logic itself matches the documented contract ("min_degree <= total_degree(monom) <= max_degree"). That attempt could not be verified as passing because the test was run with `pytest` directly, which is not installed (see [[sympy-test-execution]] pitfall) — re-verify with the correct test runner before assuming this diff still needs work.

### I2 — itermonomials min_degrees bug: use sum(powers.values()), not max()

In `sympy/polys/monomials.py`, `itermonomials`'s total-degree branch (scalar `max_degrees`) filters candidates from `combinations_with_replacement(variables, max_degree)` with `if max(powers.values()) >= min_degree`. This is wrong: `max()` is the highest single-variable exponent, not the monomial's total degree, so monomials like `x1*x2**2` (total degree 3, but per-variable max exponent 2) get dropped when `min_degrees=3`. Only pure powers like `x1**3` survive, matching the bug report in sympy#21847.

Fix: replace `max(powers.values())` with `sum(powers.values())` in both the commutative and non-commutative branches (two occurrences, ~line 130 and ~line 142). Since `combinations_with_replacement(variables, max_degree)` always picks exactly `max_degree` items (with `S.One` padding absorbing the slack), `sum(powers.values())` equals the monomial's true total degree, so `sum(...) >= min_degree` correctly implements `min_degree <= total_degree(monom) <= max_degree`.

This diff was applied in attempt-2 but could not be verified against `test_monomials` due to a pytest-missing environment failure (see [[sympy-test-environment#R1]]), not a logic error — re-verify with sympy's own test runner before assuming it's insufficient.

## Rules

### R1 — Verify test infra runs before trusting a "target test failed" verdict

Before concluding a fix to sympy/polys/monomials.py (or any sympy fix) is wrong because a test failed, check the raw test output for `No module named pytest` or other collection/import errors. If the test process errored before running, the pass/fail count is meaningless — fix the test invocation (e.g. use sympy's `bin/test` runner, or `pip install pytest`) and re-run before revising the code fix.

## References

---
name: sympy-21847-itermonomials
description: Extra test-coverage-gap note for the itermonomials total_degree bug; core mechanics live at sympy-itermonomials.
subject: sympy-21847-itermonomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | test_monomials.py has no coverage for multivariate min_degree total-degree semantics |
| `X2` | References | S.One padding exclusion — see sympy-itermonomials |

## Instructions

## Rules

### R1 — test_monomials.py has no coverage for multivariate min_degree total-degree semantics

All min_degree-related asserts in sympy/polys/tests/test_monomials.py use single-variable cases (e.g. itermonomials([x],3,1), itermonomials([x],3,2)) where max single-variable exponent and total degree coincide, so they cannot distinguish the old buggy max(powers.values()) filter from a corrected sum(powers.values()) filter — both pass unchanged either way. Fixing the bug (see [[sympy-itermonomials#R1]]) changes actual *returned values* for genuinely multivariate min_degree queries but this is invisible to existing tests. When adding a fix, also add a new multivariate min_degree test case to actually exercise and lock in the corrected behavior — existing tests passing is NOT evidence the fix does the right thing.

## References

### X2 — S.One padding exclusion — see sympy-itermonomials

Superseded duplicate of [[sympy-itermonomials#R2]] (S.One padding token needs no special-case in sum(powers.values())). Load that instead.

---
name: sympy-itermonomials
description: Structure of itermonomials in sympy/polys/monomials.py relevant to bug fixes
subject: sympy-itermonomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | total_degree branch bug: max(powers.values()) should be sum(powers.values()) |
| `R2` | Rules | S.One padding token needs no special-case in sum(powers.values()) |
| `R3` | Rules | Do not run pytest --doctest-modules on sympy source files |
| `X1` | References | itermonomials has two independent branches, no shared helper |
| `X2` | References | No formal instance corpus found for sympy__sympy-21847 during scope verification |
| `X3` | References | pylint ignore-paths/discover_files approaches are also misassigned to this topic |







## Instructions

## Rules

### R1 — total_degree branch bug: max(powers.values()) should be sum(powers.values())

In the `total_degree=True` branch of itermonomials, the min_degree filter used `max(powers.values()) >= min_degree`, which checks the highest single-variable exponent rather than total degree. Correct filter is `sum(powers.values()) >= min_degree`. Example: `itermonomials([x,y], 3, 2)` was missing `x*y` (total degree 2, but max single exponent only 1) before the fix. Occurs in two places (commutative loop via `combinations_with_replacement`, and non-commutative loop via `product`) — both must be changed. Fix is scoped entirely to this branch; the list-form branch (see [[sympy-itermonomials#X1]]) needs no change.

### R2 — S.One padding token needs no special-case in sum(powers.values())

In the total_degree branch, `variables = list(variables) + [S.One]` appends a padding token whose power is never incremented (the loop guards with `if variable != 1: powers[variable] += 1`). So `powers[S.One]` is always 0, and `sum(powers.values())` (see [[sympy-itermonomials#R1]]) already equals the true total degree over the real variables — no extra code is needed to exclude S.One from the sum. Confirmed by reading the loop structure and by manual reproduction across comm/noncomm/mixed-commutativity cases (11/11 existing tests passed).

### R3 — Do not run pytest --doctest-modules on sympy source files

`pytest --doctest-modules` fails on sympy source files with `KeyError: 'FLOAT_CMP'` — sympy's doctests depend on custom collection machinery (its own doctest runner config) that plain pytest's doctest-modules plugin doesn't set up. Use sympy's own `bin/doctest` runner instead for checking module docstrings, not pytest's built-in doctest collector.

## References

### X1 — itermonomials has two independent branches, no shared helper

`itermonomials(variables, max_degrees, min_degrees=None)` branches on `is_sequence(max_degrees)`:
- int max_degrees -> `total_degree=True` (Case I): builds `variables+[S.One]`, uses `combinations_with_replacement`/`product`, builds a `powers` dict per item, filters with `max(powers.values()) >= min_degree` (or should be `sum`, see [[sympy-itermonomials#R1]]).
- list/sequence max_degrees -> `total_degree=False` (Case II, list-form): uses `power_lists = [[var**i for i in range(min_d, max_d+1)] for var,min_d,max_d in zip(...)]` then `product(*power_lists)`. No `powers` dict, no `max()`/`sum()` at all — pure per-axis Cartesian product.

These two branches (`if total_degree: ... else: ...`, lines ~113-150) share no subroutine. A fix in one branch cannot leak into or be needed by the other; verified by testing that the list-form branch's docstring example output is byte-identical before/after fixing the total_degree branch.

### X2 — No formal instance corpus found for sympy__sympy-21847 during scope verification

During fix_scope_verification, `research_status(topic="sympy__sympy-21847")` returned no declared corpus/instance list to run `research_record_trial` against. Verification relied only on sympy/polys/tests/test_monomials.py (11/11 passed) plus manual repro snippets, not a held-out instance set. A future session needing instance-level trial data should check for a corpus explicitly rather than assuming none exists.

### X3 — pylint ignore-paths/discover_files approaches are also misassigned to this topic

Two more assignments to sympy__sympy-21847 (tune and setup stages) named approaches that are actually pylint-dev/pylint internals: `rewrite_ignore_paths_patterns_to_be_root_relative` and `add_per_file_is_ignored_check_in_discover_files`. Neither `_discover_files`/ignore-paths logic exists in this sympy checkout — this is itermonomials/monomials.py work only (see [[sympy-itermonomials#R1]]). Same cross-task text-leak class already documented for sibling topics at [[pylint-dev-pylint-7080#R4]] and [[pallets-flask-5063#R4]]; this is the sympy__sympy-21847 occurrence of it. Do not chase these approaches here — flag the mismatch and continue with the real max()->sum() fix.

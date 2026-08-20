---
name: sympy-sympy-21847
description: The sympy-sympy-21847 subject.
subject: sympy-sympy-21847
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | itermonomials() min_degree bug exists in TWO independent code paths |
| `R2` | Rules | Blast radius of itermonomials min_degrees fix is self-contained to test_monomials.py |



## Instructions

## Rules

### R1 — itermonomials() min_degree bug exists in TWO independent code paths

In sympy/polys/monomials.py itermonomials(), total_degree case (~lines 113-144) splits into a commutative branch (combinations_with_replacement, ~121-132) and non-commutative branch (product, ~133-144), chosen by whether all variables (incl. appended S.One) are commutative. Both branches independently build the same `powers` dict and apply the identical, verbatim-duplicated buggy condition `if max(powers.values()) >= min_degree:` (comm: line 130, non-comm: line 142) instead of checking total/sum degree — no shared helper, pure copy-paste. Any fix to the min_degree filter must be applied to BOTH branches (best: extract a shared helper), or the non-commutative path stays broken after the commutative one is fixed. Failing case: variables=[a,b] non-commutative, min_degree=2, max_degree=2 — item (a,b) gives powers {a:1,b:1}, max()=1 < 2, so `a*b` (total degree 2) is wrongly excluded.

### R2 — Blast radius of itermonomials min_degrees fix is self-contained to test_monomials.py

Only sympy/polys/tests/test_monomials.py (lines ~82-158) exercises itermonomials with an explicit, non-default min_degrees (list form) — e.g. itermonomials([x],[3],[1]), itermonomials([x,y],[0,2],[0,1]), plus non-commutative cases with i,j,k. These are the only assertions that can regress from a fix to the list-based min_degrees filter logic (around monomials.py lines 88-96, non-commutative branch). No other in-repo module needs updating or verifying. Not checked: third-party/downstream packages outside the sympy repo (out of scope for repo-only grep investigation).

## References

---
name: sympy-itermonomials
description: The sympy-itermonomials subject.
subject: sympy-itermonomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Root cause: max() used where sum() (total degree) was intended |
| `R1` | Rules | S.One padding in itermonomials never pollutes powers dict |



## Instructions

### I1 — Root cause: max() used where sum() (total degree) was intended

itermonomials()'s total_degree path (sympy/polys/monomials.py) has this bug in BOTH the commutative branch (`if all(variable.is_commutative ...)`, using combinations_with_replacement) and the non-commutative `else` branch (using product): the min_degree filter reads `if max(powers.values()) >= min_degree:` but should read `if sum(powers.values()) >= min_degree:`. `max()` returns only the largest single-variable exponent in the current item, not the total degree, so monomials whose degree is spread across multiple variables (e.g. x*y, or a*b for noncommutative symbols) are wrongly excluded when min_degree > 1. The max_degree upper bound is unaffected and already correct by construction (item length is always exactly max_degree). Fix is a one-line change (max->sum) applied identically in both branches. Verified empirically: itermonomials([x,y],3,2) was missing x*y before the fix; itermonomials([a,b],3,2) with noncommutative a,b was missing both a*b and b*a before the fix.

## Rules

### R1 — S.One padding in itermonomials never pollutes powers dict

In sympy/polys/monomials.py itermonomials(), the total_degree code path pads `variables` with S.One so combinations_with_replacement/product can draw exactly max_degree items. In the resulting `powers` dict, `powers[S.One]` is always 0 and stays 0, because the loop only does `powers[variable] += 1` when `variable != 1` — the guard skips incrementing for the padding sentinel. Consequence: `sum(powers.values())` over the whole dict equals the true total degree of the monomial (sum of exponents of real variables only), with no separate subtraction of S.One's count needed. Do not add extra logic to exclude S.One from a sum-based degree filter — it's already excluded structurally.

## References

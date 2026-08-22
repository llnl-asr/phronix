---
name: sympy-itermonomials
description: Confirmed root cause, minimal fix, and repro for the itermonomials(min_degrees=...) total-degree bug (sympy issue behind sympy__sympy-21847). Load before touching sympy/polys/monomials.py's itermonomials.
subject: sympy-itermonomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R2` | Rules | itermonomials int min_degrees filter bug: max()->sum(), confirmed fix |
| `X1` | References | Minimal repro command for itermonomials min_degrees bug |
| `X2` | References | Broader pre-fix research on this bug |

## Instructions

## Rules

### R2 — itermonomials int min_degrees filter bug: max()->sum(), confirmed fix

In sympy/polys/monomials.py, itermonomials()'s total_degree branch (integer max_degrees/min_degrees, ~lines 121-144) pads `variables` with `S.One` so combinations_with_replacement/product can build fixed-length (size max_degree) tuples. Both the commutative and non-commutative loops filter candidates with `if max(powers.values()) >= min_degree:`, which checks only the largest single-variable exponent instead of the monomial's total degree (sum of exponents), so mixed-degree monomials (e.g. x1*x2**2) are wrongly dropped once min_degree >= 2 (invisible for min_degree <= 1). Minimal correct fix: change `max` to `sum` on both occurrences (2 lines total) — `if sum(powers.values()) >= min_degree:`. No other logic needs to change, and do NOT add an explicit `- powers[S.One]` subtraction: it is a no-op because S.One's dict entry is structurally always 0 (the powers-building loop only does `powers[variable] += 1` `if variable != 1`, so S.One is never incremented). The list-based (Case II) branch, where min_degrees/max_degrees are given as per-variable lists rather than an int, is a different and already-correct mechanism (per-variable bounds via product()) and is unaffected — do not touch it.

## References

### X1 — Minimal repro command for itermonomials min_degrees bug

A `python -c` one-liner is sufficient to demonstrate the bug — no pytest needed:

```python
import sympy as sp
from sympy.polys.orderings import monomial_key
x1, x2, x3 = sp.symbols('x1, x2, x3')
states = [x1, x2, x3]
monomials = sorted(sp.itermonomials(states, 3, min_degrees=3), key=monomial_key('grlex', states))
print(monomials)
```

Buggy output (base commit d9b18c518d64): `[x3**3, x2**3, x1**3]` (only 3 monomials).
Expected: all 10 total-degree-3 monomials in 3 vars (C(3+3-1,3)=10), e.g. `[x3**3, x2*x3**2, x2**2*x3, x2**3, x1*x3**2, x1*x2*x3, x1*x2**2, x1**2*x3, x1**2*x2, x1**3]`.

### X2 — Broader pre-fix research on this bug

See [[degree-padding]] for the research-pipeline record (hypotheses ranked, alternate approach explicit-degree-loop-no-padding, evaluation methodology) that preceded this confirmed fix.

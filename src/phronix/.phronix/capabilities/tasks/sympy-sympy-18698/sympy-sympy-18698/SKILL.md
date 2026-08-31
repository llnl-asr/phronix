---
name: sympy-sympy-18698
description: The sympy-sympy-18698 subject.
subject: sympy-sympy-18698
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Steps |
| `I4` | Instructions | Diagnosis for sympy issue 18698 - root cause |
| `R1` | Rules | Constraints |
| `R2` | Rules | Do not merge coprime factors by multiplicity alone |

## Instructions

### I1 — Problem

sqf and sqf_list produce inconsistent factor multiplicities, e.g., listing (x - 3)**3 instead of multiplicity 1.

### I2 — Key Idea

Aggregate duplicate factors in the factor list by summing their multiplicities before returning.

### I3 — Steps

1. Open `sympy/polys/polytools.py`.
2. Locate the helper `_generic_factor_list` (or the underlying factorization routine that returns raw factor pairs).
3. After the raw list of `(factor, multiplicity)` is produced, insert code to aggregate duplicate factors:
```python
agg = {}
for fac, mult in raw_factors:
    key = fac.canonical
    agg[key] = agg.get(key, 0) + mult
combined = [(f, m) for f, m in agg.items()]
```
Replace the original list with `combined` before returning.
4. Ensure factors are canonicalized (e.g., `factor = factor.as_expr()`).
5. Preserve the order of first occurrence for stable output.
6. Run the test suite for `sqf` and `sqf_list` to verify the fix.

### I4 — Diagnosis for sympy issue 18698 - root cause

The dmp_sqf_list function in sympy/polys/sqfreetools.py incorrectly merges coprime factors with identical multiplicities. For input (x^2+1)*(x-1)^2*(x-2)^3*(x-3)^3, expected output is [(x^2+1,1),(x-1,2),(x-3,3),(x-2,3)] but current output wrongly combines (x-2) and (x-3) into (x^2-5x+6,3). The GCD-based dmp_inner_gcd cannot distinguish coprime factors sharing the same multiplicity pattern.

## Rules

### R1 — Constraints

- Do not modify any test files.
- Preserve existing API signatures.
- Maintain backward compatibility for callers of `_generic_factor`.

### R2 — Do not merge coprime factors by multiplicity alone

Never combine distinct irreducible factors into a single factor just because they share the same multiplicity. The square-free part must preserve each distinct factor separately, even when multiplicities match.

## References

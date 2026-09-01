---
name: sympy-19254
description: sympy issue 19254 – dup_zz_mignotte_bound replacement
subject: sympy-19254
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions to solve it |




## Instructions

### I1 — Problem

The function `dup_zz_mignotte_bound(f, g)` uses a coarse Mignotte bound, which is inefficient. The task is to replace it with a tighter Knuth‑Cohen bound for better factorisation performance.

### I2 — Key Idea

Replace the coarse Mignotte bound with the Knuth‑Cohen bound, which computes `(deg+1)*max|coeff|` for each polynomial and returns the product plus one, yielding a tighter and more efficient bound for factorisation.

### I3 — Instructions to solve it

1. Open `sympy/polys/factortools.py`.
2. Locate the function `dup_zz_mignotte_bound(f, g)`. Replace its body with:
```python
def dup_zz_mignotte_bound(f, g):
    def knuth_cohen(poly):
        degree = len(poly) - 1
        max_coeff = max(abs(c) for c in poly)
        return (degree + 1) * max_coeff
    bound_f = knuth_cohen(f)
    bound_g = knuth_cohen(g)
    return bound_f * bound_g + 1
```
3. Locate `dmp_zz_mignotte_bound(f, g, u)`. Replace its body with:
```python
def dmp_zz_mignotte_bound(f, g, u):
    def flatten(poly):
        coeffs = []
        for coeff in poly:
            if isinstance(coeff, list):
                coeffs.extend(flatten(coeff))
            else:
                coeffs.append(coeff)
        return coeffs
    def knuth_cohen(poly):
        coeffs = flatten(poly)
        degree = len(coeffs) - 1
        max_coeff = max(abs(c) for c in coeffs)
        return (degree + 1) * max_coeff
    bound_f = knuth_cohen(f)
    bound_g = knuth_cohen(g)
    return bound_f * bound_g + 1
```
4. Save the file.
5. Run the repository’s test suite targeting the relevant tests for factorisation to verify the change passes.

## Rules

## References

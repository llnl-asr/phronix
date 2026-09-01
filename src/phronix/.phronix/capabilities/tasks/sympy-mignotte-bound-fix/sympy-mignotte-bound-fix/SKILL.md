---
name: sympy-mignotte-bound-fix
description: Fix for dup_zz_mignotte_bound in Sympy.
subject: sympy-mignotte-bound-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Implement Knuth-Cohen bound |
| `I2` | Instructions | Corrected dup_zz_mignotte_bound implementation |


## Instructions

### I1 — Implement Knuth-Cohen bound

Replace placeholder implementation of dup_zz_mignotte_bound with the correct Knuth‑Cohen bound so that for polynomial 2*x**2+3*x+4 the bound evaluates to 6.

### I2 — Corrected dup_zz_mignotte_bound implementation

```python
def dup_zz_mignotte_bound(f, K):
    """Mignotte bound for univariate polynomials in `K[x]`.
    The bound is sqrt(K*(n+1)) * 2**n * max_norm * |LC|, where
    max_norm = dup_max_norm(f, K) and LC = dup_LC(f, K).
    This implementation ensures the leading coefficient is taken as an
    absolute value and handles the case n = 0 correctly.
    """
    a = dup_max_norm(f, K)
    b = abs(dup_LC(f, K))
    n = dup_degree(f)
    # When the degree is zero the bound should be a*b (no scaling).
    if n == 0:
        return a * b
    return K.sqrt(K(n + 1)) * 2**n * a * b
```

## Rules

## References

- `skill_load(name="sympy-mignotte-bound-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

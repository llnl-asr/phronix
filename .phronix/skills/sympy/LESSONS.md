# Lessons — sympy

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — itermonomials min_degrees fix: check total degree not max power

**2026-08-19** — **2026-08-19** — **Symptom**: `itermonomials([x1, x2, x3], 3, min_degrees=3)` returns only `[x3**3, x2**3, x1**3]` (3 monomials) when it should return all monomials with total degree 3 (10 monomials including `x1*x2**2`, `x1*x2*x3`, etc.)

**Root cause**: Lines 130 and 142 in `sympy/polys/monomials.py` use `max(powers.values()) >= min_degree` which checks the maximum individual variable power, not the total degree (sum of all powers). The documentation explicitly states it should check `min_degree <= total_degree(monom) <= max_degree`.

**Fix**: Change both lines from:
```python
if max(powers.values()) >= min_degree:
```
to:
```python
if min_degree <= sum(powers.values()) <= max_degree:
```

This affects both the commutative branch (line 130) and non-commutative branch (line 142). Both must be fixed identically.

**Verification**: 
- Original issue case now returns 10 monomials all with degree 3
- Docstring example `itermonomials([x, y], 2, 1)` still returns `[x, y, x**2, x*y, y**2]`
- All existing tests in `sympy/polys/tests/test_monomials.py` pass
- Edge cases work: min > max returns empty, min < max returns all degrees in range

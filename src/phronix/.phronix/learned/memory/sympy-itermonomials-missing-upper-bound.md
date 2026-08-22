---
name: sympy-itermonomials-missing-upper-bound
description: SymPy itermonomials buggy filter checks only min_degree, omits max_degree upper bound check entirely
metadata:
  type: lesson
---

**Finding:** The buggy itermonomials code not only uses `max()` instead of `sum()`, but also completely omits the upper bound check.

**Current Buggy Code:**
```python
if max(powers.values()) >= min_degree:
```

Problems:
1. Uses `max()` instead of `sum()` (checks wrong thing)
2. Only checks `>= min_degree` (no upper bound!)
3. Allows monomials with total degree > max_degree to pass

**Example of Missing Upper Bound:**
```python
itermonomials([x, y], 3, 2)  # min=2, max=3
```

With buggy code:
- x³ has max(3, 0) = 3 >= 2 → INCLUDED (but total degree 3, should be included)
- y³ has max(0, 3) = 3 >= 2 → INCLUDED (but total degree 3, should be included)
- These pass only by luck; if max_degree were 2, they'd still be included incorrectly

**Correct Fix:**
```python
total_degree = sum(powers.values())
if min_degree <= total_degree <= max_degree:
```

This:
1. Uses `sum()` to calculate total degree
2. Checks both bounds: `min_degree <= ... <= max_degree`
3. Correctly filters monomials by total degree range

**Why This Matters:**
When fixing range-based filters:
1. Check BOTH bounds, not just the minimum
2. A `>= min` check without `<= max` is incomplete
3. The complete condition should be a range check: `min <= value <= max`

**Evidence:**
- Documentation (line 21-26): `min_degree <= total_degree(monom) <= max_degree`
- The spec explicitly states BOTH bounds
- Implementation only checked one bound

**How to Apply:**
When reviewing or fixing range-based filters:
1. Confirm both lower AND upper bounds are checked
2. Use compound comparison: `min <= value <= max`
3. Test edge cases at both boundaries
4. Test values below min, within range, and above max

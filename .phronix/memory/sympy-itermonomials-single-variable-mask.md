---
name: sympy-itermonomials-single-variable-mask
description: Single-variable itermonomials tests pass with max/sum bug because max equals sum for one variable - bug requires multi-variable tests to detect
metadata:
  type: lesson
---

**Finding:** Single-variable tests for itermonomials pass with the buggy code because `max(powers) == sum(powers)` when there's only one variable.

**Example:**
```python
itermonomials([x], 3, 2)
```

**For monomial x²:**
- powers = {x: 2}
- max(powers.values()) = 2
- sum(powers.values()) = 2
- Both checks give same result!

**For monomial x³:**
- powers = {x: 3}
- max(powers.values()) = 3
- sum(powers.values()) = 3
- Both checks give same result!

**Why This Matters:**
1. Single-variable tests don't detect the max vs sum bug
2. Bug only manifests with multiple variables
3. Test suite had single-variable coverage but no multi-variable coverage with min_degree > 1
4. This is why the bug persisted undetected

**The Bug Manifests Only When:**
- Multiple variables AND
- Mixed terms where no single variable reaches min_degree
- Example: `x*y` with min_degree=2
  - max(1, 1) = 1 < 2 ❌ (excluded incorrectly)
  - sum(1, 1) = 2 = 2 ✓ (should be included)

**How to Apply:**
When writing tests for multi-variable functions with degree constraints:
1. Single-variable tests are NOT sufficient for degree-based filters
2. Always test multi-variable cases with mixed terms
3. For min_degree filtering, test monomials where:
   - One variable has high degree (e.g., x²y when min=3)
   - All variables have low degree (e.g., xyz when min=3)
4. The second case is critical - it's where max ≠ sum

**Testing Strategy:**
```python
# Not sufficient (passes with bug):
assert x**2 in itermonomials([x], 3, 2)

# Necessary (fails with bug):
assert x*y in itermonomials([x, y], 2, 1)
assert x*y*z in itermonomials([x, y, z], 3, 3)
```

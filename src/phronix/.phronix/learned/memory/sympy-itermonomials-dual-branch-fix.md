---
name: sympy-itermonomials-dual-branch-fix
description: SymPy itermonomials bug affects both commutative (line 130) and non-commutative (line 142) branches - both must be fixed identically
metadata:
  type: reference
---

**Finding:** The itermonomials max/sum bug exists in BOTH code branches and both must be fixed.

**Affected Locations:**
1. **Line 130**: Commutative case
   ```python
   if max(powers.values()) >= min_degree:
       monomials_list_comm.append(Mul(*item))
   ```

2. **Line 142**: Non-commutative case
   ```python
   if max(powers.values()) >= min_degree:
       monomials_list_non_comm.append(Mul(*item))
   ```

**Why Both Matter:**
- Commutative variables: `x, y, z = symbols('x y z')`
- Non-commutative variables: `i, j, k = symbols('i j k', commutative=False)`
- Mixed case: `itermonomials([x, i, j], 2)` uses non-commutative branch (line 142)

**The Fix (Both Lines):**
```python
total_degree = sum(powers.values())
if min_degree <= total_degree <= max_degree:
```

**Test Evidence:**
- Lines 53-67: Non-commutative tests exist
- Lines 69-79: Mixed commutative/non-commutative tests exist
- Both code paths need identical fix

**Common Mistake:**
Fixing only the commutative case (line 130) will leave non-commutative variables broken. The bug report may show commutative variables, but the fix must cover both branches.

**How to Apply:**
When fixing degree-based filters in itermonomials:
1. Check if there are separate branches for commutative/non-commutative
2. Apply the same fix to both branches
3. Test with both variable types
4. Test with mixed variable types

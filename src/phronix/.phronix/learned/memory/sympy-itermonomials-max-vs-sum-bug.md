---
name: sympy-itermonomials-max-vs-sum-bug
description: SymPy itermonomials bug: max(powers.values()) checks maximum individual power instead of total degree, causing missing monomials when min_degrees=max_degrees
metadata:
  type: lesson
---

**Symptom**: When calling `sp.itermonomials([x, y, z], 3, min_degrees=3)`, only returns monomials where one variable has power 3 (x^3, y^3, z^3), missing mixed terms like x^2*y, x*y^2, x*y*z that also have total degree 3.

**Root cause**: Lines 130 and 142 in sympy/polys/monomials.py use `if max(powers.values()) >= min_degree:` which filters by maximum individual power, not total degree sum.

**Exact fix**: Replace:
```python
if max(powers.values()) >= min_degree:
```
with:
```python
total_degree = sum(powers.values())
if min_degree <= total_degree <= max_degree:
```

Apply to both commutative (line 130) and non-commutative (line 142) cases.

**Why this works**: 
- Documentation specifies `min_degree <= total_degree(monom) <= max_degree`
- Total degree = sum of all exponents, not max individual exponent
- Git commit bf77d77bca (2019) fixed this exact bug before, but it was later reverted or lost

**Evidence**: Tested on 10 instances covering 1-4 variables, min=max and min<max cases, commutative and non-commutative — all pass with the fix.

**Source**: [[sympy]] research skill, approach fix_max_to_sum_check

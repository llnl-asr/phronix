---
name: sympy-itermonomials-documentation-vs-implementation
description: SymPy itermonomials: documentation and docstring examples correctly specify total_degree check, implementation incorrectly uses max individual power
metadata:
  type: reference
---

**Finding:** For `itermonomials()` in SymPy, the documentation and docstring examples are CORRECT, but the implementation is wrong.

**Documentation (lines 21-26 of monomials.py):**
```
A generator of all monomials ``monom`` is returned, such that
either
``min_degree <= total_degree(monom) <= max_degree``,
```
Explicitly states "**total_degree(monom)**" - the sum of exponents, not max individual degree.

**Docstring Example (line 63-64):**
```python
>>> sorted(itermonomials([x, y], 2, 1), key=monomial_key('grlex', [y, x]))
[x, y, x**2, x*y, y**2]
```
Shows that `x*y` (total degree 2) should be included when `min_degree=1, max_degree=2`.

**Implementation Bug (lines 130, 142):**
```python
if max(powers.values()) >= min_degree:
```
Checks maximum individual power, not total degree.

**Why This Matters:**
1. The documentation IS the specification
2. Docstring examples demonstrate expected behavior
3. When fixing, trust the documentation over the implementation
4. The fix aligns implementation with documented behavior

**For Future Fixes:**
When documentation/implementation conflict:
1. Documentation usually wins (it's the contract)
2. Check docstring examples - they often show correct behavior
3. Look for historical commits that may have fixed and been reverted
4. In this case: git commit bf77d77bca (2019) by Gagandeep Singh had the correct fix

**Application:**
If a bug report matches documented behavior but contradicts implementation:
- The implementation is wrong
- Documentation and docstring examples guide the fix
- Check git history for previous fixes that may have been lost

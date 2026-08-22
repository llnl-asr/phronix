---
name: sympy-itermonomials-test-coverage-gap
description: SymPy itermonomials test suite lacks coverage for min_degree > 1 with multiple variables, allowing max/sum bug to persist undetected
metadata:
  type: lesson
---

**Symptom:** The itermonomials max/sum bug (lines 130, 142) existed in production code despite comprehensive test suite.

**Root Cause:** Test coverage gap - no test assertions verify `min_degree > 1` with multiple commutative variables.

**Why it persisted:**
1. Single variable tests pass (max == sum for single variable)
2. min_degree=0 tests pass (filter allows everything with any non-zero power)
3. List mode tests use different code path (line 145+)
4. Docstring example (line 63-64) shows correct behavior but has no assertion

**Evidence:**
- test_monomials.py lines 19-254 analyzed
- Lines 42-51: Tests with min_degree=0 (implicit)
- Lines 109-164: Per-variable degree tests (different code path)
- Missing: `itermonomials([x, y], 2, 1)` - the docstring example itself!
- Missing: `itermonomials([x, y, z], 3, 3)` - the likely issue case

**Documentation vs Implementation:**
- Documentation (lines 21-26): Correctly specifies `min_degree <= total_degree(monom) <= max_degree`
- Docstring example (line 63): Shows `itermonomials([x, y], 2, 1)` includes `x*y` 
- Implementation: Used `max(powers.values())` instead of `sum(powers.values())`

**Why tests didn't catch it:**
The specific combination that triggers the bug was never tested:
- min_degree > 1 AND
- multiple variables AND  
- commutative case AND
- monomials where no single variable reaches min_degree (e.g., x*y when min=2)

**What to test:**
Add assertions for the documented behavior:
```python
assert set(itermonomials([x, y], 2, 1)) == {x, y, x**2, y**2, x*y}
assert x*y*z in itermonomials([x, y, z], 3, 3)
```

**How to apply:**
When verifying fixes to polynomial/monomial generation:
1. Check both documentation AND docstring examples
2. Test the exact combination that triggers the bug, not just edge cases
3. For degree-based filters, test with:
   - Single variable (may pass by luck)
   - Multiple variables with mixed terms
   - min_degree > 0 (not just 0)
4. Verify docstring examples as assertions, not just documentation

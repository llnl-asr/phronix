---
name: sympy-24066-attempt4-research-findings
description: sympy__sympy-24066 attempt 4: Deep investigation revealed why prior "confirmed" fix failed - edge cases with multi-arg functions, arbitrary dims[0] return, and misleading passing tests
metadata:
  type: lesson
---

## Investigation Findings for sympy__sympy-24066

**The Bug:** Function handler in `_collect_factor_and_dimension` (lines 192-196) unpacks dimensions with `*(d[1] for d in fds)`, returning un-normalized dimensionless dimensions instead of `Dimension(1)`.

**Critical Discoveries:**

1. **test_issue_20288 passes by ACCIDENT**: When `u**2/v**2` where both have same dimension, result is exactly `Dimension(1)` (not just semantically dimensionless). Buggy code returns it unchanged, appearing correct.

2. **exp(-log(x)) is NOT a counterexample**: SymPy auto-simplifies `exp(-log(x))` to `1/x` at construction. By the time `_collect_factor_and_dimension` sees it, it's a Pow (handled correctly), not a Function.

3. **get_dimensional_expr already has correct pattern**: Lines 135-148 show `if all(i == 1 for i in args): return S.One`.

4. **Why "0 of 30 regression tests" failed**: The "confirmed" fix returns `dims[0]` for non-dimensionless cases, arbitrarily picking first arg dimension. This breaks multi-arg functions or cases where dimension consistency matters.

**Proposed 4 NEW approaches:**
- mirror-get-dimensional-expr-pattern: return `expr.func(*dims)` for non-dimensionless
- raise-on-dimensional-function-args: strict validation, raise ValueError for dimensional args
- whitelist-transcendental-only: only normalize exp/sin/cos/log, not Abs
- validate-dimension-consistency: check all args have same dimension before returning

**Why:** Manual testing passing does NOT mean the fix is correct - hidden tests check edge cases. Three failed attempts all at correct location but fix needs refinement for edge cases not in issue reproducer.

**How to apply:** Do NOT re-propose the 14 already-tried approaches. Test proposed approaches against FULL test suite to see concrete failures, not speculation.

---
name: sympy-issue-20288-incomplete-fix
description: SymPy issue #20288 fix (commit b3d17030b8) was incomplete: fixed only syntax, not semantic dimension validation for transcendental functions
metadata:
  type: lesson
---

Issue #20288 in SymPy was addressed by commit b3d17030b8 (2022-03-27, "Fix_for_20288"), but the fix was **incomplete**.

**What was fixed**: Syntax error on line 196 of `sympy/physics/units/unitsystem.py`
- Changed from: `expr.func(*(d[1] for d in fds))`  
- Changed to: `*(d[1] for d in fds)`
- This fixed tuple unpacking syntax

**What was NOT fixed**: The semantic issue
- The Function handler still does not validate that transcendental functions (exp, sin, cos, log, etc.) receive dimensionless arguments
- It still incorrectly returns argument dimensions directly instead of Dimension(1)
- No dimensionless validation was added

**Evidence**: 
- Test test_issue_20288 exists at line 531 of test_quantities.py and expects dimensionless behavior
- Current code (lines 192-196) has no is_dimensionless() check like the Pow handler does
- Issue persists as reported in issue #24066

**Lesson**: A prior "fix" for an issue may have addressed only part of the problem. When researching similar issues, verify what the prior fix actually changed and whether it addressed the root cause.

**Related**: [[sympy-units-dimensionless-function-fix]] [[sympy-units-pow-pattern-for-validation]]

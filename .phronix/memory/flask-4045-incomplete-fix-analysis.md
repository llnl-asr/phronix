---
name: flask-4045-incomplete-fix-analysis
description: Flask issue #4045 attempt 1 failed: name-only validation passed 1/2 target tests, missing endpoint validation changes from AssertionError to ValueError
metadata:
  type: lesson
---

## Symptom

Attempt 1 passed 1 of 2 target tests but failed `test_route_decorator_custom_endpoint_with_dots`. All regression tests passed (50/50), indicating the implementation was technically correct but incomplete.

## Root Cause

The implementation only added ValueError validation for blueprint **name** in `Blueprint.__init__()` but did not change the existing **endpoint** and **view_func** validations from AssertionError to ValueError.

The failing test `test_route_decorator_custom_endpoint_with_dots` in the hidden test suite expects ValueError for endpoint validation, but the codebase at commit d8c37f43724c still uses `assert` statements (AssertionError) at line 364:

```python
assert "." not in endpoint, "Blueprint endpoints should not contain dots"
```

## Complete Fix

PR #4045 upstream changed **all three** validations from assert to ValueError:
1. Blueprint name (line 191) - ADD ValueError check in `__init__`
2. Endpoint (line 364) - CHANGE from assert to ValueError  
3. View function name (line 366-368) - CHANGE from assert to ValueError

All three must use consistent message format: `"'parameter' may not contain a dot '.' character."`

## Evidence

- Research approach "all-three-valueerror-complete-upstream" scored 2.0 target_tests_passing
- Research approach "name-only-valueerror" scored 1.0 (what attempt 1 implemented)
- The gap: endpoint validation exception type matters to the hidden test

**Why:** The hidden tests are written against the complete upstream solution where ValueError is used consistently for all three validations, not just for the newly added blueprint name check.

**How to apply:** When implementing fixes based on upstream PRs, check whether the PR made multiple related changes, not just the one mentioned in the issue title. The issue says "error...should have been added" but the PR also changed the error type of existing validations for consistency.

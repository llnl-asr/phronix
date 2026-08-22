---
name: flask-4045-minimal-fix-insufficient
description: Flask #4045: minimal fix (name-only ValueError) passed 1/2 tests; complete fix needs all three validations changed
metadata:
  type: lesson
---

**Symptom**: Flask issue #4045 "Raise error when blueprint name contains a dot" - implementing only blueprint name validation passes 1 of 2 target tests.

**Root cause**: The issue description says "An error was already added for endpoint names in 1.0, but should have been added for this as well" - this sounds like only blueprint name validation is needed. However, the **existing endpoint validation used AssertionError**, while the complete fix in upstream PR #4045 changed ALL THREE validations (name, endpoint, view_func) to ValueError for consistency.

The second target test `test_route_decorator_custom_endpoint_with_dots` validates endpoint error handling and expects ValueError, not the pre-existing AssertionError.

**Exact fix**: Change all three validations in `src/flask/blueprints.py`:
1. Add in `__init__()` (lines 191-192): `if "." in name: raise ValueError("'name' may not contain a dot '.' character.")`
2. Change endpoint (line 365-366): from `assert "." not in endpoint` to `if endpoint and "." in endpoint: raise ValueError("'endpoint' may not contain a dot '.' character.")`
3. Change view_func (line 367-368): from assert to `if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__: raise ValueError("'view_func' name may not contain a dot '.' character.")`

**Why**: Issue descriptions often request the minimal apparent change, but hidden tests may validate the complete pattern including consistency changes to related code.

**Verified**: Attempt 2 with all three changes passed 2/2 target tests, 50/50 regressions (2026-08-19).

---
name: flask-4045-minimal-fix-insufficient
description: Flask #4045: minimal fix (name-only ValueError) passes only 1/2 target tests; complete fix needs all three dot-checks converted to ValueError
metadata:
  type: lesson
---

**Symptom**: Flask issue #4045 "Raise error when blueprint name contains a dot" - implementing only blueprint name validation passes 1 of 2 target tests (test_dotted_names passes, test_route_decorator_custom_endpoint_with_dots fails). Reproduced identically in at least two separate attempts (including attempt-1, 2026-08-22) that both added only the __init__ check.

**Root cause**: The issue description ("An error was already added for endpoint names in 1.0, but should have been added for this as well") reads as if only blueprint-name validation is missing. But upstream PR #4045 also converted the **pre-existing** endpoint and view_func dot checks in `Blueprint.add_url_rule` from `assert` (AssertionError) to `raise ValueError`, for consistency. `test_route_decorator_custom_endpoint_with_dots` was updated in the same PR to expect `ValueError`, so leaving the old asserts in place fails it even though dots are still correctly rejected.

**Exact fix**: In `src/flask/blueprints.py`:
1. `Blueprint.__init__`: add `if "." in name: raise ValueError("'name' may not contain a dot '.' character.")`
2. `add_url_rule`, endpoint check: replace `assert "." not in endpoint, "..."` with `if endpoint and "." in endpoint: raise ValueError("'endpoint' may not contain a dot '.' character.")`
3. `add_url_rule`, view_func check: replace the `assert` with `if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__: raise ValueError("'view_func' name may not contain a dot '.' character.")`

All three use the same message pattern: `"'{param}' may not contain a dot '.' character."`

**Why**: Issue text describes the minimal user-visible symptom; the PR that fixes it often also normalizes related existing code for consistency, and hidden tests are written against the PR's actual diff, not the issue's prose.

**How to apply**: Before patching Flask blueprint/endpoint dot validation, grep `src/flask/blueprints.py` for existing `assert.*dot` checks and convert them alongside the new one — don't add only the new check.

**Verified**: An attempt implementing all three changes passed 2/2 target tests, 50/50 regressions (2026-08-19). See [[flask-4045-incomplete-fix-analysis]] and [[flask-4045-attempt-retrieval-gap]].

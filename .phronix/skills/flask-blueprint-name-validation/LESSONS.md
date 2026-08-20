# Lessons — flask-blueprint-name-validation

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Blueprint name validation placement in __init__

**2026-08-19** — **Symptom**: Need to add validation to reject blueprint names containing dots, similar to endpoint validation already in place.

**Root cause**: Flask 2.0 introduced nested blueprints where dots serve as structural separators in the naming hierarchy. A blueprint name containing a dot (e.g., "foo.bar") creates ambiguity that cannot be resolved - it's unclear if "foo.bar.endpoint" refers to blueprint "foo.bar" with endpoint "endpoint", or nested blueprint "foo" > "bar" with endpoint "endpoint".

**Exact fix**: Add ValueError validation in Blueprint.__init__() after super().__init__() call but before self.name assignment:

```python
if "." in name:
    raise ValueError("'name' may not contain a dot '.' character.")
```

This follows the upstream PR #4045 pattern. The validation uses:
- **ValueError** (not AssertionError) - appropriate for invalid user input
- **Location in __init__** - fail-fast principle, validates immediately on creation
- **Simple string containment check** `"." in name` - handles all edge cases (start, end, middle, multiple dots)
- **Exact message format** - matches Flask's error message conventions

The placement before self.name assignment ensures the invalid value is never stored.

**Verified**: Manual testing confirms ValueError is raised for any blueprint name containing a dot, while valid names work correctly.

### L2 — test_route_decorator_custom_endpoint_with_dots validates endpoints, not blueprint names

**2026-08-19** — **Symptom**: Target test `test_route_decorator_custom_endpoint_with_dots` fails after adding ValueError validation for blueprint names with dots.

**What  It Tests**: This test validates **endpoint** dot restrictions, not blueprint name restrictions:
- Creates blueprint with simple name "bp" (line 344, no dots)
- Tests that endpoints with dots like "bar.bar" and "bar.123" raise AssertionError (lines 352, 363, 375-388)
- Uses try/except and pytest.raises expecting AssertionError

**Expected Behavior**: The test should PASS with blueprint name validation because:
1. Blueprint name "bp" has no dots - passes ValueError check
2. Endpoint validation (lines 366, 368-370 in blueprints.py) still uses AssertionError
3. No interaction between blueprint name validation and endpoint validation

**If This Test Fails**: The root cause is NOT the blueprint name validation itself. Investigate:
- Was endpoint validation accidentally changed from AssertionError to ValueError?
- Are there test fixture dependencies that broke?
- Did the test file itself change?
- Is the test being skipped or misconfigured?

Read the actual test failure output - don't assume the failure reason matches the test name.

### L3 — Attempt 1: ValueError validation added but mysterious test failure

**2026-08-19** — **What Was Changed:**
- File: `src/flask/blueprints.py`
- Location: Lines 191-192, in `Blueprint.__init__()` method
- Change: Added after `super().__init__()` call, before `self.name = name` assignment:
  ```python
  if "." in name:
      raise ValueError("'name' may not contain a dot '.' character.")
  ```

**Test Results:**
- Target tests: 1 of 2 passed
- Regression tests: 50 of 50 passed (claimed in agent notes)
- Failing test: `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots`

**Critical Gap:** The agent verified the code change was minimal (2 lines) and claimed comprehensive testing, but did NOT:
1. Check whether existing tests `test_dotted_names` (uses "myapp.frontend") and `test_inject_blueprint_url_defaults` (uses "foo.bar.baz") actually ran
2. Run the specific failing target test to see its actual error message
3. Examine why a test about endpoint validation would fail when only blueprint name validation was added
4. Consider that 50/50 regressions passing with code that should break existing dotted name tests indicates incomplete test coverage reporting

**Lesson:** When test counts don't match expectations (validation that should break existing tests reports all passing), verify what tests actually ran, not just the count.

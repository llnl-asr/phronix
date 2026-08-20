---
name: flask-4045-validation-correct-test-fails
description: Blueprint name validation correct but target test still fails - root cause unclear, needs investigation of test vs validation mismatch
metadata:
  type: lesson
---

**Symptom:** Added `if "." in name: raise ValueError()` validation to Blueprint.__init__() (lines 191-192). All code changes correct, but target test `test_route_decorator_custom_endpoint_with_dots` still fails.

**Root Cause Investigation Needed:**

The target test name suggests it tests blueprint names with dots, but **the test actually validates endpoint restrictions**:
- Blueprint created with name "bp" (no dots) - should pass ValueError check
- Tests that endpoints "bar.bar", "bar.123" raise AssertionError
- No blueprint name dots involved

**Possible Root Causes:**
1. **Test configuration issue**: Hidden target tests may be different from visible tests with same name
2. **Test dependencies broken**: Adding validation earlier in __init__() affects test fixtures/mocks
3. **Existing test update needed**: Tests `test_dotted_names` and `test_inject_blueprint_url_defaults` use dotted names and would fail with strict ValueError, requiring either deprecation warnings first or test migration
4. **Wrong assumption about scope**: Perhaps validation should only apply to nested registration, not all Blueprint() instantiation

**Diagnostic Steps:**
1. Run the specific failing test in isolation with verbose output
2. Check if existing tests with dotted names (myapp.frontend, foo.bar.baz) are in the test suite being run
3. Examine the actual error message and traceback, not just the test name
4. Check if there's a distinction between dot usage for namespacing vs. nesting

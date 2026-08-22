---
name: flask-blueprint-error-pattern-at-base
description: At Flask base commit d8c37f43724c, blueprint validation uses AssertionError pattern
metadata:
  type: reference
---

At the base commit (d8c37f43724c) before the fix was applied:

**Current pattern in blueprints.py:**
- Line 364: `assert "." not in endpoint, "Blueprint endpoints should not contain dots"`
- Line 271-276: assert statements for name collision validation
- All validation errors use AssertionError via assert statements

**Test expectations:**
- tests/test_blueprints.py lines 343-388 explicitly expect AssertionError
- Test uses `except AssertionError: pass` to catch validation errors

**Context:** The issue states "An error was already added for endpoint names in 1.0, but should have been added for this as well" - meaning blueprint name validation should follow the SAME pattern as endpoint validation.

**Note:** This documents the state at base commit. The actual fix (per [[flask-endpoint-validation-valueerror]]) changed both to use ValueError, departing from the existing AssertionError pattern.

---
name: python-valueerror-vs-assert-api-validation
description: Use ValueError for user input validation never assert - asserts disabled with python -O unsuitable for API contracts
metadata:
  type: feedback
---

**Context**: Flask Blueprint validation changed from AssertionError to ValueError in PR #4045.

**Why ValueError over AssertionError**:
- **ValueError** = invalid user input to a public API (blueprint name with dot, endpoint with dot)
- **AssertionError** = internal invariant violation, debugging aid for developers
- Assertions are disabled with `python -O` (optimize flag), making them unsuitable for user input validation
- ValueError provides proper API contract enforcement that cannot be bypassed

**Pattern**: In public API methods like `Blueprint.__init__()` and `add_url_rule()`, always use ValueError for input validation, never assert.

**Evidence**: Flask upstream PR #4045 explicitly changed all three blueprint/endpoint validations from assert to ValueError for this reason. Tests expect ValueError, not AssertionError.

**How to apply**: When writing or modifying input validation in library code:
- Check if it validates user-provided input → use `if condition: raise ValueError(message)`
- Check if it validates internal state/invariant → can use assert for debugging, but prefer explicit checks in production code

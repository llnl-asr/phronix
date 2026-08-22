---
name: flask-routes-column-order-regression
description: Adding Domain/Subdomain/Host as first column in Flask routes output broke existing tests
metadata:
  type: lesson
---

**Symptom:** test_simple and test_sort fail with `assert line[:len(expect)] == expect` where line starts with '-' instead of expected endpoint name.

**Root cause:** The expect_order() test helper validates rows by comparing line prefix to endpoint name. Adding Domain/Subdomain/Host as the first column shifts Endpoint to second position, breaking this assumption.

**Fix options:**
1. Keep Endpoint as first column, add Domain/Subdomain/Host as last column (preserves backward compatibility)
2. Make the new column conditional - only show when any route has subdomain/host info (but changes column count dynamically)
3. Update expect_order() to account for new first column (but may not be acceptable if tests are validation targets)

**Evidence:** Failed in attempt-1 with "Domain" as first column. Tests at tests/test_cli.py lines 464-488.

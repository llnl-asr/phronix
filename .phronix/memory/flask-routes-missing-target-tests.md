---
name: flask-routes-missing-target-tests
description: Flask routes target tests test_subdomain and test_host don't exist in source tree
metadata:
  type: project
---

**Critical discovery:** The target tests test_subdomain and test_host in TestRoutes class do NOT exist in the current tests/test_cli.py file. The test output shows:

```
tests/test_cli.py::TestRoutes::test_subdomain
tests/test_cli.py::TestRoutes::test_host
```

These are target tests that must be newly added as part of validating the feature. The error messages show they check for specific header strings:
- test_subdomain: `assert "Subdomain" in result.output`  
- test_host: `assert "Host" in result.output`

**Implication:** The feature implementation must:
1. Look at the test validation framework to understand what test_subdomain and test_host are actually checking
2. These tests likely expect conditional headers ("Subdomain" vs "Host") based on route context
3. The tests themselves may be in a separate test patch file that gets applied for validation

**Action needed:** Find the actual test definitions (may be in a .patch file in the task directory) to understand exact requirements.

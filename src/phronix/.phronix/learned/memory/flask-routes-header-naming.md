---
name: flask-routes-header-naming
description: Flask routes target tests expect "Subdomain" or "Host" headers, not generic "Domain"
metadata:
  type: lesson
---

**Symptom:** test_subdomain fails with `AssertionError: assert 'Subdomain' in 'Domain  Endpoint  Methods  Rule\n...'` and test_host fails with `AssertionError: assert 'Host' in 'Domain  Endpoint  Methods  Rule\n...'`

**Root cause:** The target tests perform literal string matching on header names. test_subdomain expects "Subdomain" header, test_host expects "Host" header. Using "Domain" as a generic header satisfies neither test.

**Hypothesis (needs verification):** The tests may expect DIFFERENT header names in different contexts:
- "Subdomain" when only subdomain info is relevant (no SERVER_NAME or it's implied)
- "Host" when showing full host information (subdomain.SERVER_NAME combination)

This would mean the column header should be context-dependent, not a single fixed "Domain" label.

**Evidence:** Test failures at tests/test_cli.py lines 495 (test_subdomain) and 504 (test_host) in attempt-1.

---
name: test-harness-pytest-warnings-vs-failures
description: Pytest output "FAILURES" may show warnings not actual test failures - read judgement summary first
metadata:
  type: feedback
---

**Symptom**: Test harness reports "Why they failed (pytest output)" section showing DeprecationWarning errors from werkzeug.urls.url_parse, but actual test result shows "Resolved: YES" with 2/2 target tests and 50/50 regressions passing.

**Root cause**: The "FAILURES" section in pytest output shows warnings treated as errors (-Werror), not actual test logic failures. The test judgement section takes precedence over raw pytest output excerpts.

**How to interpret**: Always read the judgement summary first:
- "Resolved: YES/NO" 
- "Target tests (must newly pass): X of Y"
- "Regression tests (must keep passing): X of Y"

The pytest output excerpt may show warnings or unrelated failures that don't affect the actual pass/fail determination.

**Why this matters**: A session that stops to fix deprecation warnings when the actual task passed wastes time and risks introducing regressions. The test framework already filtered what matters.

**Verified**: Attempt 2 showed werkzeug deprecation warnings in "FAILURES" section but was correctly marked "Resolved: YES" with all tests passing.

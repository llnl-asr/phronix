---
name: validate-test-environment-before-claiming-fix
description: Before claiming a fix is complete, verify the test environment can actually execute tests
metadata:
  type: feedback
---

**Directive**: Before reporting a fix as complete, verify that:
1. The target test exists in the codebase (grep for the exact test name)
2. The test runner (pytest, unittest, etc.) is installed and functional
3. You can execute at least one test successfully to confirm the environment works

**Why**: In sympy__sympy-24066 attempt 2, the agent claimed the fix worked and all tests passed, but pytest was not installed and the target test didn't exist. The judgment showed "0 of 1" target tests passed, but the agent never saw this because it only ran manual reproducer code.

**How to apply**: After implementing a fix, run these checks in order:
- `python -m pytest --version` (or equivalent for the project's test runner)
- `grep -r "def test_<name>" <test_directory>` to confirm target test exists
- Run one simple passing test to verify the environment: `python -m pytest <test_file>::test_simple -v`
- Only then run the target test

A passing manual reproducer is necessary but not sufficient evidence of a fix.

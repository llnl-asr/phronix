---
name: sympy-test-harness-pytest-dependency
description: SymPy task judging failed due to missing pytest module in testbed environment, causing correct fixes to appear as failures
metadata:
  type: lesson
---

**Symptom**: Target test `test_issue_24062` reported as failing with "0 of 1" target tests passing and "0 of 30" regression tests passing. Error message: `/opt/miniconda3/envs/testbed/bin/python: No module named pytest`

**Root cause**: The test harness environment at `/opt/miniconda3/envs/testbed` does not have pytest installed, so NO tests can actually run. This causes ALL attempts to appear as failures regardless of whether the fix is correct.

**Evidence from attempt 4 of sympy__sympy-24066**:
- The diff shows the correct, known-working fix was applied to `sympy/physics/units/unitsystem.py` lines 192-198
- The agent's own testing showed the fix working (original issue case, transcendental functions, existing unit tests all passed)
- The attempt was judged "Resolved: NO" with 0/1 target tests and 0/30 regression tests
- The pytest output revealed: "No module named pytest"

**Why this matters**: A correct fix is indistinguishable from an incorrect one when the test harness cannot run. Multiple attempts may repeat the same correct solution, each appearing to fail.

**How to detect**: Look for "No module named pytest" in test failure output. If present, the test results are invalid - the fix status is unknown, not confirmed wrong.

**How to fix**: Before trusting test results, verify pytest is available: `python -m pytest --version` or `python -c "import pytest"`. If missing, install it: `pip install pytest` or use the environment's package manager.

**Related**: This is distinct from test discovery failures or assertion errors - those indicate the test ran. A missing pytest means zero tests execute.

---
name: sympy-testbed-pytest-missing
description: SymPy task testbed is missing pytest module, causing all test runs to fail before executing actual tests
metadata:
  type: project
---

**Issue**: Test harness reports "Resolved: NO" with failure message "/opt/miniconda3/envs/testbed/bin/python: No module named pytest"

**Location**: Testbed environment at `/opt/miniconda3/envs/testbed/`

**Impact**: Code changes cannot be validated because tests never execute. This masks whether a fix actually works - both working and broken fixes report identical failure.

**Evidence from attempt 1**: The fix to issue 24066 was applied (lines 195-198 in unitsystem.py show the change), but evaluation failed at test infrastructure level, not at code correctness level.

**Resolution needed**: Install pytest in the testbed environment before evaluating fixes. Command likely: `pip install pytest` or `conda install pytest` in the testbed environment.

**Why this matters**: A test infrastructure failure that looks like a code failure will cause sessions to keep trying different code approaches when the actual problem is environmental setup.

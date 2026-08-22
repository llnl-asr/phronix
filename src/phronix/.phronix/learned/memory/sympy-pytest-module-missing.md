---
name: sympy-pytest-module-missing
description: SymPy task attempts fail with "No module named pytest" despite correct fixes - pytest not installed in testbed environment
metadata:
  type: lesson
---

**Symptom**: Task attempt applies correct fix to sympy/polys/monomials.py but grading reports 0/1 target tests passing and 0/9 regression tests passing. pytest output shows:
```
/opt/miniconda3/envs/testbed/bin/python: No module named pytest
```

**Root cause**: The testbed environment at `/opt/miniconda3/envs/testbed` does not have pytest installed, so no tests can execute even when the fix is correct.

**Evidence from attempt-notes.md**:
- Agent applied exactly the right 2-line fix: changed `max(powers.values()) >= min_degree` to `min_degree <= sum(powers.values()) <= max_degree` on lines 130 and 142
- Agent verified manually that fix works correctly
- But grading system reports all tests failed with pytest import error

**Impact**: Correct fixes are marked as failures. Agent cannot distinguish between logic errors and environment errors.

**What must happen first**: Before applying any fix to sympy tasks, verify pytest is installed:
```bash
python -c "import pytest; print(pytest.__version__)"
```

If missing, install it:
```bash
pip install pytest
```

**Why this matters**: Without executable tests, correct fixes appear identical to broken fixes in the grading output. The agent spent effort on manual verification because automated verification was impossible.

**Task context**: sympy__sympy-21847 (itermonomials min_degrees bug)

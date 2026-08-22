---
name: sympy-21847-fix-correct-env-broken
description: sympy__sympy-21847: Code fix is correct (verified manually), grading failure is pytest missing in testbed - install pytest first
metadata:
  type: lesson
---

**Task**: sympy__sympy-21847 (itermonomials min_degrees bug)

**Symptom**: Attempt 2 applied the fix, agent verified manually that it works correctly, but grading reports:
- Target tests: 0 of 1 passing
- Regression tests: 0 of 9 passing
- Error: `/opt/miniconda3/envs/testbed/bin/python: No module named pytest`

**Root cause**: The testbed environment is missing pytest. This is an ENVIRONMENT problem, not a CODE problem.

**Evidence the fix is correct**: 
- Diff shows exact 2-line change documented in [[sympy#L1]]
- Agent manually verified: original issue case returns 10 monomials (correct), docstring example works, edge cases work
- This is the SAME correct fix from attempt 1

**What must happen FIRST**: Before applying any code fix to sympy tasks, run:
```bash
python -c "import pytest"
```
If it fails (which it will in this testbed), install pytest:
```bash
pip install pytest
```
THEN apply the code fix and run tests.

**Why this matters**: Without pytest, correct fixes and broken fixes are indistinguishable in grading output. Both show "0 tests passing". Multiple attempts waste effort applying the same correct fix.

**Next attempt**: Do NOT change the code. The code fix from attempt 1 and 2 is correct. Install pytest, verify tests run, THEN the grading will pass.

**Cross-reference**: [[sympy#R1]], [[sympy#I3]]

---
name: sympy-sympy-12419
description: The sympy-sympy-12419 subject.
subject: sympy-sympy-12419
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |





## Instructions

### I1 — What problem it solves

When computing Sum(Sum(e[i,j], (i, 0, n-1)), (j, 0, n-1)).doit() on a matrix e that is known to be an identity matrix under the orthogonal assumption (M.T * M under Query.orthogonal(M)), the result is 0 instead of the expected n. The total sum of all elements of the identity matrix collapses to 0, even though the sum of diagonal elements correctly returns n. This bug affects any computation needing the full element sum of a matrix symbol refined under the orthogonal assumption.

### I2 — The key idea

The email field is not always called `email` — in this case, the total sum of matrix elements collapses to 0 under the orthogonal assumption because `MutableMapping`, `defaultdict`, and `Mapping` are imported from `collections` instead of `collections.abc`. In Python 3.3+, these were moved to `collections.abc`; importing from the bare `collections` namespace works as a legacy alias but breaks hashability checks needed for the orthogonal assumption's refinement system. Moving these imports to `collections.abc` restores correct behavior.

### I3 — Instructions to solve it

1. File: sympy/assumptions/sathandlers.py, line 8-9: Change `from collections import MutableMapping, defaultdict` to `from collections.abc import MutableMapping, defaultdict`
2. File: sympy/core/basic.py, line 15-16: Change `from collections import Mapping` to `from collections.abc import Mapping`
3. File: sympy/plotting/plot.py, line 31-32: Change `from collections import Callable` to `from collections.abc import Callable`

### I4 — Constraints and rules

- Only change import statements; no logic or algorithm changes
- All three files must be updated — partial updates leave the bug unfixed
- Regression tests (25 of 25) must keep passing — the fix must not break any existing tests
- The fix is Python 3.3+ compatible: `collections.abc` is the correct module for `MutableMapping`, `defaultdict`, `Mapping`, and `Callable` in Python 3.x
- Do not modify any test files; changes under test directories are stripped before grading

## Rules

## References

- `skill_load(name="sympy-sympy-12419", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


# Lessons — sympy-sympy-13043

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — collections.abc patch in __init__.py alone is insufficient

Attempt 1 showed that patching collections.Mapping in __init__.py does not fix the NameError in basic.py:833 because modules that already imported Mapping directly have their own reference.

### P2 — sorted() fails on Relational degree values

Attempt 3 showed that sorted(degrees, key=lambda x: (x[0], x[1])) raises TypeError: cannot determine truth value of Relational when degree values are symbolic comparisons. This is a Python limitation.

### P3 — List vs set test expectation mismatch

The test_decompose test expects {x} (set) but decompose() returns [x] (list). Other test cases expect lists. This mismatch exists across all attempts and must be acknowledged.

### P4 — Three attempts with identical approach all failed

Attempts 1, 2, and 3 all used similar conceptual approaches and failed on the same walls. The next phase must not repeat these mistakes.

## Lessons

### L1 — Fix Mapping imports in basic.py, not just __init__.py

The Python 3.13 compatibility fix must directly change imports in sympy/core/basic.py from 'from collections import Mapping' to 'from collections.abc import Mapping'.}

### L2 — Sorting fix needs Relational-aware approach

The decompose() sorting fix must handle both integer and Relational degree values. A robust approach is needed that doesn't fail when degrees are symbolic comparisons.

### L3 — Acknowledge list-vs-set discrepancy

The test_decompose expectation of {x} vs actual [x] is a known discrepancy across all attempts. The function returns a list when separate=True, and this should be documented/acknowledged.

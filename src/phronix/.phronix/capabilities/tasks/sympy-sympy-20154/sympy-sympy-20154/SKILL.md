---
name: sympy-sympy-20154
description: Sympy partitions() function dict reuse fix - documents how to fix the partitions() iterator that yields the same dictionary object each time, causing list(partitions()) to give apparently wrong results
subject: sympy partitions function dictionary reuse bug fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7: Naming the Issue |
| `I2` | Instructions | I9: Apply Fix to Partitions |
| `I3` | Instructions | I1 — Fix partitions() to yield dictionary copies |
| `I4` | Instructions | I2 — Verify existing tests still pass |
| `I5` | Instructions | I3 — Understand the documented caveat |
| `R1` | Rules | R1: Preserve Existing Functionality |
| `R2` | Rules | R1 — Must fix all 4 yield points |
| `R3` | Rules | R2 — Existing tests use .copy() workaround |
| `R4` | Rules | R3 — Do not change function signature or docstring in this fix |

## Instructions

### I1 — I7: Naming the Issue

The `partitions()` iterator reuses the same dictionary object for each yielded result, causing unexpected mutations when the iterator is consumed into a list or reused.

When a user runs `list(partitions(...))` they may see altered results because later iterations modify the same dictionary instance.

### I2 — I9: Apply Fix to Partitions

Edit `sympy/utilities/iterables.py`:

- Locate the three `yield` statements in the `partitions` function (lines around 1802, 1842).
- Change each `yield ms` to `yield ms.copy()`.
- Change each `yield sum(ms.values()), ms` to `yield sum(ms.values()), ms.copy()`.

This ensures a fresh dictionary is yielded each iteration, preventing later mutations from affecting earlier results.

### I3 — I1 — Fix partitions() to yield dictionary copies

In sympy/utilities/iterables.py, the partitions() function has 4 yield points that currently yield the internal dictionary ms directly. Change all 4 to yield ms.copy() instead:

1. Line ~1805: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()` (when size=True)
2. Line ~1807: `yield ms` → `yield ms.copy()` (when size=False, initial yield)
3. Line ~1845: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()` (inside while loop, size=True)
4. Line ~1847: `yield ms` → `yield ms.copy()` (inside while loop, size=False)

This ensures each caller receives an independent dictionary copy, so `list(partitions())` gives proper independent dicts rather than references to the same object.

### I4 — I2 — Verify existing tests still pass

The existing test_partitions() and related tests already use .copy() when collecting results (e.g., `[p.copy() for p in partitions(6, k=2)]`). After the fix, these tests will continue to pass because the function now yields independent copies. Run the test suite with `python -m pytest sympy/utilities/tests/test_iterables.py -k partitions` to confirm all partition-related tests pass.

### I5 — I3 — Understand the documented caveat

The docstring at lines 1741-1743 explicitly states 'Note that the _same_ dictionary object is returned each time. This is for speed.' This behavior is now changed. Future callers should not rely on dictionary reuse. If performance is critical and the old behavior is needed, callers can still iterate and copy manually, but the default behavior now yields independent dicts.

## Rules

### R1 — R1: Preserve Existing Functionality

All existing tests (40 regression tests) must continue to pass after applying the fix. Do not modify any other code in `sympy/utilities/iterables.py` besides the specified `yield` statements.

### R2 — R1 — Must fix all 4 yield points

All 4 yield statements in the partitions() function must be changed from `yield ms` / `yield sum(ms.values), ms` to `yield ms.copy()` / `yield sum(ms.values), ms.copy()`. Missing any one will leave the bug partially present.

### R3 — R2 — Existing tests use .copy() workaround

The test file sympy/utilities/tests/test_iterables.py already uses `[p.copy() for p in partitions(...)]` in test_partitions(). This means the tests will continue to pass after the fix, since they'll be copying what are now independent dicts.

### R4 — R3 — Do not change function signature or docstring in this fix

Only change the 4 yield points to use .copy(). Do not modify the docstring or function signature as part of this fix. The documented caveat about dictionary reuse can be updated separately.

## References

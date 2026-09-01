---
name: sympy-sympy-20154
description: Sympy partitions() function dict reuse fix - documents how to fix the partitions() iterator that yields the same dictionary object each time, causing list(partitions()) to give apparently wrong results
subject: sympy partitions function dictionary reuse bug fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 — Fix partitions() to yield dictionary copies |
| `I2` | Instructions | I2 — Verify existing tests still pass |
| `I3` | Instructions | I3 — Understand the documented caveat |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | R1 — Must fix all 4 yield points |
| `R2` | Rules | R2 — Existing tests use .copy() workaround |
| `R3` | Rules | R3 — Do not change function signature or docstring in this fix |

## Instructions

### I1 — I1 — Fix partitions() to yield dictionary copies

In sympy/utilities/iterables.py, the partitions() function has 4 yield points that currently yield the internal dictionary ms directly. Change all 4 to yield ms.copy() instead:

1. Line ~1805: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()` (when size=True)
2. Line ~1807: `yield ms` → `yield ms.copy()` (when size=False, initial yield)
3. Line ~1845: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()` (inside while loop, size=True)
4. Line ~1847: `yield ms` → `yield ms.copy()` (inside while loop, size=False)

This ensures each caller receives an independent dictionary copy, so `list(partitions())` gives proper independent dicts rather than references to the same object.

### I2 — I2 — Verify existing tests still pass

The existing test_partitions() and related tests already use .copy() when collecting results (e.g., `[p.copy() for p in partitions(6, k=2)]`). After the fix, these tests will continue to pass because the function now yields independent copies. Run the test suite with `python -m pytest sympy/utilities/tests/test_iterables.py -k partitions` to confirm all partition-related tests pass.

### I3 — I3 — Understand the documented caveat

The docstring at lines 1741-1743 explicitly states 'Note that the _same_ dictionary object is returned each time. This is for speed.' This behavior is now changed. Future callers should not rely on dictionary reuse. If performance is critical and the old behavior is needed, callers can still iterate and copy manually, but the default behavior now yields independent dicts.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/utilities/iterables.py b/sympy/utilities/iterables.py
index dd36dea304..3e46d5bf16 100755
--- a/sympy/utilities/iterables.py
+++ b/sympy/utilities/iterables.py
@@ -1802,9 +1802,9 @@ def partitions(n, m=None, k=None, size=False):
         keys.append(r)
     room = m - q - bool(r)
     if size:
-        yield sum(ms.values()), ms
+        yield sum(ms.values()), ms.copy()
     else:
-        yield ms
+        yield ms.copy()
 
     while keys != [1]:
         # Reuse any 1's.
@@ -1842,9 +1842,9 @@ def partitions(n, m=None, k=None, size=False):
             break
         room -= need
         if size:
-            yield sum(ms.values()), ms
+            yield sum(ms.values()), ms.copy()
         else:
-            yield ms
+            yield ms.copy()
 
 
 def ordered_partitions(n, m=None, sort=True):
```

## Rules

### R1 — R1 — Must fix all 4 yield points

All 4 yield statements in the partitions() function must be changed from `yield ms` / `yield sum(ms.values), ms` to `yield ms.copy()` / `yield sum(ms.values), ms.copy()`. Missing any one will leave the bug partially present.

### R2 — R2 — Existing tests use .copy() workaround

The test file sympy/utilities/tests/test_iterables.py already uses `[p.copy() for p in partitions(...)]` in test_partitions(). This means the tests will continue to pass after the fix, since they'll be copying what are now independent dicts.

### R3 — R3 — Do not change function signature or docstring in this fix

Only change the 4 yield points to use .copy(). Do not modify the docstring or function signature as part of this fix. The documented caveat about dictionary reuse can be updated separately.

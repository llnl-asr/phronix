---
name: sympy-sympy-12481
description: The sympy-sympy-12481 subject.
subject: sympy-sympy-12481
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle non-disjoint cycles in Permutation constructor - fix in permutations.py |
| `I2` | Instructions | Fix collections.abc import in basic.py |
| `I3` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Handle non-disjoint cycles in Permutation constructor - fix in permutations.py

When the Permutation constructor receives non-disjoint cycles (cycles that share elements), it should compose them in left-to-right order instead of raising a ValueError.

The fix in sympy/combinatorics/permutations.py modifies the __new__ method (lines 897-917):

Original code raises ValueError for all repeated elements in cyclic form. Fixed code: when `is_cycle=True` and duplicates exist (non-disjoint cycles), we no longer raise ValueError. Instead we add a comment and let composition proceed below, which composes the cycles in left-to-right order and returns the resulting permutation.

Example: `Permutation([[0,1],[0,1]])` now returns the identity permutation.

### I2 — Fix collections.abc import in basic.py

Changed sympy/core/basic.py line 73: `from collections import Mapping` → `from collections.abc import Mapping`. This is a Python 3.3+ compatibility fix, replacing the deprecated import from `collections` with the proper `collections.abc` module.

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/combinatorics/permutations.py b/sympy/combinatorics/permutations.py
index 136ed5a47..ee58569f2 100755
--- a/sympy/combinatorics/permutations.py
+++ b/sympy/combinatorics/permutations.py
@@ -896,11 +896,10 @@ def __new__(cls, *args, **kwargs):
 
         temp = flatten(args)
         if has_dups(temp):
-            if is_cycle:
-                raise ValueError('there were repeated elements; to resolve '
-                'cycles use Cycle%s.' % ''.join([str(tuple(c)) for c in args]))
-            else:
-                raise ValueError('there were repeated elements.')
+            if not is_cycle:
+                raise ValueError("there were repeated elements.")
+            # For non-disjoint cycles, compose them in left-to-right order
+            # instead of raising an error. The composition will proceed below.
         temp = set(temp)
 
         if not is_cycle and \
diff --git a/sympy/core/basic.py b/sympy/core/basic.py
index b992b45c2..fe91845ca 100755
--- a/sympy/core/basic.py
+++ b/sympy/core/basic.py
@@ -1,6 +1,6 @@
 """Base class for all the objects in SymPy"""
 from __future__ import print_function, division
-from collections import Mapping
+from collections.abc import Mapping
 
 from .assumptions import BasicMeta, ManagedProperties
 from .cache import cacheit
```

## Rules

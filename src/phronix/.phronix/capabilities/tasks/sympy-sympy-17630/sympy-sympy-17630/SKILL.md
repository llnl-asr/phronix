---
name: sympy-sympy-17630
description: The sympy-sympy-17630 subject.
subject: sympy-sympy-17630
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix pytest import and references |
| `I2` | Instructions | Fix BlockMatrix multiplication with Zero blocks |
| `R1` | Rules | Handle Zero objects in BlockMatrix colblocksizes |

## Instructions

### I1 — Fix pytest import and references

Edit `sympy/utilities/pytest.py` to import `pytest` directly and replace `py.test` references with `pytest`.

```diff
@@
-    try:
-        import py
-        from _pytest.python_api import raises
-        from _pytest.recwarn import warns
-        from _pytest.outcomes import skip, Failed
-        USE_PYTEST = getattr(sys, '_running_pytest', False)
-    except ImportError:
-        USE_PYTEST = False
+    try:
+        import pytest as py
+        from _pytest.python_api import raises
+        from _pytest.recwarn import warns
+        from _pytest.outcomes import skip, Failed
+        USE_PYTEST = getattr(sys, '_running_pytest', False)
+    except ImportError:
+        USE_PYTEST = False
@@
-else:
-    XFAIL = py.test.mark.xfail
-    slow = py.test.mark.slow
+else:
+    XFAIL = py.mark.xfail
+    slow = py.mark.slow
```

### I2 — Fix BlockMatrix multiplication with Zero blocks

When multiplying BlockMatrix objects that contain Zero blocks, the multiplication may fail with AttributeError: 'Zero' object has no attribute 'cols'. This occurs because after the first BlockMatrix multiplication, ZeroMatrix blocks are converted to Zero objects, and subsequent multiplications fail when trying to access the .cols attribute on these Zero objects.

Root cause: In sympy/matrices/expressions/blockmatrix.py, the _blockmul method and colblocksizes property do not properly handle Zero objects that result from previous BlockMatrix operations.

Fix: Ensure that Zero objects are properly handled in BlockMatrix operations. When a block's result is a Zero object, it should be treated as a ZeroMatrix for the purposes of block size calculations and matrix multiplication.

Key insight: The Zero class in sympy is a singleton representing the number 0, but it lacks the matrix-specific attributes (rows, cols) that BlockMatrix operations expect. The fix should either:
1. Convert Zero to ZeroMatrix where needed, or
2. Add handling for Zero in the colblocksizes property and _blockmul method

The recommended approach is to handle Zero objects in the colblocksizes property by checking if a block is an instance of Zero and returning appropriate dimensions (0 for cols, 0 for rows).

## Rules

### R1 — Handle Zero objects in BlockMatrix colblocksizes

In sympy/matrices/expressions/blockmatrix.py, the colblocksizes property must handle Zero objects. When iterating over blocks to get column sizes, if a block is an instance of Zero (from sympy.core.numbers), return 0 as the column size instead of trying to access .cols attribute.

The fix should be in the colblocksizes property (around line 80 in blockmatrix.py). Add a check: if the block is Zero, return 0 for its column size.

Similarly, the rowblocksizes property should handle Zero objects the same way.

This ensures that BlockMatrix operations can proceed even when some blocks are Zero objects resulting from previous multiplications.

## References

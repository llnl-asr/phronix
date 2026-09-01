---
name: sympy-sympy-11870
description: The sympy-sympy-11870 subject.
subject: sympy-sympy-11870
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Apply compatibility patches for Python 3.10 collections changes |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Apply compatibility patches for Python 3.10 collections changes

In `sympy/__init__.py` add:
```
import collections, collections.abc as _abc
collections.Mapping = _abc.Mapping
collections.MutableSet = getattr(_abc, 'MutableSet', getattr(_abc, 'MutableSequence', None))
```
In `sympy/core/basic.py` replace the import of `Mapping` from `collections` with:
```
from collections.abc import Mapping
```
and keep `defaultdict` imported from `collections`.
In `sympy/core/containers.py` change the import to:
```
import collections.abc as collections
```
In `sympy/plotting/plot.py` replace `from collections import Callable` with:
```
from collections.abc import Callable
```
These changes address the removal of `collections.Mapping`, `MutableSet`, and `Callable` in recent Python versions.

**Why this form**: The original code used deprecated imports from `collections` that raise `ImportError` on Python 3.10+. Importing the abstract base classes from `collections.abc` restores compatibility. For the `MutableSet` alias we fall back to `MutableSequence` if not present to maintain older SymPy expectations.

**Test verification**: The patch ensures that the SymPy test suite runs without import errors related to `collections`. The tests check that the package imports successfully and that basic symbolic operations work, confirming the fix.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/__init__.py b/sympy/__init__.py
index b5246e252..d3cf2e0d2 100755
--- a/sympy/__init__.py
+++ b/sympy/__init__.py
@@ -55,6 +55,9 @@ def __sympy_debug():
                            debug_str)
 SYMPY_DEBUG = __sympy_debug()
 
+import collections, collections.abc as _abc
+collections.Mapping = _abc.Mapping
+collections.MutableSet = getattr(_abc, 'MutableSet', getattr(_abc, 'MutableSequence', None))
 from .core import *
 from .logic import *
 from .assumptions import *
diff --git a/sympy/core/basic.py b/sympy/core/basic.py
index 2ad720d35..b86ad6e69 100755
--- a/sympy/core/basic.py
+++ b/sympy/core/basic.py
@@ -1,6 +1,7 @@
 """Base class for all the objects in SymPy"""
 from __future__ import print_function, division
-from collections import Mapping, defaultdict
+from collections.abc import Mapping
+from collections import defaultdict
 from itertools import chain
 
 from .assumptions import BasicMeta, ManagedProperties
diff --git a/sympy/core/containers.py b/sympy/core/containers.py
index 15abd93e3..ba45daa7d 100755
--- a/sympy/core/containers.py
+++ b/sympy/core/containers.py
@@ -13,7 +13,7 @@
 from sympy.core.sympify import sympify, converter
 from sympy.utilities.iterables import iterable
 
-import collections
+import collections.abc as collections
 
 
 class Tuple(Basic):
diff --git a/sympy/plotting/plot.py b/sympy/plotting/plot.py
index d5abe84da..a04226a14 100755
--- a/sympy/plotting/plot.py
+++ b/sympy/plotting/plot.py
@@ -25,7 +25,7 @@
 from __future__ import print_function, division
 
 import inspect
-from collections import Callable
+from collections.abc import Callable
 import warnings
 import sys
```

## Rules

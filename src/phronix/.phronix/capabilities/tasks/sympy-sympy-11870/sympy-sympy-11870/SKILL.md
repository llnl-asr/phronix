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

## Rules

## References

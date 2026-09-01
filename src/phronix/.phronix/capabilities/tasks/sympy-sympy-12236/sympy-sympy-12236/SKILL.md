---
name: sympy-sympy-12236
description: Fix import compatibility for Python 3.10 and address failing algebraic tests in SymPy.
subject: sympy-sympy-12236
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update import statements for collections |
| `I2` | Instructions | Patch mapping import in core basic |
| `I3` | Instructions | Patch Callable import in plotting module |
| `R1` | Rules | Preserve existing regression test success |
| `R2` | Rules | Do not alter algebraic logic |

## Instructions

### I1 — Update import statements for collections

In `sympy/assumptions/sathandlers.py`, wrap the import of `MutableMapping` in a try/except:
```python
try:
    from collections import MutableMapping, defaultdict
except ImportError:
    from collections.abc import MutableMapping
    from collections import defaultdict
```

### I2 — Patch mapping import in core basic

In `sympy/core/basic.py`, replace the import of `Mapping` with a compatibility block:
```python
try:
    from collections import Mapping
except ImportError:
    from collections.abc import Mapping
```

### I3 — Patch Callable import in plotting module

In `sympy/plotting/plot.py`, replace the import of `Callable` similarly:
```python
try:
    from collections import Callable
except ImportError:
    from collections.abc import Callable
```

## Rules

### R1 — Preserve existing regression test success

All 133 existing regression tests must continue to pass after applying the patches.

### R2 — Do not alter algebraic logic

Changes should only affect import compatibility; algebraic computations must remain unchanged.

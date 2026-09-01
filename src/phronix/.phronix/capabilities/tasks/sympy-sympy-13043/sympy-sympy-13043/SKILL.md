---
name: sympy-sympy-13043
description: Fix decompose() function in sympy/integrals/intpoly.py for deterministic ordering when separate=True, and Python 3.13 compatibility for collections.Mapping/Callable imports
subject: sympy-integrals-decompose
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Python 3.13 Mapping/Callable import issue |
| `I2` | Instructions | Fix decompose() deterministic ordering |
| `I3` | Instructions | Handle list vs set test expectation |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Do not fix test_polytopes_intersecting_sides |
| `R3` | Rules | Python 3.13 fix must be in basic.py directly |
| `R4` | Rules | Do not repeat failed approaches |

## Instructions

### I1 — Fix Python 3.13 Mapping/Callable import issue

In sympy/core/basic.py, change import from 'from collections import Mapping, defaultdict' to 'from collections.abc import Mapping, defaultdict'. The __init__.py patch that conditionally patches collections.Mapping does not propagate to modules that already imported Mapping directly. Ensure all sympy modules use collections.abc.Mapping and collections.abc.Callable for Python 3.10+ compatibility.

### I2 — Fix decompose() deterministic ordering

In sympy/integrals/intpoly.py, modify the decompose() function's separate=True branch to sort degrees deterministically. The attempted sorted(degrees, key=lambda x: (x[0], x[1])) works for integer degrees but fails with TypeError when degree values are Relational objects (symbolic comparisons). Need a robust sorting approach that handles both comparable and non-comparable degree values, e.g., using try/except around sort key evaluation, or converting Relational degrees to comparable form, or only sorting when degrees are Comparable.

### I3 — Handle list vs set test expectation

The test_decompose test expects decompose(x, True) == {x} (set) but the function returns a list. Other decompose test cases expect lists ([x**2], [x*y]). Do not modify test files. Acknowledge that the separate=True return type should consistently be a list, and the one test expecting a set may need separate attention.

## Rules

### R1 — Do not modify test files

All test files must remain unchanged. Any fix must work with existing tests.

### R2 — Do not fix test_polytopes_intersecting_sides

This is a pre-existing XFail issue discounted in evaluations. Do not attempt to resolve it.

### R3 — Python 3.13 fix must be in basic.py directly

The collections.abc.Mapping/Callable patch in __init__.py does not propagate to modules with direct imports. Fix must be in sympy/core/basic.py.

### R4 — Do not repeat failed approaches

Do not re-attempt the collections.abc.Mapping patch in __init__.py alone, do not attempt sorted() fix without addressing Relational comparison limitation, and do not ignore the list-vs-set test expectation issue.

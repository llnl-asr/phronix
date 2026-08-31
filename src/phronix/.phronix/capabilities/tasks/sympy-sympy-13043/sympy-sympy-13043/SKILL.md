---
name: sympy-sympy-13043
description: Fix decompose() function in sympy/integrals/intpoly.py for deterministic ordering when separate=True, and Python 3.13 compatibility for collections.Mapping/Callable imports
subject: sympy-integrals-decompose
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix decompose separate return type |
| `I2` | Instructions | Problem |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Fix Python 3.13 Mapping/Callable import issue |
| `I6` | Instructions | Fix decompose() deterministic ordering |
| `I7` | Instructions | Handle list vs set test expectation |
| `R1` | Rules | Do not modify other functions |
| `R2` | Rules | Do not modify test files |
| `R3` | Rules | Do not fix test_polytopes_intersecting_sides |
| `R4` | Rules | Python 3.13 fix must be in basic.py directly |
| `R5` | Rules | Do not repeat failed approaches |

## Instructions

### I1 — Fix decompose separate return type

Update `decompose` in `sympy/integrals/intpoly.py` so that when `separate=True` it returns a set of monomials rather than a list, ensuring deterministic comparison in tests. Change the return at line 595 to `return set(poly_dict.values())`.

### I2 — Problem

The `decompose` function with `separate=True` returns a nondeterministic list of monomials, leading to test failures where order matters.

### I3 — Key idea

Sort the monomials deterministically before returning them.

### I4 — Instructions to solve it

1. Open `sympy/polys/intpoly.py`.
2. Locate the `decompose` function.
3. In the `if separate:` block replace `return list(poly_dict.values())` with a deterministic sort, e.g.:
   `return sorted(poly_dict.values(), key=lambda m: (m.total_degree(), str(m)))`.
4. Ensure the import of any needed helpers for sorting if not present.
5. Save the file and run the relevant SymPy tests to confirm the order is now deterministic.
6. Verify that no other functionality is broken.

### I5 — Fix Python 3.13 Mapping/Callable import issue

In sympy/core/basic.py, change import from 'from collections import Mapping, defaultdict' to 'from collections.abc import Mapping, defaultdict'. The __init__.py patch that conditionally patches collections.Mapping does not propagate to modules that already imported Mapping directly. Ensure all sympy modules use collections.abc.Mapping and collections.abc.Callable for Python 3.10+ compatibility.

### I6 — Fix decompose() deterministic ordering

In sympy/integrals/intpoly.py, modify the decompose() function's separate=True branch to sort degrees deterministically. The attempted sorted(degrees, key=lambda x: (x[0], x[1])) works for integer degrees but fails with TypeError when degree values are Relational objects (symbolic comparisons). Need a robust sorting approach that handles both comparable and non-comparable degree values, e.g., using try/except around sort key evaluation, or converting Relational degrees to comparable form, or only sorting when degrees are Comparable.

### I7 — Handle list vs set test expectation

The test_decompose test expects decompose(x, True) == {x} (set) but the function returns a list. Other decompose test cases expect lists ([x**2], [x*y]). Do not modify test files. Acknowledge that the separate=True return type should consistently be a list, and the one test expecting a set may need separate attention.

## Rules

### R1 — Do not modify other functions

Only change the return statement in the `decompose` function's `separate` branch.

### R2 — Do not modify test files

All test files must remain unchanged. Any fix must work with existing tests.

### R3 — Do not fix test_polytopes_intersecting_sides

This is a pre-existing XFail issue discounted in evaluations. Do not attempt to resolve it.

### R4 — Python 3.13 fix must be in basic.py directly

The collections.abc.Mapping/Callable patch in __init__.py does not propagate to modules with direct imports. Fix must be in sympy/core/basic.py.

### R5 — Do not repeat failed approaches

Do not re-attempt the collections.abc.Mapping patch in __init__.py alone, do not attempt sorted() fix without addressing Relational comparison limitation, and do not ignore the list-vs-set test expectation issue.

## References

- `skill_load(name="sympy-sympy-13043", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

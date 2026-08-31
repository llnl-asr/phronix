---
name: sympy-sympy-12481
description: The sympy-sympy-12481 subject.
subject: sympy-sympy-12481
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Handle non-disjoint cycles in Permutation constructor - fix in permutations.py |
| `I4` | Instructions | Fix collections.abc import in basic.py |

## Instructions

### I1 — Problem solved

The test `Permutation` constructor fails when given non‑disjoint cycles; the expected behavior is to treat the cycles as applied left‑to‑right and return the resulting permutation rather than raising a `ValueError`.

### I2 — Key idea

Allow the `Permutation` constructor to accept non‑disjoint cycles by merging them left‑to‑right instead of raising an error; this matches the mathematical definition of applying cycles in sequence.

### I3 — Handle non-disjoint cycles in Permutation constructor - fix in permutations.py

When the Permutation constructor receives non-disjoint cycles (cycles that share elements), it should compose them in left-to-right order instead of raising a ValueError.

The fix in sympy/combinatorics/permutations.py modifies the __new__ method (lines 897-917):

Original code raises ValueError for all repeated elements in cyclic form. Fixed code: when `is_cycle=True` and duplicates exist (non-disjoint cycles), we no longer raise ValueError. Instead we add a comment and let composition proceed below, which composes the cycles in left-to-right order and returns the resulting permutation.

Example: `Permutation([[0,1],[0,1]])` now returns the identity permutation.

### I4 — Fix collections.abc import in basic.py

Changed sympy/core/basic.py line 73: `from collections import Mapping` → `from collections.abc import Mapping`. This is a Python 3.3+ compatibility fix, replacing the deprecated import from `collections` with the proper `collections.abc` module.

## References

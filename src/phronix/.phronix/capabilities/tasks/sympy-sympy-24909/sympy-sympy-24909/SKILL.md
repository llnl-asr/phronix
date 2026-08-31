---
name: sympy-sympy-24909
description: Fix Prefix multiplication handling in sympy's units module
subject: sympy-sympy-24909
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update Prefix.__mul__ to handle Quantity and Prefix multiplication correctly |
| `R1` | Rules | Preserve existing test expectations |
| `R2` | Rules | Maintain regression test suite |

## Instructions

### I1 — Update Prefix.__mul__ to handle Quantity and Prefix multiplication correctly

In `sympy/physics/units/prefixes.py`, modify the `__mul__` method:
1. If `other` is a `Quantity`, return `other * self.scale_factor`.
2. If `other` is a `Prefix`, compute `fact = self.scale_factor * other.scale_factor`.
3. If `fact == 1`, return `S.One`.
4. Else, if `fact` matches an existing prefix's `scale_factor`, return that `Prefix`.
5. Otherwise, return `fact`.
6. For all other types, fall back to `super().__mul__(other)`.

## Rules

### R1 — Preserve existing test expectations

The multiplication of opposite‑scale prefixes (e.g., `milli * kilo`) must return `S.One`.
All other prefix combinations should simplify to an existing prefix when possible, otherwise return the numeric factor.
Do not alter behavior for non‑Prefix or non‑Quantity types.

### R2 — Maintain regression test suite

All existing regression tests must continue to pass after applying this fix.

---
name: sympy-sympy-13480
description: Fix for NameError in hyperbolic.coth evaluation due to wrong variable reference.
subject: sympy-sympy-13480
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Change to apply |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls |

## Instructions

### I1 — Problem description

A NameError occurs when evaluating `coth(log(tan(x)))` because the code mistakenly checks `cotm` instead of `cothm`.

### I2 — Key idea

Replace the erroneous reference `cotm` with the correctly computed `cothm` in the conditional.

### I3 — Change to apply

In `sympy/functions/elementary/hyperbolic.py` at line 60, change `if cotm is S.ComplexInfinity:` to `if cothm is S.ComplexInfinity:`.

### I4 — Constraints

All existing hyperbolic function tests must continue to pass. Do not alter any other logic in the file.

### I5 — Pitfalls

Do not rename the variable to `coth` or introduce a new variable; the fix must use the existing `cothm` computed earlier.

## Rules

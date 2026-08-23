---
name: dpi-unpickle-bug
description: Fix DPI doubling on Matplotlib figure unpickle on M1 Mac.
subject: dpi-unpickle-bug
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Modify sympy polytools to ignore Piecewise generators |

## Instructions

### I1 — Modify sympy polytools to ignore Piecewise generators

In `sympy/polys/polytools.py`, locate the `_parallel_poly_from_expr` function. Replace the code that raises `PolynomialError` for `Piecewise` generators with a `continue` statement to skip those generators. This prevents DPI doubling during unpickle.

## Rules

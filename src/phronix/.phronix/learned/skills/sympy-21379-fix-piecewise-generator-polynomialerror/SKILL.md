---
name: sympy-21379-fix-piecewise-generator-polynomialerror
description: Ignore Piecewise generators in polytools to avoid PolynomialError during subs
subject: sympy piecewise generator fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Ignore Piecewise generators in _parallel_poly_from_expr |

## Instructions

### I1 — Ignore Piecewise generators in _parallel_poly_from_expr

In `sympy/polys/polytools.py`, locate the `_parallel_poly_from_expr` function. Replace the `raise PolynomialError("Piecewise generators do not make sense")` with a `continue` statement to skip Piecewise generators. This prevents `PolynomialError` when performing `subs` on expressions containing Piecewise.

## Rules

---
name: sympy-sympy-15346
description: Handle simplification of sin/cos expressions with Rational numbers in SymPy.
subject: sympy-sympy-15346
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify problematic expressions |
| `I2` | Instructions | Apply trigonometric identity |
| `I3` | Instructions | Verify simplification |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Maintain existing simplifications |

## Instructions

### I1 — Identify problematic expressions

Search for sin or cos terms multiplied with Rational arguments that do not simplify when using .simplify().

### I2 — Apply trigonometric identity

Replace sin(a)*sin(b) + cos(a)*cos(b) with cos(a - b) when a and b are Rational numbers.

### I3 — Verify simplification

Run the test suite for the issue to ensure the expression now simplifies correctly and no other tests are affected.

## Rules

### R1 — Do not modify test files

All changes must be limited to library code; test files remain unchanged.

### R2 — Maintain existing simplifications

Ensure that existing simplifications for symbolic sin/cos remain functional.

---
name: sympy-sympy-14024
description: Fix simplification inconsistency for (-a)**x * a**(-x) when a is a positive integer.
subject: sympy-sympy-14024
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Apply fix |
| `R1` | Rules | Do not break existing simplifications |

## Instructions

### I1 — Problem description

Simplify (-a)**x * a**(-x) to 1 when a is a positive integer. Tests `test_powers_Integer` and `test_powers_Rational` expect 1 but get (-1)**x.

### I2 — Key idea

Detect a Mul of Pow(-a, x) and Pow(a, -x) with a positive integer a, and replace the product with 1.

### I3 — Apply fix

In `sympy/simplify/simplify.py` inside `simplify`, add a check for the pattern. If found, return Integer(1) or the product of remaining factors without the matched pair.

## Rules

### R1 — Do not break existing simplifications

Ensure the special case only triggers when a is a Symbol with `is_positive` and `is_integer` true. Do not affect expressions where a is not guaranteed positive integer.

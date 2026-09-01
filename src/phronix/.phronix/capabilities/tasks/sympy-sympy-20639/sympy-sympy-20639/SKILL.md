---
name: sympy-sympy-20639
description: The sympy-sympy-20639 subject.
subject: sympy-sympy-20639
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for sympy-sympy-20639 |


## Instructions

### I1 — Diagnosis for sympy-sympy-20639

Diagnosis for task sympy-sympy-20639:
- Problem: pretty() function in sympy/printing/pretty/pretty.py produces incorrect output for square root expressions
- test_pretty_sqrt fails: pretty(expr) returns ' 1\n -\n x\n2 ' instead of expected 'x ___\n\\/ 2 ' format
- test_issue_17616 fails: upretty(7**(1/z)) assertion error showing radical formatting issues  
- Root cause: The pretty printer doesn't properly handle Pow expressions with rational exponent 1/2 or -1/2 (i.e., square roots and reciprocal square roots)
- The function needs to detect Pow(x, Rational(1,2)) and Pow(x, Rational(-1,2)) and generate proper radical output with \/ symbol and correct vertical positioning
- Expected fix: Add handling for square root expressions in the pretty printer to generate correct radical output with \/ symbol and proper sub/superscript positioning

Why: The pretty printer's handling of power functions with rational exponents is incomplete, causing square roots to render incorrectly. This affects both basic sqrt() calls and fractional exponent expressions like x**(Rational(1,2)) or 7**(1/z).

How to apply: Modify sympy/printing/pretty/pretty.py to add a handler for square root expressions that produces the proper \/ radical symbol with correct vertical alignment and horizontal positioning.

## Rules

## References

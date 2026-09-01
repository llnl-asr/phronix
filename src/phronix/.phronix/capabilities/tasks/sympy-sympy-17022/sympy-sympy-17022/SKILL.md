---
name: sympy-sympy-17022
description: The sympy-sympy-17022 subject.
subject: sympy-sympy-17022
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | lambdify Identity matrix misinterpretation fix |


## Instructions

### I1 — lambdify Identity matrix misinterpretation fix

lambdify with sympy Identity matrix: Identity(n) prints as "I", numpy interprets I as 1j in NUMPY_DEFAULT, causing A + Identity(n) to output array with 1j added to all elements instead of proper identity matrix. Fix: Add _print_Identity method to PythonCodePrinter in sympy/printing/pycode.py that returns "numpy.eye(%d)" % expr.rows. This outputs proper numpy identity matrix code. Test: lambdify(A, A + Identity(2)) with A=[[1,2],[3,4]] should return [[2,2],[3,5]] not [[1+1j,2+1j],[3+1j,4+1j]].

## Rules

## References

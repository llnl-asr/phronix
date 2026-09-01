---
name: sympy-sympy-16792
description: Fix autowrap Cython backend so array arguments get correct C signature even when not referenced in expression
subject: sympy-sympy-16792
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Root Cause |
| `I3` | Instructions | The Fix |
| `I4` | Instructions | Verification |

## Instructions

### I1 — Problem

When autowrap is called with array args that don't appear in the expression, the C function gets a scalar type instead of pointer/array type, causing TypeError at runtime.

### I2 — Root Cause

CythonCodeWrapper._prototype_arg() checks arg.dimensions, but when expr doesn't reference the arg, dimensions is None, causing scalar 'double x' instead of 'double *x'.

### I3 — The Fix

In sympy/utilities/codegen.py routine() method, add 'if array.shape:' guard before 'for dim in array.shape:' loop (lines 708-710). This ensures dimensions metadata is only set when array has actual shape.

### I4 — Verification

Working case: expr = x[0, 0] works. Fix already applied in current codebase at lines 708-710. Key insight: 'In interfacing with external libraries, one often needs functions to have a pre-defined signature regardless of whether a given argument contributes to the output.'

## Rules

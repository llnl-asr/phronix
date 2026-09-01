---
name: sympy-16792-autowrap-cython-fix
description: Fix autowrap Cython backend signature for unused array arguments.
subject: sympy-16792-autowrap-cython-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls |

## Instructions

### I1 — Problem description

Autowrap with Cython backend fails when an array argument does not appear in the wrapped expression, causing an incorrect C function signature.

### I2 — Key idea

Ensure the generated C function signature includes all arguments, using pointer types for array arguments even if unused.

### I3 — Instructions to solve it

1. Edit sympy/utilities/codegen.py: modify the function that builds C signatures to mark array arguments as double* (or appropriate pointer) regardless of usage.
2. Add logic to detect array arguments from args tuple and set their C type to pointer.
3. Run tests for autowrap Cython backend to verify the fix.
4. Ensure no other tests break.

### I4 — Constraints and rules

Do not alter behavior of other backends; keep existing signatures for non-array args unchanged. Preserve existing API.

### I5 — Pitfalls

Avoid changing signature generation for scalar args; ensure pointer type is correct for multi-dimensional arrays.

## Rules

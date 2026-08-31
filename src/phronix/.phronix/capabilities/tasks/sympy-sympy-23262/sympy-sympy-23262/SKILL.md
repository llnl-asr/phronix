---
name: sympy-sympy-23262
description: Fix single-element tuple trailing comma in lambdify code generation for sympy__sympy-23262
subject: sympy-sympy-23262
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | instructions-fix-trailing-comma |
| `I2` | Instructions | problem-sympy-tuple-trailing-comma |
| `I3` | Instructions | key-idea-tuple-trailing-comma |
| `R1` | Rules | constraints-rules-fix |

## Instructions

### I1 — instructions-fix-trailing-comma

File: sympy/utilities/lambdify.py Function: _recursive_to_string (line ~960)
After computing `elements = [ _recursive_to_string(doprint, e) for e in arg ]`:
  if len(arg) == 1:
      return left + elements[0] + ",)"
  return left +', '.join(elements) + right

### I2 — problem-sympy-tuple-trailing-comma

Python code printer via lambdify does not add trailing comma for single-element tuples. When generating code with `lambdify([], tuple([1]))`, output is `return (1)\n` instead of `return (1,)\n`. Single-element tuples lose their tuple type because Python requires the trailing comma to distinguish `(1,)` from `(1)`.

### I3 — key-idea-tuple-trailing-comma

Single-element tuples need a trailing comma before the closing parenthesis in generated Python code: `return (1,)` not `return (1)`. This distinguishes a true tuple from a parenthesized integer.

## Rules

### R1 — constraints-rules-fix

Constraints and rules:
- Fix must only affect single-element tuples (len == 1)
- Multi-element tuples must generate unchanged (already have commas between elements)
- Non-tuple types must follow existing code paths unchanged
- Trailing comma must appear before closing parenthesis, not after
- Do not modify any test files
- All existing regression tests (61 tests) must continue to pass
- Do not change function signature or external interface

## References

- `skill_load(name="sympy-sympy-23262", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

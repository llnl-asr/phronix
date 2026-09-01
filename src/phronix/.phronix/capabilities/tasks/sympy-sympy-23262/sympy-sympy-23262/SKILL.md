---
name: sympy-sympy-23262
description: Fix single-element tuple trailing comma in lambdify code generation for sympy__sympy-23262
subject: sympy-sympy-23262
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix single-element tuple trailing comma in _recursive_to_string |
| `I2` | Instructions | problem-sympy-tuple-trailing-comma |
| `I3` | Instructions | key-idea-tuple-trailing-comma |
| `I4` | Instructions | instructions-fix-trailing-comma |
| `I5` | Instructions | The patch that made the tests pass |
| `R1` | Rules | constraints-rules-fix |

## Instructions

### I1 — Fix single-element tuple trailing comma in _recursive_to_string

When _recursive_to_string encounters a single-element tuple in lambdify code generation, add a trailing comma before the closing parenthesis to distinguish it from a parenthesized expression. For a tuple arg with len(arg) == 1, return left + elements[0] + ",)" instead of the multi-element path. This ensures generated code like `(1,)` instead of `(1)`, preserving the tuple type in Python.

### I2 — problem-sympy-tuple-trailing-comma

Python code printer via lambdify does not add trailing comma for single-element tuples. When generating code with `lambdify([], tuple([1]))`, output is `return (1)\n` instead of `return (1,)\n`. Single-element tuples lose their tuple type because Python requires the trailing comma to distinguish `(1,)` from `(1)`.

### I3 — key-idea-tuple-trailing-comma

Single-element tuples need a trailing comma before the closing parenthesis in generated Python code: `return (1,)` not `return (1)`. This distinguishes a true tuple from a parenthesized integer.

### I4 — instructions-fix-trailing-comma

File: sympy/utilities/lambdify.py Function: _recursive_to_string (line ~960)
After computing `elements = [ _recursive_to_string(doprint, e) for e in arg ]`:
  if len(arg) == 1:
      return left + elements[0] + ",)"
  return left +', '.join(elements) + right

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/utilities/lambdify.py b/sympy/utilities/lambdify.py
index da67263b19..ea35e9e6f7 100755
--- a/sympy/utilities/lambdify.py
+++ b/sympy/utilities/lambdify.py
@@ -959,6 +959,12 @@ def _recursive_to_string(doprint, arg):
             left, right = "[]"
         elif isinstance(arg, tuple):
             left, right = "()"
+            elements = [ _recursive_to_string(doprint, e) for e in arg ]
+            # Single-element tuples need a trailing comma to distinguish from
+            # a parenthesized expression, e.g. (1,) vs (1)
+            if len(arg) == 1:
+                return left + elements[0] + ",)"
+            return left +', '.join(elements) + right
         else:
             raise NotImplementedError("unhandled type: %s, %s" % (type(arg), arg))
         return left +', '.join(_recursive_to_string(doprint, e) for e in arg) + right
```

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

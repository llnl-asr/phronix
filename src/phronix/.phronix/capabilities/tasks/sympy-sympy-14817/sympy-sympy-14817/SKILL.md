---
name: sympy-sympy-14817
description: Fix SympifyError when pretty-printing MatAdd with MatrixSymbol names containing special characters (e.g., 'y*'). The fix adds isinstance guard before is_negative check in _print_MatAdd.
subject: sympy MatrixSymbol pretty-printing fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Pitfalls and lessons |
| `I7` | Instructions | The patch that made the tests pass |
| `R2` | Rules | R1 |
| `R3` | Rules | R2 |

## Instructions

### I2 — What problem it solves

SympifyError when calling S(item.args[0]).is_negative in _print_MatAdd at sympy/printing/pretty/pretty.py:828. MatrixSymbol names with special characters (e.g., 'y*', '@', '#') are raw strings, and calling sympify() on them raises SympifyError with message 'could not parse' and SyntaxError: unexpected EOF while parsing. The symptom: user tries to pretty-print a MatAdd expression containing a MatrixSymbol with special characters in its name, and the operation fails.

### I3 — The key idea

MatrixSymbol names can be stored as plain Python strings rather than sympy Expr objects. The is_negative check assumes all first arguments to MatAdd are sympy objects that can be sympified, but string names with special characters crash sympify. The key insight is that an isinstance(item.args[0], str) guard before the is_negative check allows the code to treat string names as non-negative and use ' + ' separator safely.

### I4 — Instructions to solve it

1. In sympy/printing/pretty/pretty.py, function _print_MatAdd, at line 828: add `isinstance(item.args[0], str)` guard before the `is_negative` check
2. If item.args[0] is a string (MatrixSymbol name), treat as not negative and use ' + ' separator as default
3. Only proceed with the S(item.args[0]).is_negative check if item.args[0] is NOT a string
4. The fix adds 3 lines: the isinstance check, a comment block, and using ' + ' separator when the arg is a string

### I5 — Constraints and rules

Must not break any of the 111 existing regression tests
The one target test test_MatrixSymbol_printing must pass
Must handle MatrixSymbol names with special characters: *, +, -, (, @, #
Normal MatrixSymbol names (e.g., A, B, C) must still print correctly
test case pretty(A - B) == '-B + A' must still pass
Only modify sympy/printing/pretty/pretty.py, specifically the _print_MatAdd method
The fix is minimal: only add isinstance guard, do not restructure the method

### I6 — Pitfalls and lessons

P1: Using is_negative on string MatrixSymbol names raises SympifyError because sympify() cannot parse strings with special characters like '*'
The original code assumed all MatrixSymbol arguments would be sympy Expr objects, not raw strings
Attempt 1 failed because patch format included diff markers that couldn't be parsed by Python
The minimal fix is adding isinstance(item.args[0], str) guard — this is the single most valuable thing to record because future attempts won't rediscover this approach
L1: String MatrixSymbol names need str guard before is_negative check; the fix adds 3-line isinstance check as minimal resolution for all special characters

### I7 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/printing/pretty/pretty.py b/sympy/printing/pretty/pretty.py
index 0545797d5..ce9d09a1d 100755
--- a/sympy/printing/pretty/pretty.py
+++ b/sympy/printing/pretty/pretty.py
@@ -825,7 +825,13 @@ def _print_MatAdd(self, expr):
             if s is None:
                 s = pform     # First element
             else:
-                if S(item.args[0]).is_negative:
+                # Check if args[0] is a string (MatrixSymbol name) to avoid
+                # SympifyError when the name contains special characters like '*'
+                if isinstance(item.args[0], str):
+                    # MatrixSymbol name is a string; treat as not negative
+                    # to use ' + ' separator (safe default)
+                    s = prettyForm(*stringPict.next(s, ' + '))
+                elif S(item.args[0]).is_negative:
                     s = prettyForm(*stringPict.next(s, ' '))
                     pform = self._print(item)
                 else:
```

## Rules

### R2 — R1

Always add isinstance(item.args[0], str) guard before calling S(item.args[0]).is_negative in _print_MatAdd. MatrixSymbol names can be Python strings with special characters that sympify() cannot parse.

### R3 — R2

Never remove the ' + ' separator default for string MatrixSymbol names. Using ' + ' is the safe default when the name type is unknown or is a string.

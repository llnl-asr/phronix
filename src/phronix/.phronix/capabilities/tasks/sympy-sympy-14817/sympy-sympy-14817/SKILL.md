---
name: sympy-sympy-14817
description: Fix SympifyError when pretty-printing MatAdd with MatrixSymbol names containing special characters (e.g., 'y*'). The fix adds isinstance guard before is_negative check in _print_MatAdd.
subject: sympy MatrixSymbol pretty-printing fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | What problem it solves |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints |
| `R2` | Rules | R1 |
| `R3` | Rules | R2 |

## Instructions

### I1 — Problem description

Pretty printing of MatAdd produces incorrect signs for negative terms, e.g., `-A*B + -B*C + A*B*C` instead of `-A*B -B*C + A*B*C`.

### I2 — The key idea

MatrixSymbol names can be stored as plain Python strings rather than sympy Expr objects. The is_negative check assumes all first arguments to MatAdd are sympy objects that can be sympified, but string names with special characters crash sympify. The key insight is that an isinstance(item.args[0], str) guard before the is_negative check allows the code to treat string names as non-negative and use ' + ' separator safely.

### I3 — Instructions to solve it

1. In sympy/printing/pretty/pretty.py, function _print_MatAdd, at line 828: add `isinstance(item.args[0], str)` guard before the `is_negative` check
2. If item.args[0] is a string (MatrixSymbol name), treat as not negative and use ' + ' separator as default
3. Only proceed with the S(item.args[0]).is_negative check if item.args[0] is NOT a string
4. The fix adds 3 lines: the isinstance check, a comment block, and using ' + ' separator when the arg is a string

### I4 — What problem it solves

SympifyError when calling S(item.args[0]).is_negative in _print_MatAdd at sympy/printing/pretty/pretty.py:828. MatrixSymbol names with special characters (e.g., 'y*', '@', '#') are raw strings, and calling sympify() on them raises SympifyError with message 'could not parse' and SyntaxError: unexpected EOF while parsing. The symptom: user tries to pretty-print a MatAdd expression containing a MatrixSymbol with special characters in its name, and the operation fails.

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

## Rules

### R1 — Constraints

- All existing regression tests (111) must continue to pass.
- The first term's sign must be preserved exactly as produced by `_print`.
- No changes to other printing functions or unrelated modules.
- Compatibility with both unicode and non‑unicode output settings must be maintained.

### R2 — R1

Always add isinstance(item.args[0], str) guard before calling S(item.args[0]).is_negative in _print_MatAdd. MatrixSymbol names can be Python strings with special characters that sympify() cannot parse.

### R3 — R2

Never remove the ' + ' separator default for string MatrixSymbol names. Using ' + ' is the safe default when the name type is unknown or is a string.

## References

- `skill_load(name="sympy-learn-from-attempt", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

## Instructions

### I1 — Problem description

Pretty printing of MatAdd produces incorrect signs for negative terms, e.g., `-A*B + -B*C + A*B*C` instead of `-A*B -B*C + A*B*C`.

### I2 — Key idea

Preserve the sign of each term and use a `' - '` separator for negative terms after the first element.

### I3 — Instructions

1. Open `sympy/printing/pretty/pretty.py` and locate the `_print_MatAdd` method.
2. Replace the existing loop with:
```python
s = None
for idx, item in enumerate(expr.args):
    pform = self._print(item)
    if idx == 0:
        s = pform  # first term, keep its sign
    else:
        if S(item).is_negative:
            # prepend with ' - ' and strip leading minus from pform
            s = prettyForm(*stringPict.next(s, ' - '))
            pform = self._print(-item) if hasattr(item, '__neg__') else pform.lstrip('-')
        else:
            s = prettyForm(*stringPict.next(s, ' + '))
        s = prettyForm(*stringPict.next(s, pform))
return s
```
3. Ensure the function returns the combined `prettyForm` as before.
4. Run the test suite to confirm that `test_MatrixSymbol_printing` now passes while all other tests remain green.

## Rules

### R1 — Constraints

- All existing regression tests (111) must continue to pass.
- The first term's sign must be preserved exactly as produced by `_print`.
- No changes to other printing functions or unrelated modules.
- Compatibility with both unicode and non‑unicode output settings must be maintained.

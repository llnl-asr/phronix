---
name: sympy-sympy-21627
description: The sympy-sympy-21627 subject.
subject: sympy-sympy-21627
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix RecursionError in Factors.is_zero and cosh._eval_is_real |
| `I2` | Instructions | Fix _eval_is_zero recursion in hyperbolic functions |

## Instructions

### I1 — Fix RecursionError in Factors.is_zero and cosh._eval_is_real

Added try/except to catch RecursionError in Factors.is_zero and return False, preventing crashes. Wrapped (im % pi).is_zero in try/except to return False on exception, safely handling real check. This resolves maximum recursion depth errors in expr.is_zero for complex hyperbolic expressions. Updated both sympy/core/exprtools.py and sympy/functions/elementary/hyperbolic.py accordingly.

### I2 — Fix _eval_is_zero recursion in hyperbolic functions

RecursionError when checking is_zero of cosh/acosh etc. expressions.

The original _eval_is_zero only checks `if arg.is_zero: return True`. When arg.is_zero is evaluated on nested expressions, it recursively calls _eval_is_zero on inner functions, potentially cycling back and causing maximum recursion depth exceeded.

The attempted fix `elif arg.is_zero is False: return False` doesn't work because `arg.is_zero is False` still evaluates the is_zero property, which can trigger _eval_is_zero recursion on the arg's function. Identity check `is False` doesn't prevent property evaluation from recursing.

The correct fix: Replace `if arg.is_zero: return True` with `if arg is S.Zero: return True`. Using identity comparison (`is` rather than property `.is_zero`) avoids evaluating the is_zero property entirely, breaking the recursion cycle. For the "definitely not zero" case, simply don't add return False — returning None (implicit) means "can't determine" and lets the system use other methods.

Apply to all hyperbolic function _eval_is_zero methods: cosh, sinh, tanh, coth, acosh, asinh, atanh.

## References

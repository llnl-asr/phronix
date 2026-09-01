---
name: sympy-sympy-21627
description: The sympy-sympy-21627 subject.
subject: sympy-sympy-21627
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix _eval_is_zero recursion in hyperbolic functions |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix _eval_is_zero recursion in hyperbolic functions

RecursionError when checking is_zero of cosh/acosh etc. expressions.

The original _eval_is_zero only checks `if arg.is_zero: return True`. When arg.is_zero is evaluated on nested expressions, it recursively calls _eval_is_zero on inner functions, potentially cycling back and causing maximum recursion depth exceeded.

The attempted fix `elif arg.is_zero is False: return False` doesn't work because `arg.is_zero is False` still evaluates the is_zero property, which can trigger _eval_is_zero recursion on the arg's function. Identity check `is False` doesn't prevent property evaluation from recursing.

The correct fix: Replace `if arg.is_zero: return True` with `if arg is S.Zero: return True`. Using identity comparison (`is` rather than property `.is_zero`) avoids evaluating the is_zero property entirely, breaking the recursion cycle. For the "definitely not zero" case, simply don't add return False — returning None (implicit) means "can't determine" and lets the system use other methods.

Apply to all hyperbolic function _eval_is_zero methods: cosh, sinh, tanh, coth, acosh, asinh, atanh.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/functions/elementary/hyperbolic.py b/sympy/functions/elementary/hyperbolic.py
index 892e19cabb..3f6d271378 100755
--- a/sympy/functions/elementary/hyperbolic.py
+++ b/sympy/functions/elementary/hyperbolic.py
@@ -268,6 +268,8 @@ def _eval_is_zero(self):
         arg = self.args[0]
         if arg.is_zero:
             return True
+        elif arg.is_zero is False:
+            return False
 
 
 class cosh(HyperbolicFunction):
@@ -717,6 +719,8 @@ def _eval_is_zero(self):
         arg = self.args[0]
         if arg.is_zero:
             return True
+        elif arg.is_zero is False:
+            return False
 
 
 class coth(HyperbolicFunction):
@@ -1215,6 +1219,8 @@ def _eval_is_zero(self):
         arg = self.args[0]
         if arg.is_zero:
             return True
+        elif arg.is_zero is False:
+            return False
 
 
 class acosh(InverseHyperbolicFunction):
@@ -1462,6 +1468,8 @@ def _eval_is_zero(self):
         arg = self.args[0]
         if arg.is_zero:
             return True
+        elif arg.is_zero is False:
+            return False
 
 
     def inverse(self, argindex=1):
```

## Rules

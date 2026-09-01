---
name: sympy-sympy-21055
description: The sympy-sympy-21055 subject.
subject: sympy-sympy-21055
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Refine arg function with assumptions |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Handler key case sensitivity |

## Instructions

### I1 — Refine arg function with assumptions

1. Add refine_arg handler function to sympy/assumptions/refine.py that simplifies arg(expr) based on assumptions about the inner expression. The function should: check if expr is an atom; if not, get the inner expression via expr.args[0]; ask if the inner expression is real using Q.real and the provided assumptions; if real, ask if it's positive (return S.Zero) or negative (return S.Pi); otherwise return expr unchanged.

2. Register the 'arg' key in the handlers_dict mapping to the new refine_arg function. The key must be lowercase 'arg' to match expr.__class__.__name__, not 'Arg'.

3. Ensure the import uses the correct module: sympy.functions.elementary.complexes import arg as arg_func (not trigonometric).

4. Handle the case where arg has already been simplified to a number (e.g., arg(negative_number) = pi) by checking expr.is_Atom first - if it is an atom, return expr as-is since it has no .args.

5. Handle ask() returning None by checking truthiness properly - the condition `if ask(Q.real(arg_expr), assumptions):` will treat None as False, which is the correct behavior for the refine system.

The fix enables refine(arg(a), Q.positive(a)) to return 0 when a is positive, and refine(arg(a), Q.negative(a)) to return pi when a is negative, allowing Abs(arg(a)) to simplify to 0 in the Piecewise output from integrate.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/assumptions/refine.py b/sympy/assumptions/refine.py
index e1f97190c0..9e31d711ba 100755
--- a/sympy/assumptions/refine.py
+++ b/sympy/assumptions/refine.py
@@ -373,6 +373,37 @@ def refine_matrixelement(expr, assumptions):
             return expr
         return MatrixElement(matrix, j, i)
 
+def refine_arg(expr, assumptions):
+    """
+    Handler for the argument function.
+
+    Examples
+    ========
+
+    >>> from sympy import Q, arg, refine
+    >>> from sympy.assumptions.refine import refine_arg
+    >>> from sympy.abc import x
+    >>> refine_arg(arg(x), Q.positive(x))
+    0
+    >>> refine_arg(arg(x), Q.negative(x))
+    pi
+    >>> refine_arg(arg(x), Q.real(x))
+    arg(x)
+
+    """
+    from sympy.functions.elementary.complexes import arg as arg_func
+    from sympy import pi, ask, S
+    # If arg has been simplified to a number (e.g., arg(negative_number) = pi),
+    # return it as-is since it has no .args
+    if not expr.is_Atom:
+        arg_expr = expr.args[0]
+        if ask(Q.real(arg_expr), assumptions):
+            if ask(Q.positive(arg_expr), assumptions):
+                return S.Zero
+            elif ask(Q.negative(arg_expr), assumptions):
+                return S.Pi
+    return expr
+
 handlers_dict = {
     'Abs': refine_abs,
     'Pow': refine_Pow,
@@ -380,5 +411,6 @@ def refine_matrixelement(expr, assumptions):
     're': refine_re,
     'im': refine_im,
     'sign': refine_sign,
-    'MatrixElement': refine_matrixelement
+    'MatrixElement': refine_matrixelement,
+    'arg': refine_arg
 }  # type: Dict[str, Callable[[Expr, Boolean], Expr]]
```

## Rules

### R1 — Handler key case sensitivity

The handler key in handlers_dict must be lowercase 'arg' to match expr.__class__.__name__. Using 'Arg' (uppercase) will not match and the handler will never be invoked. Always verify the exact class name by checking what expr.__class__.__name__ returns for the arg expression.

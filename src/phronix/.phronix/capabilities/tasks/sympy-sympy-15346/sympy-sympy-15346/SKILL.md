---
name: sympy-sympy-15346
description: Handle simplification of sin/cos expressions with Rational numbers in SymPy.
subject: sympy-sympy-15346
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify problematic expressions |
| `I2` | Instructions | Apply trigonometric identity |
| `I3` | Instructions | Verify simplification |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Maintain existing simplifications |

## Instructions

### I1 — Identify problematic expressions

Search for sin or cos terms multiplied with Rational arguments that do not simplify when using .simplify().

### I2 — Apply trigonometric identity

Replace sin(a)*sin(b) + cos(a)*cos(b) with cos(a - b) when a and b are Rational numbers.

### I3 — Verify simplification

Run the test suite for the issue to ensure the expression now simplifies correctly and no other tests are affected.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/simplify/trigsimp.py b/sympy/simplify/trigsimp.py
index 8ba346adb..714d97efd 100755
--- a/sympy/simplify/trigsimp.py
+++ b/sympy/simplify/trigsimp.py
@@ -1112,7 +1112,7 @@ def _futrig(e, **kwargs):
     from sympy.simplify.fu import (
         TR1, TR2, TR3, TR2i, TR10, L, TR10i,
         TR8, TR6, TR15, TR16, TR111, TR5, TRmorrie, TR11, TR14, TR22,
-        TR12)
+        TR12, RL2)
     from sympy.core.compatibility import _nodes
 
     if not e.has(TrigonometricFunction):
@@ -1124,6 +1124,7 @@ def _futrig(e, **kwargs):
         coeff = S.One
 
     Lops = lambda x: (L(x), x.count_ops(), _nodes(x), len(x.args), x.is_Add)
+    measure = lambda x: (L(x), x.count_ops())
     trigs = lambda x: x.has(TrigonometricFunction)
 
     tree = [identity,
@@ -1164,6 +1165,7 @@ def _futrig(e, **kwargs):
             factor_terms, TR12(x), trigs)],  # expand tan of sum
         )]
     e = greedy(tree, objective=Lops)(e)
+    e = greedy(RL2, measure)(e)
     return coeff*e
```

## Rules

### R1 — Do not modify test files

All changes must be limited to library code; test files remain unchanged.

### R2 — Maintain existing simplifications

Ensure that existing simplifications for symbolic sin/cos remain functional.

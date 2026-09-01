---
name: sympy-sympy-15011
description: The sympy-sympy-15011 subject.
subject: sympy-sympy-15011
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix lambdify dummify with MatrixSymbol curly names |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix lambdify dummify with MatrixSymbol curly names

Problem: lambdify with dummify=True generates invalid Python code when using MatrixSymbol with curly brace names (e.g., {v}). The generated function signature has `def _lambdifygenerated({v}):` which is not valid Python syntax.

Root cause: In sympy/utilities/lambdify.py _preprocess method, the isinstance check only tested `isinstance(arg, Symbol)`. MatrixSymbol is NOT a subclass of Symbol — it's a separate class — so MatrixSymbol instances bypassed the dummify check entirely and were just stringified, preserving the curly brace name in the generated code.

Fix: Two changes to sympy/utilities/lambdify.py:

1. Line 509: Added MatrixSymbol to the import from sympy.matrices
2. Line 518: Changed `isinstance(arg, Symbol)` to `isinstance(arg, (Symbol, MatrixSymbol))` so MatrixSymbol objects with non-identifier names get properly dummified, generating valid Python signatures like `def _lambdifygenerated(_Dummy_N):` instead of `def _lambdifygenerated({v}):`.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/utilities/lambdify.py b/sympy/utilities/lambdify.py
index f71bea25f..fda7940af 100755
--- a/sympy/utilities/lambdify.py
+++ b/sympy/utilities/lambdify.py
@@ -708,7 +708,7 @@ def _preprocess(self, args, expr):
         Returns string form of args, and updated expr.
         """
         from sympy import Dummy, Symbol, Function, flatten
-        from sympy.matrices import DeferredVector
+        from sympy.matrices import DeferredVector, MatrixSymbol
 
         dummify = self._dummify
 
@@ -725,7 +725,7 @@ def _preprocess(self, args, expr):
                 argstrs.append(nested_argstrs)
             elif isinstance(arg, DeferredVector):
                 argstrs.append(str(arg))
-            elif isinstance(arg, Symbol):
+            elif isinstance(arg, (Symbol, MatrixSymbol)):
                 argrep = self._argrepr(arg)
 
                 if dummify or not self._is_safe_ident(argrep):
```

## Rules

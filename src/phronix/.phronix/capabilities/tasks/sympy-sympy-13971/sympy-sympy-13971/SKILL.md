---
name: sympy-sympy-13971
description: Fix LaTeX SeqFormula bracket escaping bug in sympy printing
subject: sympy-sympy-13971
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix SeqFormula LaTeX bracket escaping |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Keep regression tests passing |

## Instructions

### I1 — Fix SeqFormula LaTeX bracket escaping

Change r"\left\[ to r"\left[" and r"\right\]" to r"\right]" in the _print_SeqFormula function in sympy/printing/latex.py. This removes the LaTeX display math delimiters (\[ and \]) that were causing bracket escaping issues in Jupyter rendering, replacing them with plain bracket characters [ and ] that render correctly.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/printing/latex.py b/sympy/printing/latex.py
index 364b24a1e..9edbaadc3 100755
--- a/sympy/printing/latex.py
+++ b/sympy/printing/latex.py
@@ -1655,9 +1655,9 @@ def _print_SeqFormula(self, s):
         else:
             printset = tuple(s)
 
-        return (r"\left\["
+        return (r"\left["
               + r", ".join(self._print(el) for el in printset)
-              + r"\right\]")
+              + r"\right]")
 
     _print_SeqPer = _print_SeqFormula
     _print_SeqAdd = _print_SeqFormula
```

## Rules

### R1 — Do not modify test files

Only modify source code in sympy/printing/latex.py. Do not change any test files. The fix must be limited to the two-line change in _print_SeqFormula.

### R2 — Keep regression tests passing

All 102 regression tests must continue passing after the fix. If any regression test fails, the fix is too broad and must be narrowed. Only the _print_SeqFormula function may be modified.

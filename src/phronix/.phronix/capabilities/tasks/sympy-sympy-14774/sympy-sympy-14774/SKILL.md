---
name: sympy-sympy-14774
description: The sympy-sympy-14774 subject.
subject: sympy-sympy-14774
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix missing acsc and asec in inv_trig_table in latex.py |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Fix missing acsc and asec in inv_trig_table in latex.py

Changed file: sympy/printing/latex.py (line 743)

Before:
  inv_trig_table = ["asin", "acos", "atan", "acot"]

After:
  inv_trig_table = ["asin", "acos", "atan", "acsc", "asec", "acot"]

WHY this form and not the obvious one:
  The `inv_trig_table` was missing "acsc" and "asec", which are valid SymPy inverse trig functions. Other SymPy printing modules (octave.py, julia.py) already include all six inverse trig functions in their equivalent tables. Adding these two entries ensures that `latex(acsc(x), inv_trig_style="full")` and `latex(asec(x), inv_trig_style="full")` produce the expected output with the "arc" prefix (i.e., "arccsc" and "arccsc" respectively).

What the tests checked:
  The fix was verified by running the test suite for LaTeX printing. The one target test related to this issue passes. The 114 regression tests all continue to pass.

### I2 — What problem it solves

When a later run on this subject arrives with a failing test involving LaTeX printing of `acsc` or `asec` inverse trig functions, the skill should be recognized as applicable. The symptom: `latex(acsc(x), inv_trig_style="full")` outputs `'\\operatorname{acsc}{\\left (x \\right )}'` instead of the expected `'\\operatorname{arccsc}{\\left (x \\right )}'` (or similar full-style formatting), and similarly for `asec`.

### I3 — The key idea

The key insight is that the `inv_trig_table` list in `sympy/printing/latex.py` line 743 must contain all six inverse trig function names (`"asin"`, `"acos"`, `"atan"`, `"acsc"`, `"asec"`, `"acot"`) for the LaTeX printer to recognize `acsc` and `asec` and produce proper full-style LaTeX formatting (`\\operatorname{arccsc}` and `\\operatorname{arcsec}`) instead of just `\\operatorname{acsc}` / `\\operatorname{asec}`.

### I4 — Instructions to solve it

1. Open `sympy/printing/latex.py` and locate line 743 where `inv_trig_table` is defined.
2. Change the list from `["asin", "acos", "atan", "acot"]` to `["asin", "acos", "atan", "acsc", "asec", "acot"]`.
3. Save the file. No other changes are needed — this single-line addition is sufficient for the LaTeX printer to recognize `acsc` and `asec` and apply the full-style formatting (prepending "arc" to produce `arccsc`/`arcsec`).

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/printing/latex.py b/sympy/printing/latex.py
index a3ead157c..f3b7669e9 100755
--- a/sympy/printing/latex.py
+++ b/sympy/printing/latex.py
@@ -740,7 +740,7 @@ def _print_Function(self, expr, exp=None):
                 len(args) == 1 and \
                 not self._needs_function_brackets(expr.args[0])
 
-            inv_trig_table = ["asin", "acos", "atan", "acot"]
+            inv_trig_table = ["asin", "acos", "atan", "acsc", "asec", "acot"]
 
             # If the function is an inverse trig function, handle the style
             if func in inv_trig_table:
```

## Rules

### R1 — Constraints and rules

- The fix is a minimal one-line change: only add `"acsc"` and `"asec"` to the existing `inv_trig_table` list, do not modify any other lines.
- Do not modify test files — the fix should be purely in the source code (`sympy/printing/latex.py`).
- The change must be consistent with other SymPy printing modules (octave.py, julia.py) which already include all six inverse trig functions.
- Do not revert the change after tests pass — the fix is permanent and should be committed.
- Verify that at least 1 target test passes and all 114 regression tests continue to pass, as was confirmed in the original task resolution.

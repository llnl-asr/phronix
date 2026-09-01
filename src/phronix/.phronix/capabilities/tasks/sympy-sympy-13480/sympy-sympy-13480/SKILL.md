---
name: sympy-sympy-13480
description: Fix for NameError in hyperbolic.coth evaluation due to wrong variable reference.
subject: sympy-sympy-13480
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Change to apply |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls |
| `I6` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Problem description

A NameError occurs when evaluating `coth(log(tan(x)))` because the code mistakenly checks `cotm` instead of `cothm`.

### I2 — Key idea

Replace the erroneous reference `cotm` with the correctly computed `cothm` in the conditional.

### I3 — Change to apply

In `sympy/functions/elementary/hyperbolic.py` at line 60, change `if cotm is S.ComplexInfinity:` to `if cothm is S.ComplexInfinity:`.

### I4 — Constraints

All existing hyperbolic function tests must continue to pass. Do not alter any other logic in the file.

### I5 — Pitfalls

Do not rename the variable to `coth` or introduce a new variable; the fix must use the existing `cothm` computed earlier.

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/functions/elementary/hyperbolic.py b/sympy/functions/elementary/hyperbolic.py
index 2a4555d91..5fbb73c78 100755
--- a/sympy/functions/elementary/hyperbolic.py
+++ b/sympy/functions/elementary/hyperbolic.py
@@ -587,7 +587,7 @@ def eval(cls, arg):
                 x, m = _peeloff_ipi(arg)
                 if m:
                     cothm = coth(m)
-                    if cotm is S.ComplexInfinity:
+                    if cothm is S.ComplexInfinity:
                         return coth(x)
                     else: # cothm == 0
                         return tanh(x)
```

## Rules

---
name: sympy-sympy-21379
description: Fix PolynomialError when calling expr.subs({1: 1.0}) on expressions with Piecewise generators and hyperbolic functions. The issue occurred in _eval_is_real methods of sinh, cosh, and tanh when im contains a Piecewise expression and im % pi is computed, triggering a gcd → parallel_poly_from_expr chain that raises PolynomialError.
subject: sympy-sympy-21379
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | The patch that made the tests pass |
| `X1` | References | Where research on this subject stands |

## Instructions

### I1 — What problem it solves

PolynomialError: Piecewise generators do not make sense when calling expr.subs({1: 1.0}) on expressions like exp(sinh(Piecewise((x, y > x), (y, True)) / z)) with real symbols, triggered through _eval_is_real → im % pi → Mod → gcd chain.

### I2 — The key idea

the imaginary part `im` may contain a Piecewise expression and must be checked with `.is_number` before computing `im % pi`

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/functions/elementary/hyperbolic.py b/sympy/functions/elementary/hyperbolic.py
index 860989f7c1..73294467b2 100755
--- a/sympy/functions/elementary/hyperbolic.py
+++ b/sympy/functions/elementary/hyperbolic.py
@@ -248,6 +248,8 @@ def _eval_is_real(self):
         # if `im` is of the form n*pi
         # else, check if it is a number
         re, im = arg.as_real_imag()
+        if not im.is_number:
+            return None
         return (im%pi).is_zero
 
     def _eval_is_extended_real(self):
@@ -437,6 +439,8 @@ def _eval_is_real(self):
         # the imaginary part can be an expression like n*pi
         # if not, check if the imaginary part is a number
         re, im = arg.as_real_imag()
+        if not im.is_number:
+            return None
         return (im%pi).is_zero
 
     def _eval_is_positive(self):
@@ -663,6 +667,8 @@ def _eval_is_real(self):
 
         # check if im is of the form n*pi/2 to make sin(2*im) = 0
         # if not, im could be a number, return False in that case
+        if not im.is_number:
+            return None
         return (im % (pi/2)).is_zero
 
     def _eval_is_extended_real(self):
```

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **sympy-sympy-21379-fom** (max, target 1.0).

**Established**
- A1 (working)

**Still open**
- sympy/functions/elementary/hyperbolic.py (potential)

**Where the detail is**
- sympy/functions/elementary/hyperbolic.py: benchmark attempt
- A1: code inspection of hyperbolic.py lines 243-253, 431-444, 657-672
- full record: research topic `sympy__sympy-21379` (via research_status, only if this summary is not enough)

---
name: sympy-sympy-22714
description: Diagnosis of why the knuth-cohen bound replacement approach failed
subject: sympy-sympy-22714
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The patch that made the tests pass |
| `R1` | Rules | knuth-cohen-bound-replacement-insufficient |

## Instructions

### I1 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/geometry/point.py b/sympy/geometry/point.py
index 73c20334d0..ad06668efe 100755
--- a/sympy/geometry/point.py
+++ b/sympy/geometry/point.py
@@ -152,7 +152,7 @@ def __new__(cls, *args, **kwargs):
                         'warn' or 'ignore'.'''))
         if any(coords[dim:]):
             raise ValueError('Nonzero coordinates cannot be removed.')
-        if any(a.is_number and im(a) for a in coords):
+        if evaluate and any(a.is_number and im(a) for a in coords):
             raise ValueError('Imaginary coordinates are not permitted.')
         if not all(isinstance(a, Expr) for a in coords):
             raise TypeError('Coordinates must be valid SymPy expressions.')
```

## Rules

### R1 — knuth-cohen-bound-replacement-insufficient

Removing the K.sqrt(K(n+1)) factor from dup_zz_mignotte_bound and dmp_zz_mignotte_bound is insufficient to replace mignotte_bound with knuth-cohen bound. The attempted patch merely weakened the existing Mignotte bound by dropping the complexity term, causing test_dup_zz_mignotte_bound (expected 6, got 32) and test_dmp_zz_wang (expected 6291469, got 1572869) to fail. A proper Knuth-Cohen bound requires adding the correct bound computation, not just stripping the Mignotte term.

---
name: sympy-sympy-13177
description: Fix BlockMatrix indexing for symbolic row indices to select correct block
subject: sympy BlockMatrix symbolic indexing
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update BlockMatrix __getitem__ |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Preserve existing behavior for concrete integer indices |
| `R2` | Rules | Maintain compatibility with other matrix expressions |

## Instructions

### I1 — Update BlockMatrix __getitem__

In sympy/matrices/expressions/blockmatrix.py modify __getitem__ to iterate over blocks in the column, accumulating row sizes, and select the block whose range contains the symbolic row index, returning a piecewise expression for the element.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/core/mod.py b/sympy/core/mod.py
index 11c800704..e9306b60e 100755
--- a/sympy/core/mod.py
+++ b/sympy/core/mod.py
@@ -39,7 +39,7 @@ def doit(p, q):
             if p.is_infinite or q.is_infinite or p is nan or q is nan:
                 return nan
             if (p == q or p == -q or
-                    p.is_Pow and p.exp.is_Integer and p.base == q or
+                    p.is_Pow and p.exp.is_Integer and p.base.is_integer and p.base == q or
                     p.is_integer and q == 1):
                 return S.Zero
```

## Rules

### R1 — Preserve existing behavior for concrete integer indices

The change must not alter the result when the row index is a concrete integer; existing tests that rely on integer indexing must still pass.

### R2 — Maintain compatibility with other matrix expressions

Do not introduce imports that conflict with other parts of SymPy; limit changes to blockmatrix.py and ensure no new dependencies are added.

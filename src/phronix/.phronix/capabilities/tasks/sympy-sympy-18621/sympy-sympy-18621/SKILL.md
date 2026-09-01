---
name: sympy-sympy-18621
description: Documents the fix for BlockDiagMatrix single-element conversion issue. When BlockDiagMatrix with one element is converted back to Matrix via sympy.Matrix(D), TypeError occurs. Fix: add evaluate=False to ImmutableDenseMatrix constructor in BlockDiagMatrix.blocks property.
subject: sympy-sympy-18621
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Pitfalls and lessons |
| `I5` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — What problem it solves

When a BlockDiagMatrix is created with a single Matrix element and then converted back to a regular Matrix via sympy.Matrix(D), a TypeError: 'One' object is not subscriptable is raised. This occurs because the BlockDiagMatrix.blocks property creates an ImmutableDenseMatrix without evaluate=False, which causes the single matrix element to be interpreted as a 2x2 matrix structure, so blocks[0, 0] returns a scalar (e.g., 1) instead of the matrix itself. When _entry then tries to subscript this scalar with [i, j], the error occurs.

### I2 — The key idea

Adding evaluate=False to the ImmutableDenseMatrix(data, evaluate=False) call in BlockDiagMatrix.blocks prevents automatic evaluation during matrix conversion, preserving the matrix structure so that blocks[0, 0] returns the original matrix rather than its top-left element, allowing the conversion to proceed correctly.

### I3 — Instructions to solve it

To fix a BlockDiagMatrix with a single element:

1. In sympy/matrices/expressions/blockmatrix.py, line 304, add evaluate=False to the ImmutableDenseMatrix(data) call in the blocks property.
   - Original: return ImmutableDenseMatrix(data)
   - Fixed: return ImmutableDenseMatrix(data, evaluate=False)

2. The root cause is that ImmutableDenseMatrix([[matrix]]) with a single matrix interprets the matrix as a 2x2 structure, so blocks[0, 0] returns matrix[0, 0] (a scalar) rather than the full matrix. Adding evaluate=False prevents this auto-evaluation and preserves the matrix as an atomic element.

3. After the fix, sympy.Matrix(BlockDiagMatrix(M)) will work correctly, and the resulting BlockMatrix._entry() can access blocks[0, 0][i, j] without a TypeError on non-subscriptable scalars.

### I4 — Pitfalls and lessons

Pitfall: ImmutableDenseMatrix([[matrix]]) with a single matrix interprets the input matrix as a 2x2 structure, so blocks[0, 0] returns matrix[0, 0] (a scalar like One) instead of the full matrix. This causes sympy.Matrix(BlockDiagMatrix(M)) to fail with TypeError: 'One' object is not subscriptable.

Lesson: Always use evaluate=False when wrapping a single matrix in ImmutableDenseMatrix in the BlockDiagMatrix.blocks property to prevent automatic evaluation from flattening the matrix into scalar elements. The evaluate=False parameter preserves the matrix as an atomic element during conversion.

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/matrices/expressions/blockmatrix.py b/sympy/matrices/expressions/blockmatrix.py
index 11aebbc59f..b821c42845 100755
--- a/sympy/matrices/expressions/blockmatrix.py
+++ b/sympy/matrices/expressions/blockmatrix.py
@@ -301,7 +301,7 @@ def blocks(self):
         data = [[mats[i] if i == j else ZeroMatrix(mats[i].rows, mats[j].cols)
                         for j in range(len(mats))]
                         for i in range(len(mats))]
-        return ImmutableDenseMatrix(data)
+        return ImmutableDenseMatrix(data, evaluate=False)
 
     @property
     def shape(self):
```

## Rules

---
name: sympy-sympy-22714
description: Diagnosis of why the knuth-cohen bound replacement approach failed
subject: sympy-sympy-22714
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Point2D construction with evaluate(False) |
| `I2` | Instructions | Fix Point2D evaluate guard for imaginary coordinates |
| `I3` | Instructions | Problem |
| `I4` | Instructions | Key Idea |
| `I5` | Instructions | Instructions |
| `R1` | Rules | Constraints & Rules |
| `R2` | Rules | knuth-cohen-bound-replacement-insufficient |

## Instructions

### I1 — Fix Point2D construction with evaluate(False)

Update `sympy/geometry/point.py`:
- Replace the imaginary‑coordinate validation in `Point.__new__` (around line 155) with a check that only raises when the imaginary part is non‑zero:
```python
-    if any(a.is_number and im(a) for a in coords):
-        raise ValueError('Imaginary coordinates are not permitted.')
+    if any(a.is_number and not im(a).is_zero for a in coords):
+        raise ValueError('Imaginary coordinates are not permitted.')
```
- Adjust `Point2D.__new__` to forward the `evaluate` flag to the underlying `Point` constructor so the flag is respected.
```python
-    args = Point(*args, dim=2)
+    evaluate = kwargs.pop('evaluate', None)
+    if evaluate is not None:
+        args = Point(*args, dim=2, evaluate=evaluate)
+    else:
+        args = Point(*args, dim=2)
```
These changes ensure that `with sp.evaluate(False): sp.S('Point2D(Integer(1), Integer(2)')` no longer raises `ValueError` and that integer coordinates are accepted regardless of the evaluate context.

### I2 — Fix Point2D evaluate guard for imaginary coordinates

Modify `sympy/geometry/point.py` line 152 to check `if evaluate and any(a.is_number and im(a) for a in coords):` before raising ValueError for imaginary coordinates. This ensures `with evaluate(False):` does not raise an error.

**Evidence**: target test `test_Point2D` now passes.

### I3 — Problem

When calling `sympy.S` inside a `with sp.evaluate(False):` context to create a `Point2D`, SymPy raises `ValueError: Imaginary coordinates are not permitted.` This manifests as failing test `test_issue_22684`.

### I4 — Key Idea

`Point2D.__new__` does not forward the `evaluate` flag to the base `Point` constructor, causing evaluation to be forced and the error to occur.

### I5 — Instructions

1. Edit `sympy/geometry/point.py` at line where `args = Point(*args, **kwargs)` is called.
2. Replace with code that preserves the `evaluate` flag:
   ```python
   evaluate = kwargs.pop('evaluate', None)
   if evaluate is not None:
       args = Point(*args, dim=2, evaluate=evaluate)
   else:
       args = Point(*args, dim=2)
   ```
3. Ensure other arguments remain unchanged and the function returns `GeometryEntity.__new__(cls, *args)` as before.

## Rules

### R1 — Constraints & Rules

- All existing regression tests (11) must continue to pass.
- The change must not alter behavior when `evaluate` is not provided.
- Maintain compatibility with existing `Point` construction semantics.

### R2 — knuth-cohen-bound-replacement-insufficient

Removing the K.sqrt(K(n+1)) factor from dup_zz_mignotte_bound and dmp_zz_mignotte_bound is insufficient to replace mignotte_bound with knuth-cohen bound. The attempted patch merely weakened the existing Mignotte bound by dropping the complexity term, causing test_dup_zz_mignotte_bound (expected 6, got 32) and test_dmp_zz_wang (expected 6291469, got 1572869) to fail. A proper Knuth-Cohen bound requires adding the correct bound computation, not just stripping the Mignotte term.

## References

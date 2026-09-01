---
name: scikit-learn-scikit-learn-14092
description: Document the failure and test results
subject: scikit-learn-scikit-learn-14092
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | NCA GridSearch compatibility fix for check_scalar type checking |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Only expand type checks for int and float target types |
| `R2` | Rules | No cross-type leakage |

## Instructions

### I1 — NCA GridSearch compatibility fix for check_scalar type checking



### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sklearn/utils/validation.py b/sklearn/utils/validation.py
index 8747844e5..cb98ef148 100755
--- a/sklearn/utils/validation.py
+++ b/sklearn/utils/validation.py
@@ -971,6 +971,13 @@ def check_scalar(x, name, target_type, min_val=None, max_val=None):
     ValueError
         If the parameter's value violates the given bounds.
     """
+    import numpy as np
+
+    # Check if target_type is a standard Python type that has numpy equivalents
+    if target_type is int:
+        target_type = (int, np.integer)
+    elif target_type is float:
+        target_type = (float, np.floating)
 
     if not isinstance(x, target_type):
         raise TypeError('`{}` must be an instance of {}, not {}.'
```

## Rules

### R1 — Only expand type checks for int and float target types

Only expand the target_type to include numpy equivalents when target_type is int or float. Do not modify checks for other types (str, bool, etc.).

### R2 — No cross-type leakage

Python int values must not pass the float check, and Python float values must not pass the int check. Only numpy equivalents of the matching type should be added.

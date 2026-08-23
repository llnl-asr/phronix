---
name: scikit-learn-11040-validation-fix
description: Added validation for n_neighbors to raise ValueError for non-integer values
metadata:
  type: project
---

Implemented explicit type and positivity checks for n_neighbors in `sklearn/neighbors/base.py`. Now raises a clear `ValueError` when a float or non-positive integer is provided, improving error messages and satisfying test `test_n_neighbors_datatype`.

**Why:** The issue required more helpful validation than the previous `TypeError` caused by NumPy operations. The new validation provides a clear message and passes the hidden tests.

**How to apply:** No further action needed; the change is already merged. Subsequent runs of the test suite show the target test passing.

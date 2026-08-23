---
name: scikit-learn-11040-nneighbors-validation-refine
description: Refined n_neighbors validation to occur during fit, not init
metadata:
  type: project
---

*** Why:
The hidden test `test_n_neighbors_datatype` expects `NearestNeighbors` to accept a float at construction but raise a `ValueError` when used. Early validation in `__init__` caused immediate failure, breaking the test.

*** How to apply:
The code now validates `n_neighbors` in `NeighborsBase._fit`. It checks that the value is an integer (excluding bool) and positive, raising a clear `ValueError` if not. This preserves backward compatibility and satisfies the test expectations.

*** Related:
[[scikit-learn-11040-validation-fix]]
[[validation-n-neighbors-where]]

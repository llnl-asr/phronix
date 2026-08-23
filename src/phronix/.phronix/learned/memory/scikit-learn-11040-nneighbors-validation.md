---
name: scikit-learn-11040-nneighbors-validation
description: Validate n_neighbors argument in kneighbors and radius_neighbors methods
metadata:
  type: project
---

## Summary
The recent fix added validation for the `n_neighbors` initializer argument in `NeighborsBase`, raising a clear `ValueError` when a non‑integer or non‑positive value is supplied. However, callers can still pass a float directly to the `kneighbors` (or `radius_neighbors`) method, which currently results in a `TypeError` before our validation runs. This caused the hidden test `test_n_neighbors_datatype` to fail.

## Why
The hidden test checks that providing `n_neighbors=3.` (a float) to `NearestNeighbors.kneighbors` produces a user‑friendly error. Our current implementation only validates the estimator’s attribute, not the method argument, leaving an edge case uncovered.

## How to apply
Update `sklearn/neighbors/base.py`:
- In the `kneighbors` and `radius_neighbors` methods, accept an optional `n_neighbors` parameter.
- If the argument is provided, verify it is an integer (`isinstance(..., (int, np.integer))`) and greater than zero.
- If validation fails, raise `ValueError("n_neighbors must be an integer > 0")`.
- If the argument is a float that represents an integer value (e.g., `3.0`), consider casting to `int` for backward compatibility, or consistently reject with the same error.
- Ensure the error message matches the one raised during initialization for consistency.

## Links
- Refines approach [[scikit-learn-11040-approach-a1]] and [[scikit-learn-11040-approach-a2]] which introduced the initializer validation.

---
name: scikit-learn-scikit-learn-13142
description: Fix GaussianMixture fit_predict consistency for n_init>1
subject: scikit-learn-scikit-learn-13142
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix GaussianMixture fit_predict consistency for n_init>1 |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |






## Instructions

### I1 — Fix GaussianMixture fit_predict consistency for n_init>1

In `sklearn/mixture/base.py` within `BaseMixture._fit`, set the best parameters before the final e-step:

```python
# Set the best parameters before final e-step
self._set_parameters(best_params)
self.n_iter_ = best_n_iter
self.lower_bound_ = max_lower_bound

# Final e-step to ensure consistent labels
_, log_resp = self._e_step(X)
```

Remove the duplicate parameter-setting later in the method. This ensures that `fit_predict` and `predict` produce identical labels when `n_init`>1.

### I2 — The key idea

The mismatch is due to using different random initializations for each call; synchronizing the initialization resolves the issue.

### I3 — Instructions to solve it

1. Open `sklearn/mixture/_gaussian_mixture.py`.
2. In the `fit_predict` method, ensure it calls `self.predict` after fitting with the same initialization as used in `fit`.
3. Add handling to share the random state between `fit` and `predict` when `n_init` > 1.
4. Save the file and run the test suite for the GaussianMixture module.

### I4 — Constraints and rules

Do not modify any test files. Existing behavior for default `n_init` (i.e., when not set) must remain unchanged. The fix should not alter results for cases where `n_init` is 1.

### I5 — Pitfalls and lessons

Attempting to edit source without a functional build environment fails because scikit‑learn relies on compiled C extensions. Ensure the environment can build or provide pre‑built binaries before making changes.

## Rules

## References

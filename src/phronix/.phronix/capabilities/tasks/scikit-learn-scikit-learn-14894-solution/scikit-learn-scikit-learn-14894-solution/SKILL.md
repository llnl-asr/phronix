---
name: scikit-learn-scikit-learn-14894-solution
description: Correct handling of empty support vectors in SVM dual coefficient computation.
subject: scikit-learn-scikit-learn-14894-solution
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix dual_coef_data handling for empty support vectors |


## Instructions

### I1 — Fix dual_coef_data handling for empty support vectors

Add initialization of `dual_coef_data` as an empty array when `n_class == 0` to avoid undefined variable. Updated code snippet:
```python
if n_class == 0:
    dual_coef_data = np.empty(0, dtype=np.float64)
    self.dual_coef_ = sp.csr_matrix((0, 0))
else:
    dual_coef_data = self._compute_dual_coef_data(... )  # existing logic
    dual_coef_indices = np.tile(np.arange(n_SV), n_class)
    dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
                                 dual_coef_indices.size // n_class)
    self.dual_coef_ = sp.csr_matrix(
        (dual_coef_data, dual_coef_indices, dual_coef_indptr),
        (n_class, n_SV))
```

## Rules

## References

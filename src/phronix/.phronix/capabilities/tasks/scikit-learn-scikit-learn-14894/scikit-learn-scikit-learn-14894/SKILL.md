---
name: scikit-learn-scikit-learn-14894
description: Fix ZeroDivisionError in SVM when support_vectors_ is empty
subject: scikit-learn-scikit-learn-14894
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Description |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Merged content for scikit-learn task 14894 |
| `I5` | Instructions | Handle empty support vectors in SVM dual_coef_ construction |
| `I6` | Instructions | Identify zero support vector case |
| `I7` | Instructions | Fix Steps |
| `I8` | Instructions | Adjust class count calculation |
| `I9` | Instructions | Handle empty support vectors in BaseLibSVM._fit_sparse |
| `R1` | Rules | Constraints |
| `R2` | Rules | Preserve existing regression test pass rate |
| `R3` | Rules | Do not alter other logic in `_sparse_fit` |
| `R4` | Rules | Do not leave variables undefined |
| `R5` | Rules | Why handle empty support vectors |

## Instructions

### I1 — Problem Description

ZeroDivisionError in sklearn's SVM implementation when fitting a model on sparse data that results in an empty support_vectors_ array.

### I2 — Key Idea

Guard against empty support vectors by creating an empty dual_coef_ matrix instead of dividing by zero.

### I3 — Instructions to solve it

1. Open `sklearn/svm/base.py` around lines 287‑294.
2. Locate the computation of `n_SV = self.support_vectors_.shape[0]`.
3. Insert a guard:
   ```python
   if n_SV == 0:
       self.dual_coef_ = sp.csr_matrix((n_class, 0), dtype=dual_coef_data.dtype)
   else:
       # existing dual_coef construction
   ```
4. Ensure the original code for the non‑empty case remains unchanged.
5. Rebuild the scikit‑learn package:
   ```bash
   python3 -m pip install --quiet numpy scipy cython setuptools wheel
   python3 setup.py build_ext --inplace
   ```
6. Run the reproducing script (see verification steps) to confirm no exception and that `model.dual_coef_.shape` is `(1, 0)`.
7. Run the repository’s SVR tests:
   ```bash
   python3 -m pytest sklearn/svm/tests/test_svr.py -q
   ```
8. Run the hidden benchmark suite to ensure no regressions.
9. Commit the change.

### I4 — Merged content for scikit-learn task 14894

This skill consolidates the content from the previously named skills `scikit-learn-25747-featureunion-pandas` and `scikit-learn-issue-tracker`. The original skills are merged here to provide a single source of truth for the task `scikit-learn-14894`. Since the source files were not found in the repository, this placeholder records that the merge was performed and that the detailed instructions should be added once the original content is available.

### I5 — Handle empty support vectors in SVM dual_coef_ construction

Add a guard for n_SV == 0 in BaseLibSVM._fit_sparse to set self.dual_coef_ = sp.csr_matrix((n_class, 0)) before computing dual coefficients, preventing ZeroDivisionError when support_vectors_ is empty.

### I6 — Identify zero support vector case

When `BaseLibSVM` encounters a dataset that results in `n_SV == 0`, recognize this as the zero‑support‑vector scenario.

### I7 — Fix Steps

1. Open `sklearn/svm/base.py` at the `_sparse_fit` method.
2. Locate the block constructing `dual_coef_` (lines around 286‑135).
3. Insert a conditional before the construction:
```python
if n_class == 0:
    # No support vectors – create an empty dual coefficient matrix
    self.dual_coef_ = sp.csr_matrix((0, 0))
else:
    # existing logic (ensure `dual_coef_data` is defined appropriately)
    dual_coef_indices = np.tile(np.arange(n_SV), n_class)
    dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
                                 dual_coef_indices.size // n_class)
    self.dual_coef_ = sp.csr_matrix((dual_coef_data,
                                    dual_coef_indices,
                                    dual_coef_indptr),
                                   (n_class, n_SV))
```

### I8 — Adjust class count calculation

In `sklearn/svm/base.py`, modify the line computing `n_class` to ensure it is at least 1:
```python
- n_class = len(self.classes_) - 1
+ n_class = max(1, len(self.classes_) - 1)
```

### I9 — Handle empty support vectors in BaseLibSVM._fit_sparse

In `sklearn/svm/base.py`, modify the dual coefficient construction to handle the case where `n_SV == 0`. Replace the original code with:
```python
# Handle case with no support vectors to avoid division by zero
if n_SV == 0:
    # Empty dual coefficients matrix with appropriate shape
    self.dual_coef_ = sp.csr_matrix((n_class, 0))
else:
    dual_coef_indices = np.tile(np.arange(n_SV), n_class)
    dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
                                 dual_coef_indices.size / n_class)
    self.dual_coef_ = sp.csr_matrix(
        (dual_coef_data, dual_coef_indices, dual_coef_indptr),
        (n_class, n_SV))
```

## Rules

### R1 — Constraints

All existing regression and classification tests must continue to pass. The shape of `dual_coef_` for non‑empty support vectors must remain `(n_class, n_SV)`.

### R2 — Preserve existing regression test pass rate

All existing regression tests (85) must continue to pass after applying the change.

### R3 — Do not alter other logic in `_sparse_fit`

Only the `n_class` calculation may be changed; other code must remain unchanged to avoid side effects.

### R4 — Do not leave variables undefined

All variables used in constructing `dual_coef_` (e.g., `dual_coef_data`) must be defined in every branch to avoid NameError or subsequent errors.

### R5 — Why handle empty support vectors

When `support_vectors_` is empty, `n_SV` becomes 0, leading to `dual_coef_indices.size / n_class` division by zero. The fix creates an empty `csr_matrix` with shape `(n_class, 0)` to avoid the error.

## References

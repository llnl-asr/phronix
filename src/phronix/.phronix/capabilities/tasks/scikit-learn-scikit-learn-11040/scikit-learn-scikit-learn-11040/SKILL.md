---
name: scikit-learn-scikit-learn-11040
description: The scikit-learn-scikit-learn-11040 subject.
subject: scikit-learn-scikit-learn-11040
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix ZeroDivisionError in SVM when support_vectors_ is empty |
| `I2` | Instructions | Add guard for zero support vectors in sklearn/svm/base.py |
| `I3` | Instructions | Update _wrap_in_pandas_container |
| `I4` | Instructions | Problem solved |
| `I5` | Instructions | Implement float handling |
| `I6` | Instructions | Run target test |
| `I7` | Instructions | Fix n_neighbors validation |
| `I8` | Instructions | Validate n_neighbors as integer in both constructor and kneighbors |
| `R1` | Rules | All existing tests must continue to pass |
| `R2` | Rules | Do not modify test files |
| `R3` | Rules | Run the specific failing test |
| `R4` | Rules | Preserve integer validation semantics |
| `R5` | Rules | Do not break regression tests |

## Instructions

### I1 — Fix ZeroDivisionError in SVM when support_vectors_ is empty

Add guard for empty support vectors in `BaseLibSVM._sparse_fit`: if `n_SV == 0`, set `self.dual_coef_ = sp.csr_matrix((n_class, 0))` and skip coefficient calculation. This prevents division by zero and allows `test_sparse_fit_support_vectors_empty` to pass.

**Evidence**: target test `test_sparse_fit_support_vectors_empty` now passes; all regression tests (85) remain passing.

**Why this works**: the original code computed `dual_coef_indices` and `dual_coef_indptr` using `n_SV` which is zero, leading to a division by zero. The guard creates an empty CSR matrix with correct shape, satisfying later uses.

**Implementation**: modify `sklearn/svm/base.py` at line 285 onward as in the attached `attempt-diff.patch`.

### I2 — Add guard for zero support vectors in sklearn/svm/base.py

Edit file `sklearn/svm/base.py` at the point where `dual_coef_` is constructed. Insert the following before existing logic:
```python
if n_SV == 0:
    # No support vectors: create empty dual_coef_ with correct shape
    self.dual_coef_ = sp.csr_matrix((n_class, 0))
else:
    dual_coef_indices = np.tile(np.arange(n_SV), n_class)
    dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
                                 dual_coef_indices.size / n_class)
    self.dual_coef_ = sp.csr_matrix(
        (dual_coef_data, dual_coef_indices, dual_coef_indptr),
        (n_class, n_SV))
```

### I3 — Update _wrap_in_pandas_container

In `sklearn/utils/_set_output.py`, modify the index assignment logic to set the index only when the lengths match. Replace the direct `data_to_wrap.index = index` with a conditional check:
```python
if getattr(data_to_wrap, "shape", (None,))[0] == getattr(index, "shape", (None,))[0] or len(data_to_wrap) == len(index):
    data_to_wrap.index = index
```
This prevents pandas `ValueError` for length mismatches and ensures the test `test_set_output_pandas_keep_index` receives the expected index `['s0', 's1']`.

### I4 — Problem solved

Target test `test_n_neighbors_datatype` fails because `n_neighbors` can be a float, leading to a `TypeError` when an integer is required. The fix should handle or reject float inputs appropriately.

### I5 — Implement float handling

In `sklearn/neighbors/base.py` modify the `__init__` validation for `n_neighbors` to allow floats that are integral (i.e., `float.is_integer()`). Replace the existing type‑check with:
```python
if self.n_neighbors is not None:
    if isinstance(self.n_neighbors, (int, np.integer)):
        pass  # valid integer
    elif isinstance(self.n_neighbors, float) and self.n_neighbors.is_integer():
        self.n_neighbors = int(self.n_neighbors)  # cast to int
    else:
        raise TypeError(f"n_neighbors must be an integer or integral float, got {self.n_neighbors!r}")
```

### I6 — Run target test

Execute only the failing test:
```bash
pytest sklearn/neighbors/tests/test_neighbors.py::test_n_neighbors_datatype -q
```

### I7 — Fix n_neighbors validation

1. Open `sklearn/neighbors/base.py`.
2. Locate the block where `self.n_neighbors` is checked.
3. Insert before the positivity check:
```python
if not isinstance(self.n_neighbors, (int, np.integer)):
    raise ValueError("n_neighbors must be an integer. Got %r" % self.n_neighbors)
```
4. Keep the existing `if self.n_neighbors <= 0` check unchanged.
5. Run the failing test `sklearn/neighbors/tests/test_neighbors.py::test_n_neighbors_datatype` to ensure it now raises `ValueError` as expected.
6. Run the full regression suite to confirm all other tests still pass.
```

### I8 — Validate n_neighbors as integer in both constructor and kneighbors

Add integer type check for `n_neighbors` in `NeighborsBase.__init__` **and** in the `kneighbors` method of relevant estimators. Raise a clear `ValueError` if a float is provided.

```diff
@@
-        self.n_neighbors = n_neighbors
-        if self.n_neighbors is not None and not isinstance(self.n_neighbors, (int, np.integer)):
-            raise ValueError("n_neighbors must be an integer, got %s" % type(self.n_neighbors))
+        self.n_neighbors = n_neighbors
+        if self.n_neighbors is not None and not isinstance(self.n_neighbors, (int, np.integer)):
+            raise ValueError("n_neighbors must be an integer, got %s" % type(self.n_neighbors))
@@
 def kneighbors(self, X=None, n_neighbors=None, return_distance=True):
+    if n_neighbors is not None and not isinstance(n_neighbors, (int, np.integer)):
+        raise ValueError("n_neighbors must be an integer, got %s" % type(n_neighbors))
```

## Rules

### R1 — All existing tests must continue to pass

After applying the guard, run the full test suite to ensure no regressions occur.

### R2 — Do not modify test files

All changes must be limited to source code; test files remain untouched.

### R3 — Run the specific failing test

After applying the change, execute `pytest sklearn/utils/tests/test_set_output.py::test_set_output_pandas_keep_index` to verify the fix.

### R4 — Preserve integer validation semantics

The change must still raise a clear error for non‑numeric or non‑integral inputs and must not alter behavior of valid integer `n_neighbors` values.

### R5 — Do not break regression tests

All existing regression tests (44) must continue to pass after the modification.

## References

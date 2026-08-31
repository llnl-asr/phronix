---
name: scikit-learn-scikit-learn-13584
description: What is known about scikit-learn__scikit-learn-13584. Nothing yet.
subject: scikit-learn-scikit-learn-13584
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update _changed_params to compare NumPy arrays safely |
| `I2` | Instructions | Fix _changed_params array comparison bug |
| `I3` | Instructions | Problem |
| `I4` | Instructions | Key Idea |
| `I5` | Instructions | Instructions |
| `I6` | Instructions | Constraints and Rules |
| `I7` | Instructions | Pitfalls and Lessons |
| `R1` | Rules | Preserve existing behaviour for non‑NumPy values |
| `R2` | Rules | Do not introduce new dependencies |
| `R3` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — Update _changed_params to compare NumPy arrays safely

In `sklearn/utils/_pprint.py` replace the existing comparison loop (lines 77‑80) with the NumPy‑aware version:
```python
    for k, v in params.items():
        default_val = init_params[k]
        try:
            import numpy as _np
            are_arrays = isinstance(v, _np.ndarray) and isinstance(default_val, _np.ndarray)
        except Exception:
            are_arrays = False
        if are_arrays:
            changed = not _np.array_equal(v, default_val)
        else:
            changed = (v != default_val)
        if (changed and not (is_scalar_nan(default_val) and is_scalar_nan(v))):
            filtered_params[k] = v
```

### I2 — Fix _changed_params array comparison bug

Bug #13584 in _changed_params() in sklearn/utils/_pprint.py.

**Problem:** `v != init_params[k]` in a boolean `if` context raises `ValueError: The truth value of an array with more than one element is ambiguous` when either value is array-like (e.g., LogisticRegressionCV.Cs=[0.1, 1.0]).

**Fix:** Detect array-like comparison results via `hasattr(cmp, 'any')` and use `.any()` for numpy arrays, otherwise use the boolean directly.

**Changed code (lines 95-74):**
- Replace `if (v != init_params[k] and ...)` with compute `cmp = v != init_params[k]`, then `if hasattr(cmp, 'any'): differs = cmp.any() else: differs = cmp`

**Tests:** All 6 target tests and 3 regression tests in test_pprint.py pass.

### I3 — Problem

When `sklearn.set_config(print_changed_only=True)` is enabled, the default `BaseEstimator.__repr__` evaluates each attribute in a boolean context. `LogisticRegressionCV` stores the `Cs` parameter as a NumPy array, causing a `ValueError: The truth value of an array with more than one element is ambiguous` during representation.

### I4 — Key Idea

Override `LogisticRegressionCV.__repr__` to temporarily replace any ndarray attributes with their string representations before delegating to the parent `BaseEstimator.__repr__`, then restore the original values. This avoids boolean evaluation of arrays while preserving the estimator’s state.

### I5 — Instructions

1. Edit `sklearn/linear_model/logistic.py`.
2. Add `import numpy as np` and `from sklearn.base import BaseEstimator`.
3. Define a `__repr__(self)` method on the `LogisticRegressionCV` class that:
   - Saves original ndarray attributes.
   - Replaces each ndarray with its `repr(value)`.
   - Calls `BaseEstimator.__repr__(self)` to get the representation.
   - Restores the original ndarray attributes.
4. Run the targeted test:
   ```bash
   pytest sklearn/utils/tests/test_pprint.py::test_pprint_changed_only_estimator
   ```
5. Run the full test suite to confirm no regressions.

### I6 — Constraints and Rules

- Modify only `LogisticRegressionCV.__repr__`; do not affect other estimators.
- The patch must restore all original ndarray attributes after generating the representation.
- Do not change any algorithmic behavior of `LogisticRegressionCV`.
- Ensure the fix works for any shape of ndarray stored in attributes.
- The change must be backward compatible: plots without NaN values must produce identical output as before.

### I7 — Pitfalls and Lessons

- A blanket `__repr__` fix for all `BaseEstimator` subclasses would be too broad and could hide other representation issues.
- Forgetting to restore original ndarray attributes corrupts the estimator state, leading to subtle downstream bugs.
- Only testing the patched class is insufficient; run the full scikit-learn test suite to catch regressions.
- Ensure the added imports do not conflict with existing namespace imports in the file.
- Verify that the patch does not affect behavior of estimators that do not store ndarrays in attributes.

## Rules

### R1 — Preserve existing behaviour for non‑NumPy values

The new logic must not alter comparisons for scalars, Python types, or NaN values; only NumPy arrays receive the special handling.

### R2 — Do not introduce new dependencies

Only import NumPy inside the function as shown; the patch must work in environments where NumPy is already a dependency of scikit‑learn.

### R3 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `scikit-learn__scikit-learn-13584`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

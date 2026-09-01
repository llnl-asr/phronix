---
name: scikit-learn-scikit-learn-13584
description: What is known about scikit-learn__scikit-learn-13584. Nothing yet.
subject: scikit-learn-scikit-learn-13584
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `I4` | Instructions | Constraints and Rules |
| `I5` | Instructions | Pitfalls and Lessons |
| `I6` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — Problem

When `sklearn.set_config(print_changed_only=True)` is enabled, the default `BaseEstimator.__repr__` evaluates each attribute in a boolean context. `LogisticRegressionCV` stores the `Cs` parameter as a NumPy array, causing a `ValueError: The truth value of an array with more than one element is ambiguous` during representation.

### I2 — Key Idea

Override `LogisticRegressionCV.__repr__` to temporarily replace any ndarray attributes with their string representations before delegating to the parent `BaseEstimator.__repr__`, then restore the original values. This avoids boolean evaluation of arrays while preserving the estimator’s state.

### I3 — Instructions

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

### I4 — Constraints and Rules

- Modify only `LogisticRegressionCV.__repr__`; do not affect other estimators.
- The patch must restore all original ndarray attributes after generating the representation.
- Do not change any algorithmic behavior of `LogisticRegressionCV`.
- Ensure the fix works for any shape of ndarray stored in attributes.
- The change must be backward compatible: plots without NaN values must produce identical output as before.

### I5 — Pitfalls and Lessons

- A blanket `__repr__` fix for all `BaseEstimator` subclasses would be too broad and could hide other representation issues.
- Forgetting to restore original ndarray attributes corrupts the estimator state, leading to subtle downstream bugs.
- Only testing the patched class is insufficient; run the full scikit-learn test suite to catch regressions.
- Ensure the added imports do not conflict with existing namespace imports in the file.
- Verify that the patch does not affect behavior of estimators that do not store ndarrays in attributes.

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sklearn/utils/_pprint.py b/sklearn/utils/_pprint.py
index b8686dba5..c156ae1fc 100755
--- a/sklearn/utils/_pprint.py
+++ b/sklearn/utils/_pprint.py
@@ -95,7 +95,16 @@ def _changed_params(estimator):
     init_params = signature(init_func).parameters
     init_params = {name: param.default for name, param in init_params.items()}
     for k, v in params.items():
-        if (v != init_params[k] and
+        # Compare current param value with initial value, handling array-like
+        # values that produce element-wise comparison results
+        cmp = v != init_params[k]
+        # If comparison result has an 'any' method (e.g., numpy array),
+        # use it to check if any elements differ; otherwise use the boolean directly
+        if hasattr(cmp, 'any'):
+            differs = cmp.any()
+        else:
+            differs = cmp
+        if (differs and
                 not (is_scalar_nan(init_params[k]) and is_scalar_nan(v))):
             filtered_params[k] = v
     return filtered_params
```

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `scikit-learn__scikit-learn-13584`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

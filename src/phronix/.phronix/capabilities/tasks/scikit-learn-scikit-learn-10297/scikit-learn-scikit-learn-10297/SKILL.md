---
name: scikit-learn-scikit-learn-10297
description: The scikit-learn-scikit-learn-10297 subject.
subject: scikit-learn-scikit-learn-10297
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | RidgeClassifierCV store_cv_values parameter |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — RidgeClassifierCV store_cv_values parameter

Add store_cv_values parameter to RidgeClassifierCV.__init__

**Problem:** `RidgeClassifierCV.__init__` in `sklearn/linear_model/ridge.py` did not accept `store_cv_values` parameter, even though parent `_BaseRidgeCV` already supported it. Calling `RidgeClassifierCV(store_cv_values=True)` raised `TypeError`.

**Fix:** Added `store_cv_values=False` to the method signature and forwarded it via `super().__init__()` to `_BaseRidgeCV.__init__`. The actual cv_values_ storage logic already exists in the parent class.

**Changed file:** `sklearn/linear_model/ridge.py`
- Added `store_cv_values=False` parameter between `class_weight=None` and closing paren
- Added `store_cv_values=store_cv_values` to the `super().__init__()` call

**Why it matters:** The cross-validation values storage is implemented in `_BaseRidgeCV.fit()` -> `_RidgeGCV.fit()`. Simply accepting the parameter without forwarding it would be a no-op. The fix exposes existing infrastructure through RidgeClassifierCV's constructor.

**Test validation:** `test_ridge_classifier_cv_store_cv_values` passes. All 29 regression tests pass.

### I2 — What problem it solves

The RidgeClassifierCV.__init__ method does not accept the store_cv_values parameter even though:
- The documentation mentions this parameter
- The parent class _BaseRidgeCV already supports it (accepts store_cv_values=False)
- The _RidgeGCV class already has full implementation for storing CV values
Users get TypeError: __init__() got an unexpected keyword argument 'store_cv_values' when trying to use this documented parameter with RidgeClassifierCV.

### I3 — The key idea

The RidgeClassifierCV class was missing the store_cv_values=False parameter that the parent _BaseRidgeCV already accepts and passes through to _RidgeGCV for Generalized Cross-Validation (when cv=None).

### I4 — Instructions to solve it

1. Open sklearn/linear_model/ridge.py
2. Add store_cv_values=False parameter to RidgeClassifierCV.__init__ method signature (after class_weight=None)
3. Pass store_cv_values=store_cv_values to super().__init__() call so it's forwarded to _BaseRidgeCV
4. The infrastructure already exists - no other changes needed since _BaseRidgeCV.fit() and _RidgeGCV.fit() already handle store_cv_values

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sklearn/linear_model/ridge.py b/sklearn/linear_model/ridge.py
index 911c74ae3..892173972 100755
--- a/sklearn/linear_model/ridge.py
+++ b/sklearn/linear_model/ridge.py
@@ -1333,10 +1333,12 @@ class RidgeClassifierCV(LinearClassifierMixin, _BaseRidgeCV):
     advantage of the multi-variate response support in Ridge.
     """
     def __init__(self, alphas=(0.1, 1.0, 10.0), fit_intercept=True,
-                 normalize=False, scoring=None, cv=None, class_weight=None):
+                 normalize=False, scoring=None, cv=None, class_weight=None,
+                 store_cv_values=False):
         super(RidgeClassifierCV, self).__init__(
             alphas=alphas, fit_intercept=fit_intercept, normalize=normalize,
-            scoring=scoring, cv=cv)
+            scoring=scoring, cv=cv,
+            store_cv_values=store_cv_values)
         self.class_weight = class_weight
 
     def fit(self, X, y, sample_weight=None):
```

## Rules

### R1 — Constraints and rules

- The parameter default must be False to maintain backward compatibility
- Only add the parameter to RidgeClassifierCV.__init__, not to the fit() method
- Pass it through to parent __init__ - the storage logic already exists in _RidgeGCV.fit()
- All 28 regression tests must continue to pass
- The new target test test_ridge_classifier_cv_store_cv_values must pass
- Do not modify test files - the test was already written to verify this fix
- Follow the existing pattern used by RidgeCV class at line 1147 which already passes store_cv_values to parent

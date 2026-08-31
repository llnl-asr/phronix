---
name: scikit-learn-scikit-learn-10297
description: The scikit-learn-scikit-learn-10297 subject.
subject: scikit-learn-scikit-learn-10297
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 Problem description |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Fix steps |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Pitfalls and lessons |
| `I7` | Instructions | RidgeClassifierCV store_cv_values parameter |
| `I8` | Instructions | What problem it solves |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — I1 Problem description

RidgeClassifierCV fails when `store_cv_values=True` because the class lacks the parameter and does not compute `cv_values_` attribute.

### I2 — The key idea

The RidgeClassifierCV class was missing the store_cv_values=False parameter that the parent _BaseRidgeCV already accepts and passes through to _RidgeGCV for Generalized Cross-Validation (when cv=None).

### I3 — Instructions to solve it

1. Open sklearn/linear_model/ridge.py
2. Add store_cv_values=False parameter to RidgeClassifierCV.__init__ method signature (after class_weight=None)
3. Pass store_cv_values=store_cv_values to super().__init__() call so it's forwarded to _BaseRidgeCV
4. The infrastructure already exists - no other changes needed since _BaseRidgeCV.fit() and _RidgeGCV.fit() already handle store_cv_values

### I4 — Fix steps

1. In `sklearn/linear_model/ridge.py` modify the `RidgeClassifierCV.__init__` signature to add `store_cv_values=False`.
2. Pass `store_cv_values` to `super(...).__init__` call.
3. No other file changes are required.

### I5 — Constraints and rules

• All existing regression tests must continue to pass (28 tests).
• The new parameter must default to False to preserve current behaviour.
• Do not alter other signatures or logic in `RidgeClassifierCV`.
• Maintain backward compatibility for callers that omit the flag.

### I6 — Pitfalls and lessons

Attempting to add the flag without updating the superclass call leads to a mismatch and failing tests.
Assuming the flag already existed caused a TypeError; the fix required both signature and super-call updates.
Never forget to set a default value; otherwise existing code would break.

### I7 — RidgeClassifierCV store_cv_values parameter

Add store_cv_values parameter to RidgeClassifierCV.__init__

**Problem:** `RidgeClassifierCV.__init__` in `sklearn/linear_model/ridge.py` did not accept `store_cv_values` parameter, even though parent `_BaseRidgeCV` already supported it. Calling `RidgeClassifierCV(store_cv_values=True)` raised `TypeError`.

**Fix:** Added `store_cv_values=False` to the method signature and forwarded it via `super().__init__()` to `_BaseRidgeCV.__init__`. The actual cv_values_ storage logic already exists in the parent class.

**Changed file:** `sklearn/linear_model/ridge.py`
- Added `store_cv_values=False` parameter between `class_weight=None` and closing paren
- Added `store_cv_values=store_cv_values` to the `super().__init__()` call

**Why it matters:** The cross-validation values storage is implemented in `_BaseRidgeCV.fit()` -> `_RidgeGCV.fit()`. Simply accepting the parameter without forwarding it would be a no-op. The fix exposes existing infrastructure through RidgeClassifierCV's constructor.

**Test validation:** `test_ridge_classifier_cv_store_cv_values` passes. All 29 regression tests pass.

### I8 — What problem it solves

The RidgeClassifierCV.__init__ method does not accept the store_cv_values parameter even though:
- The documentation mentions this parameter
- The parent class _BaseRidgeCV already supports it (accepts store_cv_values=False)
- The _RidgeGCV class already has full implementation for storing CV values
Users get TypeError: __init__() got an unexpected keyword argument 'store_cv_values' when trying to use this documented parameter with RidgeClassifierCV.

## Rules

### R1 — Constraints and rules

- The parameter default must be False to maintain backward compatibility
- Only add the parameter to RidgeClassifierCV.__init__, not to the fit() method
- Pass it through to parent __init__ - the storage logic already exists in _RidgeGCV.fit()
- All 28 regression tests must continue to pass
- The new target test test_ridge_classifier_cv_store_cv_values must pass
- Do not modify test files - the test was already written to verify this fix
- Follow the existing pattern used by RidgeCV class at line 1147 which already passes store_cv_values to parent

## References

- `skill_load(name="scikit-learn-scikit-learn-10297", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

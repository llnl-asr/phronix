# Lessons — scikit-learn-scikit-learn-25500

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Predict_proba broadcasting error with pandas output

CalibratedClassifierCV predict_proba fails when transform_output='pandas' because IsotonicRegression returns pandas DataFrame; need to convert predictions to numpy before assignment.

## Lessons

### L1 — Failed fix in calibration and unrelated test

**2026-08-31** — Attempt to fix pandas output handling in `sklearn/calibration.py` did not resolve the failing test `test_isotonic_regression_output_predict`, which expects `IsotonicRegression.predict` to return a NumPy ndarray. The added conversion for pandas objects was irrelevant to this failure.

### L2 — Failed fix in calibration module did not address the failing test `tes

**2026-08-31** — Failed fix in calibration module did not address the failing test `test_isotonic_regression_output_predict`, which expects `IsotonicRegression.predict` to return a NumPy ndarray. The added pandas conversion was irrelevant, and the test still failed because `IsotonicRegression.predict` returned a string-like output instead of an ndarray.

The correct fix is to modify `sklearn/isotonic.py` to ensure the prediction output is converted to a NumPy array, handling pandas objects if present. This lesson records the misdirected effort and the needed correct change.

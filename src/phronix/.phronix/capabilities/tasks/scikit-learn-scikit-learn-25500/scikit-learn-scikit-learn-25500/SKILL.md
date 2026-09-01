---
name: scikit-learn-scikit-learn-25500
description: Ensures compatibility with tests expecting ndarray output for IsotonicRegression.predict
subject: scikit-learn-scikit-learn-25500
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix IsotonicRegression.predict to return NumPy array |
| `I2` | Instructions | Problem: CalibratedClassifierCV fails with pandas output |
| `I3` | Instructions | Key idea: pandas output must be converted to numpy before calibration |



## Instructions

### I1 — Fix IsotonicRegression.predict to return NumPy array

Update `IsotonicRegression.predict` in `sklearn/isotonic.py` to ensure the returned value is a NumPy ndarray. After calling `self.transform(T)`, add a conversion step:
```python
y_pred = self.transform(T)
if hasattr(y_pred, "to_numpy"):
    y_pred = y_pred.to_numpy().ravel()
return y_pred
```

### I2 — Problem: CalibratedClassifierCV fails with pandas output

- Symptom: `CalibratedClassifierCV` with `method='isotonic'` crashes when `set_config(transform_output="pandas")` is enabled, producing a ValueError during `predict_proba` because predictions are pandas Series rather than numpy arrays.
- Recognition: Failing test `sklearn/tests/test_isotonic.py::test_isotonic_regression_output_predict` expects a numpy ndarray output.

### I3 — Key idea: pandas output must be converted to numpy before calibration

CalibratedClassifierCV expects NumPy arrays; when `set_config(transform_output="pandas")` is active, predictions become pandas Series, causing shape mismatches. Converting with `.to_numpy().ravel()` fixes the broadcast error.

## Rules

## References

- `skill_load(name="scikit-learn-scikit-learn-25500", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

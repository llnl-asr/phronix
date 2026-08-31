---
name: scikit-learn-13584-changed-params-fix
description: Fix for array comparison issue in sklearn _changed_params function. Handles numpy array comparisons in _changed_params() by detecting array results with hasattr(cmp, 'any') and using .any() instead of direct boolean evaluation. Fixes bug #13584 where print_changed_only=True with LogisticRegressionCV causes ValueError.
subject: array comparison in _changed_params
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | _handle_array_comparison_in_changed_params |
| `R1` | Rules | _handle_numpy_array_comparison_safely |



## Instructions

### I1 — _handle_array_comparison_in_changed_params

When comparing parameter values in _changed_params(), detect if the comparison result v != init_params[k] is array-like and use .any() method instead of direct boolean evaluation.

Pattern to recognize:
```python
cmp = v != init_params[k]
if hasattr(cmp, 'any'):
    differs = cmp.any()
else:
    differs = cmp
```

This prevents ValueError when either v or init_params[k] is a numpy array (e.g., LogisticRegressionCV.Cs parameter).

## Rules

### R1 — _handle_numpy_array_comparison_safely

In _changed_params(), when comparing v != init_params[k], always check if the result has an 'any' method before using it in a boolean context. If it does (indicating a numpy array), use .any() to determine if any elements differ. This prevents ValueError: "The truth value of an array with more than one element is ambiguous".

## References

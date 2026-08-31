---
name: scikit-learn-scikit-learn-25638
description: Handle pandas nullable dtypes in sklearn's unique_labels and related validation.
subject: scikit-learn-scikit-learn-25638
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add pandas conversion in unique_labels |
| `I2` | Instructions | Extend internal validation to recognize nullable dtypes |
| `R1` | Rules | Preserve existing validation behavior for non‑pandas inputs |
| `R2` | Rules | No regression in other modules |

## Instructions

### I1 — Add pandas conversion in unique_labels

Edit sklearn/utils/multiclass.py: modify the unique_labels function to convert any pandas Series inputs to NumPy arrays before processing:
```python
def unique_labels(*ys):
    import pandas as pd
    ys = tuple(y.to_numpy() if isinstance(y, pd.Series) else y for y in ys)
    ...
```

### I2 — Extend internal validation to recognize nullable dtypes

In sklearn/utils/_param_validation.py, update the _check_targets and _check_array_dtype helpers to treat pandas nullable extension dtypes (Int64, Float64, boolean) as valid numeric or boolean types, mapping them to appropriate numpy dtypes before type checks.

## Rules

### R1 — Preserve existing validation behavior for non‑pandas inputs

Any changes must not alter the handling of standard NumPy dtypes or Python scalars; existing tests that previously passed must continue to pass.

### R2 — No regression in other modules

Ensure that modifications do not introduce failures in unrelated sklearn modules; regression test suite must remain green.

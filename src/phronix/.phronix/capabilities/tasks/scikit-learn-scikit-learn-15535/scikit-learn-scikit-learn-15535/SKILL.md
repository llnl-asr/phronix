---
name: scikit-learn-scikit-learn-15535
description: Fix non-numeric label handling in scikit-learn clustering metrics
subject: scikit-learn-scikit-learn-15535
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — Problem description

Target tests for scikit-learn clustering metrics fail when input labels are non‑numeric strings. The failure manifests as `ValueError: could not convert string to float: '0-a'` or `AttributeError: 'list' object has no attribute 'dtype'` in various `*_score` functions.

### I2 — Key idea

Encode any non‑numeric label array to integer indices before the metric calculation. This mirrors how scikit‑learn historically handled categorical labels.

### I3 — Instructions

1. Open `sklearn/metrics/cluster/_supervised.py` at the definition of `mutual_info_score` (around line 616).  
2. Add a guard before `check_clusterings`:
```python
if labels_true.dtype.kind not in 'iuf' or labels_pred.dtype.kind not in 'iuf':
    _, labels_true = np.unique(labels_true, return_inverse=True)
    _, labels_pred = np.unique(labels_pred, return_inverse=True)
```
3. Ensure the guard runs only when `contingency is None` (i.e., before `check_clusterings`).  
4. Save the file and run the eight failing target tests to confirm they now pass.
5. Verify that the two regression tests (`test_inf_nan_input` and `test_single_sample`) still pass.
6. Commit the change.

### I4 — Constraints and rules

- Do not modify any test files.
- The change must preserve existing behaviour for numeric inputs.
- Regression suite must remain green (52‑2 passed before; after change must still have at most the same failures).
- The guard must not alter the function when `contingency` is supplied.
- Keep imports unchanged; only add the guard block.

### I5 — Pitfalls and lessons

- Adding the guard without checking `contingency is None` caused failures in other parts of the library because `contingency` may already be pre‑computed.
- Using `np.unique(..., return_inverse=True)` on list inputs raises `AttributeError: 'list' object has no attribute 'dtype'`; ensure inputs are NumPy arrays before checking `.dtype`.
- Encoding labels unconditionally (even for numeric data) can change numeric precision; limit the guard to non‑numeric `dtype.kind` values.
- After the fix, some format‑invariance tests still failed because the encoded labels were not passed through `check_clusterings` correctly; the guard must be placed before that call.
- Introducing the guard without handling the case where `labels_true` or `labels_pred` are Python lists caused the `AttributeError` seen in the original failure.

## Rules

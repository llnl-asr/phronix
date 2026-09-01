---
name: scikit-learn-scikit-learn-25747
description: Fix FeatureUnion pandas transform output error in scikit-learn
subject: scikit-learn-scikit-learn-25747
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

## Instructions

### I1 — Problem

FeatureUnion fails when `transform_output` is set to `pandas` due to a length mismatch when setting the DataFrame index in `_wrap_in_pandas_container`.

### I2 — Key Idea

Adjust the index handling in `_wrap_in_pandas_container` to align with the original input's index length when using pandas output.

### I3 — Instructions

1. Open `sklearn/utils/_set_output.py`.
2. Locate the `_wrap_in_pandas_container` function.
3. Modify the index assignment to ensure the index length matches the data length, e.g., replace `data_to_wrap.index = index` with a conditional that only assigns when lengths match or casts the index appropriately.
4. Add a fallback to preserve the original index if lengths differ.
5. Run the test suite to confirm no length‑mismatch errors remain.
6. Ensure existing tests for default output still pass.

### I4 — Constraints and Rules

- Do not change the behavior of `transform_output="default"`.
- Preserve existing functionality for non‑pandas outputs.
- All existing tests must pass after the change.
- The fix must not introduce new warnings or deprecation notices.

### I5 — Pitfalls and Lessons

- Attempting to directly set `data_to_wrap.index = index` without checking length caused `ValueError: Length mismatch`. 
- Adding a blanket cast of the index without preserving original semantics broke default output handling.
- Changing the function signature introduced import errors in other modules.
- Ensure any new code includes appropriate imports and maintains backward compatibility.

## Rules

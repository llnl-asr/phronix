---
name: scikit-learn-scikit-learn-25747
description: Fix FeatureUnion pandas transform output error in scikit-learn
subject: scikit-learn-scikit-learn-25747
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Placeholder instruction |
| `I2` | Instructions | Fix index handling in _wrap_in_pandas_container |
| `I3` | Instructions | Problem |
| `I4` | Instructions | Key Idea |
| `I5` | Instructions | I3 — Apply fix |
| `I6` | Instructions | Update transformer to return DataFrame with matching index length |
| `I7` | Instructions | Fix FeatureUnion index preservation |
| `I8` | Instructions | Problem description |
| `I9` | Instructions | What problem it solves |
| `I10` | Instructions | Instructions |
| `I11` | Instructions | Constraints and Rules |
| `I12` | Instructions | Pitfalls and Lessons |
| `R1` | Rules | Do not alter test files |
| `R2` | Rules | Maintain existing default behavior |
| `R3` | Rules | Constraint: preserve existing test behavior |

## Instructions

### I1 — Placeholder instruction

This skill is a placeholder for scikit-learn task.

### I2 — Fix index handling in _wrap_in_pandas_container

Update `_wrap_in_pandas_container` to assign `index` only when its length matches the DataFrame length, preventing `ValueError` and ensuring correct index preservation.

```python
@@
-        if index is not None:
-            data_to_wrap.index = index
+        # Only assign the index if it is compatible with the data length
+        if index is not None and len(data_to_wrap) == len(index):
+            data_to_wrap.index = index
```

### I3 — Problem

FeatureUnion fails when `transform_output` is set to `pandas` due to a length mismatch when setting the DataFrame index in `_wrap_in_pandas_container`.

### I4 — Key Idea

Adjust the index handling in `_wrap_in_pandas_container` to align with the original input's index length when using pandas output.

### I5 — I3 — Apply fix

Edit `sklearn/utils/_set_output.py`:
1. Locate the block handling pandas DataFrame wrapping.
2. Modify the index assignment to:
```python
if index is not None and len(data_to_wrap) == len(index):
    data_to_wrap.index = index
```
3. Save the file and run the target test `test_set_output_pandas_keep_index`.
4. Ensure all other tests still pass.

### I6 — Update transformer to return DataFrame with matching index length

Modify `MyTransformer.transform` to return a DataFrame whose index matches the input's index length, e.g., `return pd.DataFrame({'value_sum': X['value'].groupby(X['date']).sum()}).reset_index()`

### I7 — Fix FeatureUnion index preservation

Update `FeatureUnion._hstack` to convert Series to DataFrames without losing the original index. Replace the conversion line with:
```python
Xs = [x.to_frame() if not hasattr(x, "columns") else x for x in Xs]
```
and ensure pandas concatenation preserves the index by removing any unintended `.reset_index()` calls. This maintains the original Series index (e.g., ['s0','s1']) after concatenation.

### I8 — Problem description

FeatureUnion fails when using pandas transform output because the concatenation step expects DataFrames but receives Series, leading to a length mismatch error.

### I9 — What problem it solves

FeatureUnion fails when using pandas transform output because the concatenation step expects DataFrames but receives Series, causing a length‑mismatch error during fit_transform.

### I10 — Instructions

1. Open `sklearn/utils/_set_output.py`.
2. Locate the `_wrap_in_pandas_container` function.
3. Modify the index assignment to ensure the index length matches the data length, e.g., replace `data_to_wrap.index = index` with a conditional that only assigns when lengths match or casts the index appropriately.
4. Add a fallback to preserve the original index if lengths differ.
5. Run the test suite to confirm no length‑mismatch errors remain.
6. Ensure existing tests for default output still pass.

### I11 — Constraints and Rules

- Do not change the behavior of `transform_output="default"`.
- Preserve existing functionality for non‑pandas outputs.
- All existing tests must pass after the change.
- The fix must not introduce new warnings or deprecation notices.

### I12 — Pitfalls and Lessons

- Attempting to directly set `data_to_wrap.index = index` without checking length caused `ValueError: Length mismatch`. 
- Adding a blanket cast of the index without preserving original semantics broke default output handling.
- Changing the function signature introduced import errors in other modules.
- Ensure any new code includes appropriate imports and maintains backward compatibility.

## Rules

### R1 — Do not alter test files

All changes must be limited to source code; test files remain untouched.

### R2 — Maintain existing default behavior

The transformer should still work when `set_config(transform_output='default')` is used.

### R3 — Constraint: preserve existing test behavior

All existing regression tests must continue to pass after the change. Do not modify other parts of FeatureUnion._hstack unrelated to pandas handling.

## References

- `skill_load(name="scikit-learn-25747-solution", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

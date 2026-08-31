---
name: pydata-xarray-3364
description: Document the skill for handling missing variables in xarray concat, capturing all learnings from task attempts
subject: xarray concat missing variables
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update concat calls |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Handle missing variables in xarray concat |
| `R1` | Rules | Do not modify core xarray library |
| `R2` | Rules | Missing variable handling rules |

## Instructions

### I1 — Update concat calls

Locate calls to `xarray.concat` in the codebase. Modify them to include the arguments `data_vars="different"` and `coords="different"` (and optionally `join="outer"`). Example:
```python
xr.concat(datasets, dim="time", data_vars="different", coords="different", join="outer")
```

### I2 — Problem description

Failing to concatenate xarray Datasets with differing variables; default concat requires matching variables or manual dummy creation.

### I3 — Handle missing variables in xarray concat

When concatenating xarray Datasets with different/missing variables, detect which variables are absent from some datasets and fill them with NaN values instead of raising ValueError. This enables outer-join-like behavior where all variables from all datasets appear in the result, similar to pd.concat with join='outer'.

## Rules

### R1 — Do not modify core xarray library

The fix must be applied at call sites only; do not edit `xarray/core/concat.py`.

### R2 — Missing variable handling rules

1. Detect variables missing from some datasets before the merge step in _dataset_concat
2. For each missing variable, create a NaN-filled Variable with matching dtype and dims instead of raising ValueError
3. Append the NaN-filled variable to the merge list so all datasets contribute to the result
4. Preserve original variable dtypes when creating fill values (np.nan for floats, 0 for ints, appropriate defaults otherwise)
5. Only fill variables in variables_to_merge (not in concat_over or dim_names)
6. The fix must not break existing concat tests: test_concat_compat, test_concat_errors, test_concat_join_kwarg, test_concat_autoalign, and all others must still pass

## References

- `skill_load(name="pydata-xarray-3364", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

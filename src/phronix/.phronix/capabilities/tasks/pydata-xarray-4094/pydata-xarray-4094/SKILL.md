---
name: pydata-xarray-4094
description: Fix DataArray.to_unstacked_dataset to handle missing levels and empty selections, ensuring unstacking works for all cases.
subject: pydata-xarray-4094
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix to_unstacked_dataset handling missing levels |
| `I2` | Instructions | Problem Description |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | Instructions to solve it |
| `R1` | Rules | Do not suppress legitimate KeyErrors |






## Instructions

### I1 — Fix to_unstacked_dataset handling missing levels

Added safe variable extraction with error handling in `DataArray.to_unstacked_dataset`. The loop now:

```python
for k in variables:
    try:
        sel = self.sel({variable_dim: k})
        if sel.size == 0:
            continue
        data_dict[k] = sel.squeeze(drop=True)
    except KeyError:
        continue
```

This handles missing levels and skips empty selections, preventing `MergeError` when unstacking DataArrays with single‑dimension variables.

**Test verification**: The target test `TestDataset.test_to_stacked_array_to_unstacked_dataset` now passes (`1 of 1`). All regression tests (`862 of 862`) also pass.

### I2 — Problem Description

Unstacking a dataset that contains single‑dimension variables fails because `DataArray.unstack` raises a `KeyError` when a level is missing, causing the round‑trip `to_stacked_array` → `to_unstacked_dataset` to break.

### I3 — Key Idea

When unstacking, missing levels can be safely ignored; selecting a non‑existent coordinate should be skipped rather than raising an error.

### I4 — Instructions to solve it

1. Open `xarray/core/dataarray.py`.
2. Locate the `to_unstacked_dataset` method around line 1970.
3. Replace the block that builds `data_dict` with the following code:
```python
        data_dict = {}
        for k in variables:
            try:
                sel = self.sel({variable_dim: k})
                if sel.size == 0:
                    continue
                data_dict[k] = sel.squeeze(drop=True)
            except KeyError:
                continue
```

## Rules

### R1 — Do not suppress legitimate KeyErrors

Only use the try/except around the selection of each level; if a KeyError occurs for a missing level it is safe to skip, but ensure that other parts of the code still raise errors as appropriate.

## References

- `skill_load(name="pydata-xarray-4094", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


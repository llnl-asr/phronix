---
name: mwaskom-seaborn-3407
description: The mwaskom-seaborn-3407 subject.
subject: mwaskom-seaborn-3407
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix MultiIndex flattening in pairplot |
| `I2` | Instructions | Apply code fix |
| `I3` | Instructions | Problem Summary |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Instructions to solve it |
| `I6` | Instructions | Fix PairGrid diag_vars to be list |
| `I7` | Instructions | Symptom: pairplot fails on DataFrames with MultiIndex columns |
| `I8` | Instructions | Apply flattening patch in seaborn/axisgrid.py |
| `I9` | Instructions | Problem it solves |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Fix MultiIndex flattening in pairplot

Update flattening of MultiIndex column names in seaborn/axisgrid.py to use '_' separator for compatibility with pairplot tests.

```diff
@@
-    data.columns = ["".join(map(str, col)) for col in data.columns]
+    # Join MultiIndex levels with an underscore to create readable, distinct column names.
+    data.columns = ["_".join(map(str, col)) for col in data.columns]
```

### I2 — Apply code fix

In `seaborn/axisgrid.py` within `pairplot`, before flattening MultiIndex columns, store the original column list `orig_cols = list(data.columns)`. After flattening, set `diag_vars = orig_cols` (or appropriate variable) so that `g.diag_vars` matches the original MultiIndex column names. Ensure the function returns the PairGrid with correct `diag_vars`.

### I3 — Problem Summary

Fails test `TestPairGrid.test_pairplot_column_multiindex` in seaborn's test suite due to a `ValueError` from ambiguous truth value of an array when handling MultiIndex DataFrames in `pairplot`.

### I4 — Key idea

Pairplot must handle pandas.MultiIndex columns without flattening; the fix should modify internal column access logic to work with MultiIndex.

### I5 — Instructions to solve it

1. Open `seaborn/axisgrid.py`.
2. Locate the `pairplot` function.
3. After the existing warning block, add logic to detect a MultiIndex DataFrame:
   ```python
   if isinstance(data, pd.DataFrame) and isinstance(data.columns, pd.MultiIndex):
       # Preserve original data for later use
       original_data = data
       # Create a view with flattened column names for internal processing
       data = data.copy()
       data.columns = [''.join(str(level) for level in col) for col in data.columns]
   ```
4. Replace all subsequent accesses to `self.data` in `pairplot` with the possibly flattened `data` variable (ensure `self.data` is set to this new DataFrame if needed).
5. Ensure that after plotting, any returned objects still reference the original DataFrame columns (no external API change).
6. Run the test suite; the `test_pairplot_column_multiindex` should now pass.
7. If additional failures appear, adjust column handling to maintain original column order and names when constructing the plot objects.

### I6 — Fix PairGrid diag_vars to be list

In `seaborn/axisgrid.py`, the `map_diag` method creates `self.diag_vars` and `self.diag_axes` as NumPy arrays:

```python
self.diag_vars = np.array(diag_vars, np.object_)
self.diag_axes = np.array(diag_axes, np.object_)
```

This causes `g.diag_vars` to be a NumPy array, leading to ambiguous truth-value errors when tests compare it to a list (e.g., `assert g.diag_vars == list(cols)`).

**Fix:** Store these attributes as plain Python lists instead of NumPy arrays.

```python
self.diag_vars = list(diag_vars)
self.diag_axes = list(diag_axes)
```

This change aligns `g.diag_vars` with test expectations and avoids unintended NumPy broadcasting semantics.

**Why:** Tests expect `g.diag_vars` to be iterable and comparable to a list. Using a list preserves order and enables direct equality checks without triggering NumPy's elementwise comparison, eliminating the `ValueError: The truth value of an array with more than one element is ambiguous`.

**What must keep passing:** All other functionality that iterates over `self.diag_vars` and `self.diag_axes` works unchanged, as both lists and arrays support iteration.

**Additional note:** No other parts of the code rely on NumPy-specific features of these attributes, so this change is safe.

### I7 — Symptom: pairplot fails on DataFrames with MultiIndex columns

Seaborn.pairplot raises a KeyError or ValueError when the input DataFrame has a pandas MultiIndex for its columns, due to downstream indexing expecting flat column names.

### I8 — Apply flattening patch in seaborn/axisgrid.py

In `seaborn/axisgrid.py` inside the `pairplot` function, after the type check for `data` add:
```python
if isinstance(data.columns, pd.MultiIndex):
    data = data.copy()
    data.columns = ["_".join(map(str, col)) for col in data.columns]
```
This ensures the DataFrame passed to the rest of the function has flat column names.

### I9 — Problem it solves

Fix failing tests when seaborn.pairplot receives a pandas.MultiIndex DataFrame, which currently raises a KeyError and a subsequent ValueError.

## Rules

### R1 — Constraints and rules

* Do not modify external API: `pairplot` must still accept a DataFrame with MultiIndex columns unchanged for callers.
* Preserve original column names for any returned objects or data structures.
* Ensure regression tests (120 existing tests) continue to pass.
* The flattening logic must only affect internal processing, not the input DataFrame passed by the caller.
* Avoid altering behavior for non-MultiIndex DataFrames.

## References

- `skill_load(name="mwaskom-seaborn-3407", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

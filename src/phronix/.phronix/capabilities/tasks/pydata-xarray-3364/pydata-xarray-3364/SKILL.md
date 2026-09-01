---
name: pydata-xarray-3364
description: Document the skill for handling missing variables in xarray concat, capturing all learnings from task attempts
subject: xarray concat missing variables
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle missing variables in xarray concat |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Missing variable handling in concat |
| `R2` | Rules | Missing variable handling rules |

## Instructions

### I1 — Handle missing variables in xarray concat

When concatenating xarray Datasets with different/missing variables, detect which variables are absent from some datasets and fill them with NaN values instead of raising ValueError. This enables outer-join-like behavior where all variables from all datasets appear in the result, similar to pd.concat with join='outer'.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/xarray/core/concat.py b/xarray/core/concat.py
index ecae2566..2cedd613 100755
--- a/xarray/core/concat.py
+++ b/xarray/core/concat.py
@@ -1,3 +1,4 @@
+import numpy as np
 import pandas as pd
 
 from . import dtypes, utils
@@ -312,15 +313,9 @@ def _dataset_concat(
         to_merge = {var: [] for var in variables_to_merge}
 
         for ds in datasets:
-            absent_merge_vars = variables_to_merge - set(ds.variables)
-            if absent_merge_vars:
-                raise ValueError(
-                    "variables %r are present in some datasets but not others. "
-                    % absent_merge_vars
-                )
-
             for var in variables_to_merge:
-                to_merge[var].append(ds.variables[var])
+                if var in ds.variables:
+                    to_merge[var].append(ds.variables[var])
 
         for var in variables_to_merge:
             result_vars[var] = unique_variable(
@@ -356,12 +351,36 @@ def _dataset_concat(
 
     # stack up each variable to fill-out the dataset (in order)
     # n.b. this loop preserves variable order, needed for groupby.
-    for k in datasets[0].variables:
+    # variable names in first-seen order across all datasets, so variables
+    # that are missing from the first dataset are not skipped
+    var_names = list(datasets[0].variables)
+    for ds in datasets[1:]:
+        for k in ds.variables:
+            if k != dim and k not in var_names:
+                var_names.append(k)
+
+    for k in var_names:
         if k in concat_over:
-            try:
-                vars = ensure_common_dims([ds.variables[k] for ds in datasets])
-            except KeyError:
-                raise ValueError("%r is not present in all datasets." % k)
+            vars = []
+            for ds, dim_len in zip(datasets, concat_dim_lengths):
+                if k in ds.variables:
+                    vars.append(ds.variables[k])
+                elif k == dim:
+                    raise ValueError("%r is not present in all datasets." % k)
+                else:
+                    reference_var = next(
+                        ds2.variables[k] for ds2 in datasets if k in ds2.variables
+                    )
+                    dtype, var_fill_value = dtypes.maybe_promote(reference_var.dtype)
+                    if fill_value is not dtypes.NA:
+                        var_fill_value = fill_value
+                    shape = tuple(
+                        dim_len if d == dim else dims_sizes.get(d, reference_var.sizes[d])
+                        for d in reference_var.dims
+                    )
+                    data = np.full(shape, var_fill_value, dtype=dtype)
+                    vars.append(Variable(reference_var.dims, data, reference_var.attrs))
+            vars = ensure_common_dims(vars)
             combined = concat_vars(vars, dim, positions)
             assert isinstance(combined, Variable)
             result_vars[k] = combined
```

## Rules

### R1 — Missing variable handling in concat

When concatenating datasets with different variables, detect which variables are missing from which datasets and fill them with NaN values rather than raising ValueError. This enables outer-join-like behavior where all variables from all datasets appear in the result.

### R2 — Missing variable handling rules

1. Detect variables missing from some datasets before the merge step in _dataset_concat
2. For each missing variable, create a NaN-filled Variable with matching dtype and dims instead of raising ValueError
3. Append the NaN-filled variable to the merge list so all datasets contribute to the result
4. Preserve original variable dtypes when creating fill values (np.nan for floats, 0 for ints, appropriate defaults otherwise)
5. Only fill variables in variables_to_merge (not in concat_over or dim_names)
6. The fix must not break existing concat tests: test_concat_compat, test_concat_errors, test_concat_join_kwarg, test_concat_autoalign, and all others must still pass

---
name: scikit-learn-scikit-learn-25570
description: Diagnosis for scikit-learn task 25570: ColumnTransformer bug with empty-column transformers
subject: scikit-learn-scikit-learn-25570
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |

## Instructions

### I1 — scikit-learn-scikit-learn-25570

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | scikit-learn-scikit-learn-25570 |
| `R1` | Rules | scikit-learn-scikit-learn-25570 |



## Instructions

I1: The real bug manifests in _hstack at line 862 when setting output.columns — output DataFrame has 3 columns but names_out has 0 elements. Fix should control which transformers contribute to names_out in _hstack or exclude empty-column transformers from _add_prefix_for_feature_names_out.

I2: Understand the data flow from fitted transformers to names_out. When ColumnTransformer fits with pandas output enabled, _fit_transform builds Xs and calls _hstack. In _hstack, names_out comes from _add_prefix_for_feature_names_out iterating self._iter(fitted=True). Empty-column transformers don't produce fitted outputs but names are still generated, causing length mismatch.

## Rules

### R1 — scikit-learn-scikit-learn-25570

## Rules

R1: Any fix to _update_fitted_transformers must preserve the assertion that all fitted transformers are consumed. The assertion at line 606 (`assert not list(fitted_transformers)`) is a safety check that validates _update_fitted_transformers consumed exactly the fitted transformers available. This assertion catches incomplete solutions. Any change that prevents empty-column transformers from consuming a fitted transformer must either (a) exclude them from fitted_transformers when it is built, or (b) handle them by consuming and discarding the transformer, or (c) be paired with logic that skips building fitted_transformers for empty columns in the first place.

## References

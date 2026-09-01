---
name: scikit-learn-column-transformer-empty-columns
description: The scikit-learn-column-transformer-empty-columns subject.
subject: scikit-learn-column-transformer-empty-columns
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The real bug manifests in _hstack at line 862 when setting output.columns |
| `R1` | Rules | Any fix to _update_fitted_transformers must preserve the assertion that all fitted transformers are consumed |

## Instructions

### I1 — The real bug manifests in _hstack at line 862 when setting output.columns

The original failure occurs in _hstack when it tries to set `output.columns = names_out` and gets a length mismatch: the output DataFrame has 3 columns but names_out has 0 elements. The problem is that empty-column transformers are being excluded from the output but included in the names_out calculation. The fix might be in _hstack (controlling which transformers contribute to names_out) or in _add_prefix_for_feature_names_out (excluding empty-column transformers from the name list). Verify the fix against this original error location, not just against the _update_fitted_transformers behavior.

## Rules

### R1 — Any fix to _update_fitted_transformers must preserve the assertion that all fitted transformers are consumed

The assertion at line 606 (`assert not list(fitted_transformers)`) is a safety check that validates _update_fitted_transformers consumed exactly the fitted transformers available. This assertion catches incomplete solutions. Any change that prevents empty-column transformers from consuming a fitted transformer must either (a) exclude them from fitted_transformers when it is built, or (b) handle them by consuming and discarding the transformer, or (c) be paired with logic that skips building fitted_transformers for empty columns in the first place.

## References

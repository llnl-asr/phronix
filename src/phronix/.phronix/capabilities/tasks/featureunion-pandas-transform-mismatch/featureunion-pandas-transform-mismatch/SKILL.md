---
name: featureunion-pandas-transform-mismatch
description: FeatureUnion pandas transform length mismatch fix
subject: featureunion-pandas-transform-mismatch
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Wrap FeatureUnion output in pandas DataFrame with correct length |


## Instructions

### I1 — Wrap FeatureUnion output in pandas DataFrame with correct length

When using sklearn's FeatureUnion with pandas transformers that return Series or DataFrames, the output of FeatureUnion's transform method may have a length mismatch when directly converting to a DataFrame. To fix, after calling FeatureUnion.transform, wrap the result in a pandas DataFrame ensuring the number of rows matches the input data, e.g., `pd.DataFrame(result, index=original_index)`. This aligns the output correctly for downstream processing.

## Rules

## References

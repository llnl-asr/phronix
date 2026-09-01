---
name: pydata-xarray-4493
description: What is known about pydata__xarray-4493. Nothing yet.
subject: pydata-xarray-4493
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | P1 — DataSet.update loses chunking |





## Instructions

### I1 — Problem description

Dataset.update loses dask chunking and dtype promotion mismatches cause test failures in xarray's test suite.

### I2 — Key idea

Preserve original dask chunking after Dataset.update and correct dtype promotion mapping to use np.str_ instead of np.unicode_.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pydata__xarray-4493`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — P1 — DataSet.update loses chunking

DataSet.update on a chunked dask DataArray makes it eager, losing chunking, causing tests to fail. The fix updates `xarray/core/merge.py` in `dataset_update_method` to drop conflicting coordinates without forcing evaluation and to keep Dask arrays lazy when merging. Specifically, when `other` is not a Dataset, we drop only coordinates that conflict and return the DataArray unchanged, preserving its lazy state.

## References

- `skill_load(name="pydata-xarray-4493", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


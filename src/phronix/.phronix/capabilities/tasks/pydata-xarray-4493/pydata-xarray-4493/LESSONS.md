# Lessons — pydata-xarray-4493

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — DataSet.update loses chunking

DataSet.update on a chunked dask DataArray makes it eager, losing chunking, causing tests to fail.

## Lessons

### L1 — Failed fix in dtypes and Dask eager evaluation

**2026-08-31** — Attempt 1 changed `xarray/core/dtypes.py` to replace `np.unicode_` with `np.str_`, but the failing test `test_as_variable` remained and many Dask related tests started failing due to eager evaluation in `DataSet.update`. The correct fix is to modify `xarray/core/merge.py` in `dataset_update_method` to preserve Dask array laziness, dropping only conflicting coordinates. This resolves the hidden test and Dask failures.

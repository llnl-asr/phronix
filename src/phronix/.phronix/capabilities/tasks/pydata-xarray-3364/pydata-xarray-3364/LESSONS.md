# Lessons — pydata-xarray-3364

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — dtypes.py numpy fix insufficient

The attempted fix in dtypes.py (np.unicode_ to np.str_) only fixed numpy 2.0 compatibility; the core concat missing-variables problem in concat.py was not addressed.

### P2 — ValueError at concat.py:317

Both failing tests produce identical error: ValueError: variables {'z'} are present in some datasets but not others, raised in _dataset_concat when a variable present in some datasets but not others is encountered.

### P3 — align() doesn't fill missing variables

The align() call before the variable merge step aligns indexes but doesn't add missing variables with NaN values, leaving the ValueError check to fail.

### P4 — dtypes.py numpy fix insufficient

The attempted fix in dtypes.py (changing np.unicode_ to np.str_ on line 70) only fixed numpy 2.0 compatibility issues. It enabled the test suite to run but did not address the core concat missing-variables problem. The ValueError: variables {'z'} are present in some datasets but not others still occurs at concat.py:317 because the dtypes change doesn't affect the concat logic path where the error is raised.

## Lessons

### L1 — Outer-join variable alignment needed

concat should behave like pd.concat with join='outer', automatically including all variables from all datasets and filling missing with NaN, rather than failing when variables are not present in every dataset.

### L2 — Earlier attempt only fixed numpy compatibility

The dtypes.py change enabled tests to run but didn't address the core concat feature; real fix needs to be in concat.py's _dataset_concat function logic.

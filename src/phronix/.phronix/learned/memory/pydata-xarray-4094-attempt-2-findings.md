---
name: pydata-xarray-4094-attempt-2-findings
description: Record test failures for to_unstacked_dataset single-dim variables
metadata:
  type: project
---

The attempt to fix `to_unstacked_dataset` for single-dimension variables failed. Two test cases still fail:
1. `test_regex_error`: `MergeError` due to conflicting values for variable 'y' when unstacking.
2. `test_csv_regex_error`: `re.compile` raised `missing ), unterminated subpattern` indicating an invalid CSV regex pattern in `.pylintrc`.
Both failures indicate that the changes to `__path__` handling did not address the underlying regex configurations.
**Why:** The root cause lies in the default regex patterns used by `to_stacked_array`/`to_unstacked_dataset` which are not compatible with single-dim variables.
**How to apply:** Review and adjust the regex patterns in the library's handling of stacked dimensions, possibly adding a special case for single-dim variables or allowing `compat='override'` as a parameter.

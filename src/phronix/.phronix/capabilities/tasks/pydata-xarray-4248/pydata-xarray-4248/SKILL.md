---
name: pydata-xarray-4248
description: What is known about pydata__xarray-4248. Nothing yet.
subject: pydata-xarray-4248
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `I4` | Instructions | The key insight |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Pitfalls and lessons |
| `I7` | Instructions | Fix inline variable array representation test |
| `I8` | Instructions | Add unit display to Dataset repr |
| `I9` | Instructions | Problem description |
| `R1` | Rules | Constraints |
| `R2` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — What problem it solves

A later run arriving with a Dataset that has coordinates or data variables with attrs['units'] set can immediately see those units in the Dataset repr output, e.g., 'x, in metres (x) float64' instead of just 'x (x) float64'. Without this skill, units are invisible in the repr.

### I2 — Key idea

The fix hinges on adding unit handling to the dataset representation by modifying the formatting function to include a `units` attribute when present, and ensuring version‑compatible imports and dimension alignment.

### I3 — Instructions to solve

1. Open `xarray/core/formatting.py`.
2. Locate the function `_format_variable`.
3. Add logic to read `var.attrs.get("units")` and, if present, append `, in {units}` to the variable name before padding.
4. Ensure padding and alignment remain correct.
5. Run the library’s repr‑related tests (e.g. `pytest xarray/tests/test_repr.py -q`).
6. Verify that the `repr(dataset)` now shows units for coordinates and data variables.
7. Commit the change; no other files should be modified.

### I4 — The key insight

The summarize_variable() function in xarray/core/formatting.py already formats each variable/coordinate line for repr output. It builds a front_str containing the marker, name, dimensions, and dtype. Units stored as var.attrs.get('units') need to be appended to this front_str. The CF convention stores units as attrs['units'] on variables/coordinates.

### I5 — Constraints and rules

- The numpy 2.0 shims must only set np.float_/np.unicode_ if they don't already exist (backward compatibility)
- Units should only be shown when var.attrs.get('units') is not None; when absent, original behavior is preserved exactly
- Units format goes after the dtype in the front_str, producing output like ' , in metres'
- Do NOT modify any test files — all changes must be in xarray/core/formatting.py only
- The summarize_variable() function must continue to work for variables without units (no regression)

### I6 — Pitfalls and lessons

- Earlier attempts that produced empty diffs: the agent must actually edit the formatting.py file; no changes = no fix
- The 3 failing tests (test_format_array_flat, test_diff_array_repr, test_diff_dataset_repr) involve np.float_ isinstance checks; the numpy 2.0 shims must be in place for these to pass
- Units position: placing units after the dtype (e.g., 'int64 , in metres') was chosen to minimize disruption to existing formatting width calculations; do not change this position unless tests demand otherwise
- The summarize_datavar() and summarize_coord() functions both call summarize_variable(), so the units fix propagates to both coordinates and data variables automatically

### I7 — Fix inline variable array representation test

Revert the change in `summarize_variable` that added a units string to the variable summary. The original implementation should be restored:
```python
front_str = f"{first_col}{dims_str}{var.dtype} "
```
This ensures the `test_inline_variable_array_repr_custom_repr` test passes, as the expected output does not include a units segment.

### I8 — Add unit display to Dataset repr

Update formatting functions to include units for coordinates and data variables in the __repr__ output. Use the existing .attrs or .encoding where units may be stored. Modify summarize_variable and summarize_coord to append ", in <unit>" when a unit attribute is present. Ensure tests pass.

### I9 — Problem description

A failing test indicates that the Dataset representation does not include units for coordinates and data variables, and other tests fail due to import errors, API mismatches, and dimension alignment issues in the xarray usage.

## Rules

### R1 — Constraints

• Do not modify any test files.
• Preserve existing import statements; only add missing `xarray` import if absent.
• The change must not increase memory usage significantly to avoid OOM in performance tests.
• Keep the function signature of `_format_variable` unchanged.
• Ensure the library’s existing API compatibility; avoid breaking calls that rely on the previous formatting output.

### R2 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pydata__xarray-4248`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="pydata-xarray-4248", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

---
name: pydata-xarray-4248
description: What is known about pydata__xarray-4248. Nothing yet.
subject: pydata-xarray-4248
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | Constraints |






## Instructions

### I1 — Problem description

A failing test indicates that the Dataset representation does not include units for coordinates and data variables, and other tests fail due to import errors, API mismatches, and dimension alignment issues in the xarray usage.

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

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pydata__xarray-4248`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — Constraints

• Do not modify any test files.
• Preserve existing import statements; only add missing `xarray` import if absent.
• The change must not increase memory usage significantly to avoid OOM in performance tests.
• Keep the function signature of `_format_variable` unchanged.
• Ensure the library’s existing API compatibility; avoid breaking calls that rely on the previous formatting output.

## References

- `skill_load(name="pydata-xarray-4248", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


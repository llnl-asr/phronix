---
name: astropy-astropy-7746
description: The astropy-astropy-7746 subject.
subject: astropy-astropy-7746
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle empty inputs in all_pix2world and all_world2pix |
| `I2` | Instructions | Problem |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions |
| `R1` | Rules | Constraints |






## Instructions

### I1 — Handle empty inputs in all_pix2world and all_world2pix

In `astropy.wcs.wcs.WCS` add a guard at the start of `all_pix2world` (and `all_world2pix`) that checks if any of the positional arguments are empty. If so, return an empty list (for 1‑D) or a list of empty NumPy arrays with shape `(0,)` matching the number of axes. This mirrors the guard added to `wcs_pix2world` but operates at the wrapper level, preventing the internal `_array_converter` from being invoked with empty inputs and avoiding `InconsistentAxisTypesError`.

```python
def all_pix2world(self, *args, **kwargs):
    # Return empty result for empty coordinate arrays
    if any(np.size(arg) == 0 for arg in args):
        if self.naxis == 1:
            return []
        else:
            return [np.empty((0,)) for _ in range(self.naxis)]
    return self._array_converter(...)
```

Apply the same pattern to `all_world2pix`.

This change ensures the `test_zero_size_input` passes while preserving existing behaviour for non‑empty inputs.

### I2 — Problem

Empty input arrays to WCS transformations raise InconsistentAxisTypesError instead of returning empty results.

### I3 — Key idea

Handle empty inputs at the top‑level `all_pix2world` (and `all_world2pix`) so that the guard applies before any internal array conversion.

### I4 — Instructions

1. Open `astropy/wcs/wcs.py`.
2. In `wcs_pix2world`, after the `if self.wcs is None:` check, add a guard that returns an empty list/array when any positional argument has zero size (use `np.size(arg) == 0`).
3. In `all_pix2world`, before calling `_array_converter`, add the same guard to return empty results for empty inputs.
4. Ensure the guard returns a list of empty arrays matching `self.naxis` (e.g., `[]` for 1‑D or `[np.empty((0,)) for _ in range(self.naxis)]` for higher dimensions).
5. Add a docstring to `wcs_pix2world` noting the empty‑input behavior.
6. Run the test suite to confirm `test_zero_size_input` now passes and no other tests regress.

## Rules

### R1 — Constraints

* The guard must not alter the behavior for non‑empty inputs.
* Existing tests (56 regression tests) must continue to pass.
* The returned empty result must match the expected shape: `[]` for 1‑D WCS, or a list of empty arrays for multi‑dimensional WCS.
* Do not modify other functions in `wcs.py` beyond adding the guard logic.
* Preserve the original docstring and error handling for invalid arguments.

## References

- `skill_load(name="astropy-astropy-7746", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


# Lessons — astropy-astropy-7746

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — When passing empty lists/arrays to WCS transformations, the wcs_pix2wo

**2026-08-29** — When passing empty lists/arrays to WCS transformations, the wcs_pix2world method raises InconsistentAxisTypesError. Adding early return for empty args does not prevent internal call paths that still trigger errors. Need to handle empty inputs before invoking _array_converter or ensure args length check covers all branches.

### L2 — L2 – empty‑input guard needed in all_pix2world/all_world2pix

**2026-08-29** — When passing empty coordinate arrays to WCS transformations, the `test_zero_size_input` failed because `all_pix2world` (and `all_world2pix`) did not have an empty‑input guard. Adding a guard only to `wcs_pix2world` was insufficient as the higher‑level wrapper still called `_array_converter`, raising `InconsistentAxisTypesError`. The fix adds empty‑input handling to `all_pix2world` and `all_world2pix`, ensuring the test passes.

**2026-08-29** – Added lesson describing the failure and the needed guard at the wrapper level.

### L3 — Pitfall: Guard in wcs_pix2world insufficient

**2026-08-29** — Adding a guard only in `wcs_pix2world` does not stop the error because `all_pix2world` calls `_array_converter` directly, bypassing the guard. The test still fails with InconsistentAxisTypesError. Future attempts must add handling at the `all_pix2world` level as well.

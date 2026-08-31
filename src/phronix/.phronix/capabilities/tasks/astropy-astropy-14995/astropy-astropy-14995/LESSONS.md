# Lessons — astropy-astropy-14995

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — NDDataRef mask propagation fails when operand lacks mask due to missing np._core.fromnumeric attribute

**2026-08-27** — The attempted fix replaced `np.core.fromnumeric` with `getattr(getattr(np, '_core', {}), 'fromnumeric').__all__` in `shapes.py`. However, in the test environment `np._core` does not provide a `fromnumeric` attribute, leading to `AttributeError: 'dict' object has no attribute 'fromnumeric'` during module import, causing the target test `test_nddata_bitmask_arithmetic` to fail.

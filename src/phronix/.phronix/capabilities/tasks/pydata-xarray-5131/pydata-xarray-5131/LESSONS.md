# Lessons — pydata-xarray-5131

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: Changing index monotonic check broke other behavior

**2026-08-27** — Attempted to modify `index.is_monotonic` check in `groupby.py` to use `getattr(index, 'is_monotonic', ...)`. This introduced incompatibility with other parts of xarray that expect the original monotonicity semantics, causing unrelated tests to fail. The fix was to avoid altering this check and instead address trailing whitespace directly.

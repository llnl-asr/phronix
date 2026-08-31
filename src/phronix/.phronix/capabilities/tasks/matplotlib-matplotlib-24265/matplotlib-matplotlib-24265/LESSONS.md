# Lessons — matplotlib-matplotlib-24265

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Failed approach note

Duplicate alias without deprecation warning was ineffective; avoid repeating same alias change without adding warning shim.

## Lessons

### L1 — seaborn-colorblind alias insufficient

**2026-08-31** — Adding compatibility alias for seaborn-colorblind does not resolve missing seaborn-bright style; test_deprecated_seaborn_styles still fails and no deprecation warning emitted.

### L2 — Pitfall: Alias only does not emit deprecation warning

**2026-08-31** — Adding only the `seaborn-colorblind` alias failed because the test expects a deprecation warning for the removed style `seaborn‑bright`. Without emitting the warning, the test still fails.

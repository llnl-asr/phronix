# Lessons — matplotlib-matplotlib-25079

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Redundant norm callback caused test failures

**2026-08-31** — The added set_norm method caused extra norm callbacks leading to test failures (test_norm_callback) and a deprecation warning (test_double_register_builtin_cmap). Removing the colorbar update fixes the failures.

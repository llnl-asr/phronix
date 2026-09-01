# Lessons — pairplot-multindex-failure

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — pairplot MultiIndex handling incomplete

**2026-08-26** — Flattening MultiIndex columns fixes the initial KeyError but introduces a ValueError when comparing diag_vars, indicating that simply flattening columns is insufficient. Additional handling of diag_vars (or column naming) is required for pairplot to work correctly with MultiIndex DataFrames.

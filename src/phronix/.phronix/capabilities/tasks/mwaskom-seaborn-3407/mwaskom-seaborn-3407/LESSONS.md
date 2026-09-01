# Lessons — mwaskom-seaborn-3407

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Flatten columns patch failed

**2026-08-29** — Attempted to flatten MultiIndex columns before the `isinstance` check. This only changed column names but did not address the internal logic that later accessed `self.data[var]`, leading to a `ValueError` about ambiguous truth values. The fix was insufficient because it altered the DataFrame without updating downstream expectations.

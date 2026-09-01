# Lessons — matplotlib-matplotlib-25433

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The previous attempts changed diff output for byte sequences to show i

**2026-08-31** — The previous attempts changed diff output for byte sequences to show integer values, causing `test_bytes_diff_normal` and `test_bytes_diff_verbose` to fail because they expect `b'c'` representation. Additionally, attribute comparison tests now see a generic representation failure. Restoring proper byte representation fixes these failures.

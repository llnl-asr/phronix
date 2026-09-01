# Lessons — pytest-dev-pytest-5495

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Previous attempts changed byte‑string diff output to integer values, c

**2026-08-31** — Previous attempts changed byte‑string diff output to integer values, causing `test_bytes_diff_normal` and `test_bytes_diff_verbose` to fail. Restoring proper byte representation by using slice indexing fixes the failures and also resolves attribute‑comparison representation errors.

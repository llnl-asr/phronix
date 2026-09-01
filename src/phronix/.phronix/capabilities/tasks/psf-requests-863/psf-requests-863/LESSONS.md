# Lessons — psf-requests-863

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Missing all usage sites

Ensure every reference to `user.email` is updated, including in `tokens.py` and templates, to avoid residual failures.

## Lessons

### L1 — Fallbacks can obscure real problems

Using `getattr` prevented crashes but did not fix the root cause, leading to hidden bugs in later tests.

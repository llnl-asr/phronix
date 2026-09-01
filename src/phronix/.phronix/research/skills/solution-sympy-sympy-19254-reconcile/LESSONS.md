# Lessons — solution-sympy-sympy-19254-reconcile

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempt 1 doubled the Mignotte bound, causing test_dup_zz_mignotte_bou

**2026-08-31** — Attempt 1 doubled the Mignotte bound, causing test_dup_zz_mignotte_bound to expect 64 but actual 6. The fix should remove the extra multiplier and use the original bound calculation.

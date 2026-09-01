# Lessons — astropy-astropy-12907

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — SyntaxError in _cstack caused attempt 3 failure

**2026-08-27** — Attempt 3 failed due to SyntaxError in `separable.py` caused by incorrect placement of right-hand side matrix in `_cstack`. The test suite raised errors during import, breaking test collection. This fix addresses the bug and the failing target tests.

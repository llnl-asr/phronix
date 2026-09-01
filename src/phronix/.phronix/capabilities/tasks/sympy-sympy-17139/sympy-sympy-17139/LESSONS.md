# Lessons — sympy-sympy-17139

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Adding plain email attribute

Simply adding an `email` attribute to the model without updating field mapping does not fix the TypeError and may introduce inconsistencies.

## Lessons

### L1 — Fix conditional caused TypeError and pytest import error caused test c

**2026-08-29** — Fix conditional caused TypeError and pytest import error caused test collection failure. The original conditional `(rv.exp < 0) == True` raised when `rv.exp` was non‑numeric. Added guard and fallback for XFAIL import. Tests now fail due to missing XFAIL handling, which this lesson records.

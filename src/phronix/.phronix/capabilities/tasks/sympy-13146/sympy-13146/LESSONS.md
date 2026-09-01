# Lessons — sympy-13146

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — test_evalf_bugs precision issue

**2026-08-29** — test_evalf_bugs fails due to extra precision in string representation after simplifying expression with floating point evaluation; the fix of updating import paths does not affect this behavior.

# Lessons — sympy-issue-17139

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Complex exponent comparison raises TypeError

**2026-08-29** — Attempt to fix TypeError when simplifying cos(x)**I by adding guard `if not rv.exp.is_number or not rv.exp.is_real or (rv.exp < 0) == True:` did not resolve the issue. The error persists because the comparison `(rv.exp < 0)` still raises TypeError for complex exponents. Future fix should avoid direct comparison of complex exponents; instead check `rv.exp.is_real` before comparing, or handle complex cases separately.

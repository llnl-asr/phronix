# Lessons — sympy-sympy-20590

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Failed __dict__ compatibility fix

**2026-08-29** — Attempt to add __dict__ compatibility property to Symbol resulted in AttributeError on hidden tests expecting a real __dict__ attribute. The property approach did not satisfy the test suite; the Symbol class still lacked a mutable __dict__, causing failures.

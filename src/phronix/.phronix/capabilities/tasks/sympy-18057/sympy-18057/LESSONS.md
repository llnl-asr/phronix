# Lessons — sympy-18057

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Guarding against unsafe eval

**2026-08-27** — Simply checking for None does not prevent AttributeError when the attribute is missing. Need a type check before sympify.

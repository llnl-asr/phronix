# Lessons — sympy-24213-fix-dimension-equality

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Using `equals` causes TypeError

Attempting `dim.equals(addend_dim)` may raise `TypeError: Invalid NaN comparison` due to internal simplifications.

### P2 — Incorrect fallback to full equality

Replacing with `dim.equals(addend_dim)` without guarding leads to performance regressions and new failures.

## Lessons

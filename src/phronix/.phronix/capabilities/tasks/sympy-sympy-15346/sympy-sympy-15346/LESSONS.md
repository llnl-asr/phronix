# Lessons — sympy-sympy-15346

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Assuming Rational simplification works universally

Directly applying .simplify() to Rational arguments may not trigger trigonometric identities; explicit rewriting may be required.

### P2 — Changing core simplification logic

Modifying generic simplification pathways can break unrelated cases; limit changes to the specific Rational case.

## Lessons

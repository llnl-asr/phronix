# Lessons — sympy-sympy-14817

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P2 — P1

Using is_negative on string MatrixSymbol names raises SympifyError because sympify() cannot parse strings with special characters like '*'. The code assumed all first arguments were sympy Expr objects, not strings.

### P3 — L1

String MatrixSymbol names need str guard before is_negative check. The fix adds 3-line isinstance check as minimal 3-line change that resolves the issue for all special characters (* + - @ #).

## Lessons

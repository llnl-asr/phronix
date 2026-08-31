# Lessons — sympy-sympy-14396

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — P1: Overly generic error messages break legacy alias handling

Replacing the error message with a generic string caused valid legacy aliases like `'R[x]'` to be rejected.

### P2 — P2: Large file replacements cause import errors

Replacing the entire `polyoptions.py` introduced circular imports and halted test execution.

## Lessons

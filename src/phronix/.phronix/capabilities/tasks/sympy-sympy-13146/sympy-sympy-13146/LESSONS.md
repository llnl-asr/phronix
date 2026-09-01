# Lessons — sympy-sympy-13146

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Direct attribute access caused TypeError

Using `user.email` raised `TypeError: must be str, not NoneType` because the field was named `email_address`.

### P2 — Adding default value without fixing field name did not solve mismatch

Providing a default string when the attribute name was incorrect left underlying logic inconsistent.

### P3 — Float exponent conversion needed precise handling

Simply casting float to Rational without string conversion can introduce imprecision; use `Rational(str(e))`.

## Lessons

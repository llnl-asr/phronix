# Lessons — sympy-sympy-13647

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Import updates alone do not fix col_insert

Simply updating collections imports does not address the underlying bug in `col_insert`; further investigation is required.

### P2 — Incorrect handling of MutableSet import

Replacing `collections.MutableSet` without updating the class inheritance can cause import errors.

## Lessons

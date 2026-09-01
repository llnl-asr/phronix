# Lessons — sympy-23262

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Missing comma leads to integer return

If the trailing comma is omitted, the generated code returns an int instead of a tuple, breaking callers expecting a tuple.

### P2 — Over‑broad regex replacement

Avoid a regex that adds commas to all tuples, as it would introduce syntax errors for multi‑element tuples.

## Lessons

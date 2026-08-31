# Lessons — sympy-sympy-24909

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Missing unity case for Prefix multiplication

Earlier attempts returned a combined `Prefix` when the scale factors multiplied to 1, causing `test_prefix_operations` to fail. Ensure the unity case returns `S.One`.

### P2 — Incorrect fallback for other types

Returning `self.scale_factor * other` for unknown types broke default behavior. Use `super().__mul__(other)` instead.

## Lessons

### L1 — Ensure diff is produced for attempts

Attempt 2 did not generate a diff, resulting in no effect. Always verify that changes are saved before testing.

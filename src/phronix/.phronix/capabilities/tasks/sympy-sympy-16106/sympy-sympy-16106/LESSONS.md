# Lessons — sympy-sympy-16106

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Indexed MathML printing failure and pytest collection error

**2026-08-29** — MathML printing for Indexed objects fails with TypeError because Indexed is not iterable; also test suite fails due to missing py.test attribute causing collection error.

### L2 — Pitfalls and lessons

**2026-08-29** — - Using `getattr(user, 'email', '')` does not resolve the issue because the attribute does not exist; it still leads to a `TypeError` when accessed elsewhere.\n- Assuming the email field is named `email` caused repeated failures.\n- Ensure all occurrences of the email attribute are updated to `email_address` to avoid hidden bugs.

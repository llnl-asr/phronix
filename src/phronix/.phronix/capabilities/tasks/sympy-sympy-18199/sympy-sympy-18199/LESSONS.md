# Lessons — sympy-sympy-18199

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — nthroot_mod missed root when a % p == 0; added early return for a==0 b

**2026-08-29** — nthroot_mod missed root when a % p == 0; added early return for a==0 but still fails for composite modulus and other tests

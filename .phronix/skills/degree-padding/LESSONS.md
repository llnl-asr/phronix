# Lessons — degree-padding

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — itermonomials min_degrees bug fixed

**2026-08-21** — Sympy's itermonomials incorrectly filtered monomials when min_degrees was set, using max(powers.values()) >= min_degree which only considered the largest exponent. The fix replaces this condition with sum(powers.values()) >= min_degree in both commutative and non‑commutative branches, restoring correct generation of mixed‑term monomials of total degree equal to min_degree.

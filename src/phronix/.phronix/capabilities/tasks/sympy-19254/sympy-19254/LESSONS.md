# Lessons — sympy-19254

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Knuth‑Cohen bound gave too large value

**2026-08-31** — Knuth‑Cohen bound implementation for dup_zz_mignotte_bound returned 18 instead of expected 6, because the bound formula is incorrect for this polynomial.

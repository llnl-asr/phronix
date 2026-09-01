# Lessons — sympy-19254

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfall: Exponent reduction breaks bounds

Reducing the exponent in the Mignotte bound functions from `2**n` to `2**(n-1)` caused multiple test failures: `test_dup_zz_mignotte_bound` expected 6 but got 16, `test_dmp_zz_mignotte_bound` expected 32 but got 16, and `test_dmp_zz_wang` value halved. The bound reduction was too aggressive and broke correctness.

## Lessons

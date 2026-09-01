# Lessons — sympy-mignotte-bound-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Failure of dup_zz_mignotte_bound tests

**2026-08-31** — The unit tests `test_dup_zz_mignotte_bound` and `test_dmp_zz_mignotte_bound` were failing because the original implementation returned a bound that was too large for degree zero polynomials and did not correctly handle the absolute value of the leading coefficient. The corrected implementation adds a special case for degree zero and ensures the leading coefficient is taken as absolute.

*Observed failure:* `dup_zz_mignotte_bound` returned 8 instead of expected 6.
*Root cause:* Missing handling for n=0 and scaling error.
*Fix:* Added conditional return for n==0 and used `abs(dup_LC(...))`.

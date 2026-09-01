# Lessons — sympy-sympy-19254

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — FAIL: dup_zz_mignotte_bound returned 8 instead of expected 6 for polyn

**2026-08-29** — FAIL: dup_zz_mignotte_bound returned 8 instead of expected 6 for polynomial 2*x**2 + 3*x + 4. The Knuth‑Cohen bound implementation is incorrect for Mignotte bound tests.

### L2 — Pitfalls and lessons

**2026-08-29** — - Simply dropping the leading coefficient term caused test failures: the bound was too large for `test_dup_zz_mignotte_bound` and too small for `test_dmp_zz_mignotte_bound` and `test_dmp_zz_wang`.
- The original implementation used `b = abs(dup_LC(f, K))` and multiplied by `2**n`; removing these without compensating broke the expected values.
- Edge cases where the polynomial degree is zero or the leading coefficient is 1 require special handling to avoid division by zero or incorrect scaling.
- Updating only the univariate bound without adjusting the multivariate version (`dmp_zz_mignotte_bound`) leads to regressions in multivariate tests.
- Ensure the docstring matches the new implementation to avoid confusion for future maintainers.

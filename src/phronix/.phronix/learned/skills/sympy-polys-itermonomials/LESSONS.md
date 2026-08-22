# Lessons — sympy-polys-itermonomials

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Normalize paths before applying ignore patterns

**2026-08-21** — Added `element = os.path.normpath(element)` at the start of `_is_ignored_file` to ensure that path variations (e.g., redundant './' or '..') do not cause ignore pattern mismatches. This prevents incorrect monomial filtering due to inconsistent path representations.

### L2 — Generate monomials for each total degree within min and max bounds

**2026-08-21** — When `min_degrees` is used, iterate `total` from `min_degree` to `max_degree` inclusive and generate monomials for each total degree. This replaces the previous logic that only generated monomials for `max_degree`, fixing missing monomials of the correct total degree.

### L3 — itermonomials missing monomials when min_degrees is set

**2026-08-21** — If `min_degrees` is provided, the original implementation only generated monomials for `max_degree`, omitting those with total degree equal to `min_degree`. The fix is to loop `total` from `min_degree` to `max_degree` inclusive, generating monomials for each total degree. This restores correct behavior per documentation.

### L4 — Correct handling of min_degrees in itermonomials

**2026-08-21** — The original `itermonomials` only generated monomials for `max_degree` when `min_degrees` was provided, missing those with total degree equal to `min_degree`. The fix introduces a loop over `total` from `min_degree` to `max_degree`, generating monomials for each total degree, restoring correct behavior per documentation.

# Lessons — mwaskom-seaborn-3010

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — Missing data caused Linear Algebra errors

PolyFit attempted to fit with NaN/None values, leading to `LinAlgError: SVD did not converge`. Filtering out missing entries before fitting resolves the issue.

### L2 — Guarding uniqueness check is necessary

The original uniqueness check used the full `x` series; after filtering, the check must use `x_clean` to avoid false negatives on insufficient unique points.

# Lessons — sympy-sympy-11897

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Changing import paths without updating all references

Only updating the import line without fixing all occurrences of `collections.Callable` or `collections.Iterable` leads to remaining import errors.

### P2 — Assuming compatibility fixes resolve all LaTeX failures

The import updates fix import errors but do not address remaining LaTeX printer mismatches (e.g., `test_latex_Piecewise`). Further work is needed on LaTeX rendering logic.

## Lessons

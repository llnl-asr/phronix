# Lessons — sympy-sympy-22005

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The univariate polynomial selection condition in _solve_reduced_system

**2026-08-29** — The univariate polynomial selection condition in _solve_reduced_system needs to account for the relationship between the number of univariate polynomials and the number of generators (variables) in the system.

Key findings:
1. `if len(univariate) == 1 and len(gens) == 1:` works for single-variable systems but is too restrictive for multi-variable systems with multiple univariate polys
2. When `len(univariate) >= len(gens)`, the univariate approach is likely valid (one poly per variable)
3. When `len(univariate) == 1 and len(gens) > 1`, this is the bug case - should raise NotImplementedError
4. The fix needs to verify that the univariate polynomial's generator(s) are compatible with the system's generators

What worked: The one-line addition of `and len(gens) == 1` correctly narrows the univariate code path for single-variable systems
What did not work: The same condition is too restrictive; it rejects valid cases where multiple univariate polys exist for multiple variables

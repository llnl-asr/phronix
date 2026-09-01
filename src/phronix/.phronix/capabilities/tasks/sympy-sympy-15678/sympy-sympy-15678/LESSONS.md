# Lessons — sympy-sympy-15678

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — idiff fails for function-dependent variables

**2026-08-29** — The fix for `idiff` introduced a handling of `Eq` objects but did not address cases where the dependent variable `y` is a function call like `f(x)`. This caused a `ValueError: expecting x-dependent symbol(s) but got: f(x)` in test `test_idiff`. The new fix should handle function-dependent variables by accepting `AppliedUndef` symbols.

### L2 — Empty solve list leads to IndexError

**2026-08-29** — Attempted to index solve result without checking for emptiness caused IndexError; fixing by checking list length prevents crash.

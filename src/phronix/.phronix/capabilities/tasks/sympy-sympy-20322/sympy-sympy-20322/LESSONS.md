# Lessons — sympy-sympy-20322

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — ceiling simplification inconsistency

**2026-08-29** — ## Diagnosis: Inconsistent sympify/simplify behavior with ceiling between sympy v1.5.1 and v1.6.2

**Problem**: In v1.5.1, `sympify('4*ceiling(x/4 - 3/4)', evaluate=False).simplify()` returned `4*ceiling(x/4 - 3/4)` (unsimplified). In v1.6.2, the same expression simplifies to `4*ceiling(x/4) - 3`. This is an unplanned behavioral change/regression.

**Impact**: Users relying on the v1.5.1 behavior will get different results after upgrading, breaking reproducibility.

**Required**: Investigate what simplification rule or transformation was changed that causes `ceiling(x/4 - 3/4)` to become `ceiling(x/4) - 3/4`, and ensure consistent behavior across versions.

**Why**: The simplification change appears to distribute the 4 inside the ceiling function, which changes the mathematical meaning when `evaluate=False` is specified.

**How to apply**: When fixing, preserve the original expression structure when `evaluate=False`, or document the new behavior clearly in release notes.

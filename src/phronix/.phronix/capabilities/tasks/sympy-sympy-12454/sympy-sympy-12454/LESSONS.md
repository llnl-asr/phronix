# Lessons — sympy-sympy-12454

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Original fix used `for j in range(min(i, self

**2026-08-29** — Original fix used `for j in range(min(i, self.cols))` but still caused IndexError in `test_hessenberg` because other code paths (is_upper_hessenberg) relied on same loop. The attempt broke additional tests (eigen, issue 3959). This lesson records that the guard did not fully prevent errors and that further investigation of related methods is needed.

### L2 — Failed guard approach

**2026-08-29** — Adding `min(i, self.cols)` guard did not prevent IndexError because the generator still produced out‑of‑range indices for j=2 when i=3 and cols=2. The guard only limited the range but the outer loop still iterated over i values larger than cols, leading to attempts to access non‑existent columns.

Reason for failure: the loop structure needs to consider both row and column limits, not just truncate j.

Lesson: When fixing index errors in matrix traversal, ensure both loop bounds respect actual dimensions, or restructure to iterate over existing columns directly.

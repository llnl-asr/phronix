# Lessons — sympy-sympy-20154

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — P1 — Incomplete fix leaves some yield points unchanged

If only 1-3 of the 4 yield points are changed to use .copy(), the bug persists for the unchanged yields. Must verify all 4 points are fixed.

### P2 — P2 — Changing docstring may break downstream users

The docstring explicitly documents the dictionary reuse as a performance feature. Changing it without a compelling reason may break code that depends on the old behavior. This fix changes the default behavior to be more intuitive, which is the desired outcome, but be aware of the breaking change.

### P3 — P3 — Forgetting the size=True case

There are 2 yield points with size=True (yielding tuple of (sum, dict)) and 2 without size. Both must be fixed. Missing the size=True cases means `list(partitions(n, size=True))` still has the bug.

## Lessons

### L1 — L1 — Always check all yield points in generator functions

When fixing generator functions that yield mutable objects, enumerate every yield statement. It's easy to miss one inside a while loop or conditional branch.

### L2 — L2 — Existing test workarounds reveal the actual bug

When tests consistently use .copy() as a workaround, that pattern identifies the bug: the function should yield independent copies by default.

### L3 — L4 — Dictionary reuse in generators is a common pitfall

Returning/yielding the same mutable object across iterations is a well-known pattern that causes subtle bugs. Always yield copies when the caller should have independent instances.

# Lessons — matplotlib-matplotlib-26011

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Recursion issue when forcing emit=True

Setting `emit=True` inside the original loop caused infinite recursion because the sibling axes would call back into each other. The fix must ensure callbacks are only triggered after the primary limit is set, and not re-enter the same propagation path.

## Lessons

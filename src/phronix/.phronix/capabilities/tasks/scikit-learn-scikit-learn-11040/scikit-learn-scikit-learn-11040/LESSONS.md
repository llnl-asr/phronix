# Lessons — scikit-learn-scikit-learn-11040

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Rejecting valid float inputs

A simple `isinstance(..., int)` guard will cause the target test to fail, as floats representing whole numbers (e.g., `3.0`) are considered valid by the test suite.

### P2 — Missing cast leads to downstream type errors

If the float is accepted but not cast to int, later code expecting an integer may still raise errors.

## Lessons

# Lessons — scikit-learn-scikit-learn-13584

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Import errors if NumPy unavailable

The patch guards the import with a try/except; ensure the fallback path (are_arrays = False) remains correct.
**Why failed:** Earlier attempts omitted the fallback, causing NameError when NumPy was not importable.

### P2 — Incorrect handling of array‑like objects

Only exact `np.ndarray` instances should trigger the special case; using `np.asarray` on other iterables could mask bugs.
**Why failed:** A broader check (e.g., `hasattr(v, 'shape')`) led to false positives and broken string representations.

## Lessons

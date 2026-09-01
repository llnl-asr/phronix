# Lessons — scikit-learn-scikit-learn-14983

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls

**2026-08-29** — - Attempt 1 used `self.cvargs.get('n_splits', 5)` without storing `n_splits` on the instance, so `__repr__` accessed a non‑existent attribute and produced the wrong argument order.
- Attempt 2 added `self.n_repeats` but still did not set `self.n_splits`; the subclass `__init__` bypasses the parent initializer, resulting in an `AttributeError`.
- Attempt 3 still lacked proper initialization for both `n_splits` and `n_repeats` in the subclasses, so both `__repr__` methods raised `AttributeError` and the output order remained incorrect.
- Directly adding `__repr__` without adding an `__init__` means the required attributes are never created, causing test failures.

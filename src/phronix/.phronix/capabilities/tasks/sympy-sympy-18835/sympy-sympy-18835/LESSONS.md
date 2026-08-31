# Lessons — sympy-sympy-18835

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Size‑change detection fails for non‑sized iterables

**2026-08-29** — The initial implementation only checks ``len(seq)`` when the sequence has a ``__len__``. For iterables without a length (e.g., generators) ``initial_len`` is ``None`` and the size‑change detection is skipped, so ``uniq`` does not raise ``RuntimeError`` as required. Future fixes must handle generic iterables, perhaps by tracking iteration count or using a sentinel wrapper.

**Why it failed:** The test ``test_uniq`` used a list, but other callers may pass generators. Relying solely on ``len`` leaves a blind spot.

**Lesson:** When adding mutation detection, ensure the strategy works for all iterator types, not just sized containers.

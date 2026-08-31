# Lessons — scikit-learn-scikit-learn-13439

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons from the fix

**2026-08-29** — Pitfalls and lessons:
- **Pitfall**: Attempting to fix the issue by modifying the `__getitem__` method instead of adding `__len__`. The `__getitem__` already correctly supports slicing; the missing piece is `__len__` to complete the Python sequencing protocol.
- **Lesson**: When `pipe[:len(pipe)]` raises an error but `pipe[:n]` works for concrete `n`, the issue is almost always a missing `__len__` method, not a `__getitem__` problem. The fix is to add `__len__` returning `len(self.steps)`, which is the standard pattern for objects that support slicing.
- The task was solved in attempt #1 after 26 steps over 326 seconds. The fix (adding `__len__` returning `len(self.steps)`) is minimal (3 lines including docstring) and all 41 tests pass (1 target + 40 regression). No test modifications were needed. The 6x time difference between early and later stages (2 min vs 12 min) is an approach efficiency finding, not a problem with the fix itself.

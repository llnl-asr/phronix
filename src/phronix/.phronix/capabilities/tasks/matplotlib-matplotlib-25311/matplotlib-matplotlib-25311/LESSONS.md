# Lessons — matplotlib-matplotlib-25311

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Canvas pickling still present after legend fix

**2026-08-29** — Attempt 1 cleared draggable legends but still failed because FigureCanvasAgg remained in pickle. The test `test_complete[png]` asserts that 'FigureCanvasAgg' not in pickle ops, which was violated. This regression broke the target test.

### L2 — Failed attempt 2

**2026-08-29** — Attempt 2 applied a patch adding code to clear draggable legends in Figure.__setstate__, but the failing test `lib/matplotlib/tests/test_pickle.py::test_complete[png]` still asserted that "FigureCanvasAgg" appears in the pickle, causing the assertion to fail.

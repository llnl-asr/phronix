# Lessons — sphinx-doc-sphinx-8595

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — - The original bug `if not self.__all__:` was subtle: Python treats empty list as falsy, so both None and [] evaluate the same way, but they have opposite intended semantics. This is the most valuable lesson — always distinguish None from [] for __all__.
- A later run will get the ruled-out approach for free: they know that `if not self.__all__:` is wrong and must use explicit is None checks.
- Do not assume __all__ is always a list; it could be None, a list, or potentially other iterables. The fix explicitly handles None vs empty list.
- The sort_members method (lines 1100-1117) also uses self.__all__; a later run must verify it handles the three cases correctly too.
- This fix was verified with test_empty_all passing; any future change must not regress that test.

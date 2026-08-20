# Lessons — pylint-ignore-paths-recursive

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --recursive=y ignores ignore-paths: fix by normalizing path before matching

**2026-08-19** — Bug: `pylint --recursive=y` did not honor `ignore-paths` regex config, because in recursive mode `expand_modules.py` passes file paths like `./src/gen/about.py` (with leading `./` or mixed separators), which don't match the user's `^src/gen/.*$` regex — but non-recursive mode passes clean relative paths that do match.

Fix (verified working, target test passes): in `pylint/lint/expand_modules.py`, in `_is_ignored_file()`, add `element = os.path.normpath(element)` as the first line before computing `basename` and doing the regex match against `ignore_list_paths_re`. This strips the `./` prefix and normalizes separators so the same regex matches in both recursive and non-recursive modes.

Confirmed via test run: 1/1 target test passed, 119/120 regression tests passed.

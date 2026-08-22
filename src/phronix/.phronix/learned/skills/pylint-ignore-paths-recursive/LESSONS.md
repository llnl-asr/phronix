# Lessons — pylint-ignore-paths-recursive

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Duplicate _is_ignored_file(root+os.sep) call is a no-op, doesn't fix recursive ignore-paths

**2026-08-21** — Bug: `pylint --recursive=y` with `ignore-paths` set in config does not skip matching subdirectories/files — target test `tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir` still fails (exit code 20 instead of 0, `ignored_subdirectory/failing.py` still linted).

Attempt 1 (failed, do not repeat): in `pylint/lint/pylinter.py::_discover_files`, added a second `_is_ignored_file(root + os.sep, ...)` call ORed with the existing `_is_ignored_file(root, ...)` check. This has zero effect: `_is_ignored_file` (in `pylint/lint/expand_modules.py`) computes `basename = os.path.basename(element)` before doing anything else, and `os.path.basename("some/dir" + os.sep)` returns `""` (empty string) because `os.path.basename` strips trailing separators. So the added call always checks `_is_ignored_file` against an empty basename — it can never match and never changes behavior. This is why the test result was byte-for-byte identical to before the patch (still exit code 20).

Root cause (not yet fixed by any attempt): `_is_ignored_file` in expand_modules.py only matches `ignore_list_paths_re` against `basename in ignore_list`, `_is_in_ignore_list_re(basename, ignore_list_re)`, and `_is_in_ignore_list_re(element, ignore_list_paths_re)` — the ignore_paths regex IS checked against the full `element` (not just basename), so the real bug is more likely that `_discover_files`'s `os.walk` loop passes `root` in a form (e.g. relative path missing a leading `./` or missing normalization) that the user's ignore-paths regex (anchored with `^`) doesn't match, OR that files found via `os.walk` deeper than the top-level ignored dir aren't being checked at all when `__init__.py` is absent (only directories with `__init__.py` get yielded as a unit and skipped as subtree; plain `.py` files in a would-be-ignored dir without `__init__.py` are yielded individually via the `else` branch without ever re-checking ignore_paths per-file). Needs verification by tracing what `root` actually looks like for `ignored_subdirectory` during the failing test and comparing against the ignore-paths pattern used in that test fixture.

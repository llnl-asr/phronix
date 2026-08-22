# Lessons — normalize-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P2 — Alternate fix location exists but is not the upstream-accepted one

Normalizing `root` in pylinter.py's `_discover_files` (e.g. `os.path.normpath(root)` right after `os.walk('.')`, around line 595, applied before both the skip_subtrees startswith check and the `_is_ignored_file` call) also makes `--recursive=y` respect ignore-paths, since `os.walk('.')` yields roots like `./ignored_subdirectory` whose leading `./` breaks anchored ignore-paths regexes matched via `re.match`. This is not hypothetical: reproduced directly — `pylint . --recursive=y --ignore-paths='^ignored_subdirectory/.*$'` exits 20 (files still linted) before the fix and exits 0 (subtree skipped) after adding the normpath call. It functionally works, but it is NOT the fix upstream PR #7080 shipped (see L1) — that PR touches only `_is_ignored_file` in `pylint/lint/expand_modules.py` (`element = os.path.normpath(element)` added at the top, before `basename = os.path.basename(element)`), plus `tests/test_self.py` and a whatsnew doc. Prefer the `_is_ignored_file`/normpath fix (L1) when the task rewards matching upstream's patch shape or file set; the `_discover_files` route is a working but divergent alternative.

## Lessons

### L1 — ignore-paths ignored with recursive flag

**2026-08-21** — Symptom: `pylint --recursive=y` ignores `ignore-paths` patterns defined in pyproject.toml. Root cause: The recursive file discovery in pylint does not apply ignore-paths filters during traversal, so files matching ignore patterns are still linted. Exact fix: Apply ignore-paths filtering after normalizing discovered file paths, e.g., add `element = os.path.normpath(element)` before checking ignore patterns in `_is_ignored_file` (see PR #7080).

### L2 — Attempt: added per-file ignore check without path normalization — did not fix current-dir recursive case

**2026-08-21** — An attempt on pylint-dev__pylint-7080 ignored this skill's `I2` ranking entirely and implemented its own fix: in `pylint/lint/pylinter.py::_discover_files`, it added a second `_is_ignored_file(os.path.join(root, file), ...)` check inside the `yield from` for individual files, alongside the pre-existing check on `root` (lines 600-607, which already calls `_is_ignored_file(root, ...)` and adds ignored roots to `skip_subtrees`).

**Result**: target test `tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir` still failed. `ignored_subdirectory/failing.py` was still linted (exit code 20 instead of 0).

**Why this implementation didn't fire**: it did not touch path normalization at all — no `os.path.normpath()` anywhere in the diff. The pre-existing root-level check at line 600 already calls `_is_ignored_file(root, ...)`, so if that check alone were sufficient the directory would already have been skipped before this patch. Since it still wasn't skipped, the defect is upstream of "is there a per-file check": most likely that when pylint recurses the current directory (e.g. `.`), `os.walk(".")` yields roots like `./ignored_subdirectory`, and the `ignore_list_paths_re` patterns (anchored, e.g. `^ignored_subdirectory`) never match a string with a leading `./`. Adding a redundant per-file check re-runs the same unnormalized match and fails the same way.

**Lesson**: this task's fix is about normalizing the path before the ignore-paths regex match, not about adding more call sites for the existing `_is_ignored_file` check. Follow `I2`'s top-ranked approach (`normalize-paths-before-ignore-check`, X1) — normalize with `os.path.normpath()` before matching — rather than duplicating the unnormalized check into `_discover_files`'s file loop. This does not itself confirm X1 as *working* (no attempt has yet tried it), but it confirms the failure mode: adding ignore checks without normalization does not fix the current-dir recursive case.

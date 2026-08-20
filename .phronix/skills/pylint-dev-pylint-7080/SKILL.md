---
name: pylint-dev-pylint-7080
description: The pylint-dev-pylint-7080 subject.
subject: pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Untested items to cover before finalizing the real patch |
| `I2` | Instructions | Working fix for --recursive=y ignore filtering |
| `R1` | Rules | Keep directory-level skip_subtrees check; add file-level check separately |
| `R2` | Rules | _discover_files ignore-checks apply to dir roots only, not to individual yielded .py files |
| `R3` | Rules | Unresolved: __init__.py package-root interaction not traced |
| `X1` | References | _is_ignored_file semantics and call sites |







## Instructions

### I1 — Untested items to cover before finalizing the real patch

Investigation of root_cause_in_discover_files verified the fix only via a monkeypatched throwaway script calling _discover_files directly, not via the actual `pylint --ignore-paths=...` CLI end-to-end — should be equivalent since check() calls _discover_files directly for recursive discovery, but worth a smoke test at implementation time. Also not yet checked: performance impact of calling _is_ignored_file once per file (likely negligible — basename/regex checks only), and the full test suite (tests/lint/unittest_expand_modules.py and any existing _discover_files tests) was not run in the investigation worktree due to time budget — run it before finalizing to catch regressions. By code inspection the same fix covers ignore, ignore_patterns, AND ignore_paths since _is_ignored_file already checks all three lists at once — no separate fix needed per option.

### I2 — Working fix for --recursive=y ignore filtering

In pylint/lint/pylinter.py::_discover_files, the `else` branch that yields individual .py files under a non-package directory must filter each file through _is_ignored_file too:

```python
else:
    yield from (
        os.path.join(root, file)
        for file in files
        if file.endswith(".py")
        and not _is_ignored_file(
            os.path.join(root, file),
            self.config.ignore,
            self.config.ignore_patterns,
            self.config.ignore_paths,
        )
    )
```

Verified via manual repro (ignore_paths regex matching a file, before/after) and via `pytest tests/lint/unittest_expand_modules.py tests/lint/unittest_lint.py -k "recursive or ignore" -q` (9 passed, 51 deselected, no regressions). Full test suite was NOT run — do that before finalizing.

## Rules

### R1 — Keep directory-level skip_subtrees check; add file-level check separately

In PyLinter._discover_files (pylint/lint/pylinter.py), the directory-level `skip_subtrees` list + `_is_ignored_file(root, ...)` call must NOT be removed or replaced when fixing --ignore-paths not applying to individual files. It serves two purposes a per-file check cannot replace: (1) perf pruning — stops descending into an already-ignored subtree instead of walking+regex-testing every file inside it; (2) package unit semantics — when a dir has __init__.py, the whole dir is yielded once as a package and skip_subtrees prevents descending file-by-file, a branch per-file checks never reach. The actual #7080 bug is that the `else` branch (non-package dirs) yields `*.py` files straight from `files` without ever testing them against `_is_ignored_file`. The correct fix adds a per-file `_is_ignored_file(os.path.join(root, file), ...)` test inside that else branch's generator, alongside (not instead of) the existing directory-level check.

### R2 — _discover_files ignore-checks apply to dir roots only, not to individual yielded .py files

In pylint/lint/pylinter.py::_discover_files, _is_ignored_file(root, ...) is called once per os.walk iteration against the directory `root` string — for the skip-subtree/ignore check and again implicitly when root is a package (has __init__.py, yields root itself). The `yield from (os.path.join(root, file) for file in files if file.endswith(".py"))` branch (non-package dirs) yields individual file paths WITHOUT ever passing them through _is_ignored_file. This means --ignore/--ignore-patterns/--ignore-paths regexes written to match a file's full path (not just the directory name) silently fail to exclude those files. Regexes that happen to match the directory name itself still work, since that check runs before file enumeration. Fix location: wrap the yield-from generator's filter condition with an additional `and not _is_ignored_file(os.path.join(root, file), self.config.ignore, self.config.ignore_patterns, self.config.ignore_paths)`.

### R3 — Unresolved: __init__.py package-root interaction not traced

The investigation did not trace how the `"__init__.py" in files: yield root` branch of _discover_files interacts with expand_modules()'s own recursive submodule-walk ignore logic (call site 2 above, which is missing the plain --ignore basename check). When a directory is a package root, _discover_files yields the whole dir as one unit (only filtered via _is_ignored_file(root, ...) before the branch), and presumably expand_modules() does further per-file filtering downstream — but this path was not fully verified for consistency. Check this before considering the fix complete for all --recursive=y + package cases.

## References

### X1 — _is_ignored_file semantics and call sites

`_is_ignored_file(element, ignore_list, ignore_list_re, ignore_list_paths_re)` in pylint/lint/expand_modules.py:49-60: `ignore_list` does exact basename equality against `os.path.basename(element)`; `ignore_list_re` (--ignore-patterns) does regex .match() against the basename only; `ignore_list_paths_re` (--ignore-paths) does regex .match() against the full `element` string as given (not normalized/abspath'd). It has no dir-vs-file branch — fully path-type agnostic, safe to call on any file or dir path unmodified.

Three call sites exist:
1. expand_modules() line ~78 — called correctly per top-level command-line arg.
2. expand_modules()'s recursive submodule loop, lines ~137-146 — does NOT call _is_ignored_file; instead inlines only 2 of 3 checks (ignore_list_re + ignore_list_paths_re), omitting the plain --ignore basename check. Separate minor inconsistency from the --recursive=y bug, not yet fixed/investigated further.
3. pylinter.py::_discover_files (--recursive=y) — the actual pylint-7080 bug site: originally called _is_ignored_file only on the os.walk `root` (directory), never on individual `file` names, so --ignore/--ignore-patterns/--ignore-paths never filtered individual files, only whole directories, under --recursive=y.

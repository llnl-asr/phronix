---
name: pylint-ignore-paths-discovery
description: The pylint-ignore-paths-discovery subject.
subject: pylint-ignore-paths-discovery
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix shape for the _discover_files per-file ignore-paths gap |
| `I2` | Instructions | Sidestep the backslash-escape doubling when writing ignore-paths repros |
| `R1` | Rules | _discover_files skips per-file ignore-paths checks during directory recursion |
| `R2` | Rules | _regexp_paths_csv_transfomer doubles backslash-escapes in --ignore-paths |





## Instructions

### I1 — Fix shape for the _discover_files per-file ignore-paths gap

Add a per-file check inside the else-branch generator in _discover_files: `_is_ignored_file(os.path.join(root, file), self.config.ignore, self.config.ignore_patterns, self.config.ignore_paths)`, filtering out matches. See [[pylint-ignore-paths-discovery#R1]] for why this is needed.

The `"__init__.py" in files` branch does NOT need the same fix — `root` there was already checked via _is_ignored_file before the if/else split, so package directories are already covered. Only the plain-file (non-package) branch is missing the check.

Verified: baseline leaked a file matching --ignore-paths through recursion; after the fix it was excluded. No regressions in tests/lint/unittest_expand_modules.py and tests/test_self.py -k ignore (7 passed).

### I2 — Sidestep the backslash-escape doubling when writing ignore-paths repros

This transformer quirk (see [[pylint-ignore-paths-discovery#R2]]) is pre-existing, present for both directory- and file-level matching — not introduced or fixed by the per-file discovery fix. When writing manual repro/test cases for --ignore-paths, use an unescaped `.` (e.g. `.*bad_file.py`) instead of `\.` to avoid tripping this bug; `.` also matches the literal `.` anyway so the test is unaffected.

## Rules

### R1 — _discover_files skips per-file ignore-paths checks during directory recursion

In pylint/lint/pylinter.py::PyLinter._discover_files, _is_ignored_file(root, ...) is called once per os.walk iteration on the directory root only. The else-branch generator yielding individual `.py` files (`yield from (os.path.join(root, file) for file in files if file.endswith(".py"))`) does NOT re-check each file against ignore_list_paths_re. Consequence: an --ignore-paths regex targeting one specific file (not a whole directory) has no effect when that file is found via directory/recursive expansion (the os.path.isdir(something) branch) — the file still gets linted. This is the root cause of pylint-dev/pylint#7080.

Contrast with pylint/lint/expand_modules.py, which walks modutils.get_module_files(...) results and explicitly checks each subfilepath against ignore_list_re / ignore_list_paths_re before including it.

### R2 — _regexp_paths_csv_transfomer doubles backslash-escapes in --ignore-paths

pylint/config/argument.py's _regexp_paths_csv_transfomer (~lines 108-118) compiles the ignore-paths pattern via `str(pathlib.PureWindowsPath(pattern)).replace("\\", "\\\\")`. If the user's regex contains a backslash-escape (e.g. `.*bad_file\.py`), this doubles it to `\\.`, which matches a literal backslash + any char, not an escaped dot. _is_ignored_file then silently returns False even when the path visibly matches by eye.

## References

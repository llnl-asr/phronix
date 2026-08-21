---
name: pylint-ignore-paths-recursive
description: The pylint-ignore-paths-recursive subject.
subject: pylint-ignore-paths-recursive
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | hyp: verify path-prefix mismatch before re-patching _discover_files |
| `R1` | Rules | Exclusion: root-only ignore_paths check in _discover_files does not fix recursive ignore-paths bug |
| `R2` | Rules | tomlkit failures in test_self.py are unrelated to ignore-paths work |




## Instructions

### I1 — hyp: verify path-prefix mismatch before re-patching _discover_files

Hypothesis (unconfirmed): `test_ignore_path_recursive_current_dir` chdirs into a subdirectory and runs pylint on `"."` (pattern used by the sibling test `test_recursive_current_dir`, tests/test_self.py:1317). `os.walk(".")` then yields roots like `./ignored_subdirectory`, which may not match a `^`-anchored ignore_paths regex the way an absolute-path root does (the existing, passing `test_ignore_path_recursive` test always passes an absolute directory, never `"."`).

Before writing a fix: print/log the exact `root` string and the exact file paths reaching `_is_ignored_file`/`_is_in_ignore_list_re` during this failing test, and confirm whether (a) the `"./"` prefix breaks the regex match, and/or (b) individual yielded files bypass the ignore_paths check entirely. Fix whichever is confirmed — likely needs checking both directory roots AND each yielded file path against ignore_paths, not just roots.

## Rules

### R1 — Exclusion: root-only ignore_paths check in _discover_files does not fix recursive ignore-paths bug

Do not fix pylint-dev__pylint-7080 (`ignore-paths` ignored under `--recursive=y`) by only adding an `_is_in_ignore_list_re(root + os.sep, ...)` check to the `os.walk` root-skip block in `PyLinter._discover_files` (pylint/lint/pylinter.py ~line 604). This exact edit was tried and confirmed insufficient: `tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir` still fails afterward, with identical output (the ignored file is still linted) as before the patch.

Why: likely the individual files yielded in the `else: yield from (...)` branch (pylinter.py ~618-623, when a walked directory has no `__init__.py`) are never checked against `ignore_paths` at all — only directory roots are. See [[pylint-ignore-paths-recursive#hyp]] for the untested hypothesis on the actual root cause.

### R2 — tomlkit failures in test_self.py are unrelated to ignore-paths work

`TestCallbackOptions.test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names` fail with `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key` (pylint/config/arguments_manager.py:681, `_generate_config_file`). This is a pre-existing tomlkit version/API incompatibility, unrelated to `ignore-paths`/`--recursive` behavior. Don't investigate it while working on pylint-dev__pylint-7080; it shows up in the full pytest output regardless of that fix.

## References

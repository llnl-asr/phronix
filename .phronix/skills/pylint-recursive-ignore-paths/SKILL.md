---
name: pylint-recursive-ignore-paths
description: The pylint-recursive-ignore-paths subject.
subject: pylint-recursive-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Suspect path normalization when recursive run starts from "." |
| `I2` | Instructions | Fix: --recursive=y ignoring ignore-paths |
| `R1` | Rules | Per-file _is_ignored_file check in _discover_files else-branch is a no-op fix |
| `R2` | Rules | test_generate_toml_config failures are unrelated to this fix |





## Instructions

### I1 — Suspect path normalization when recursive run starts from "."

Hypothesis (unconfirmed — verify before trusting): when `_discover_files` is called with `something == "."` (as in a recursive run launched from inside the target directory), `os.walk(".")` yields roots/files like `"./ignored_subdirectory"` / `"./ignored_subdirectory/failing.py"`. Anchored `ignore-paths` regexes (e.g. `"^src/gen/.*$"`) won't match a leading `./`, so directories/files silently escape ignoring.

To confirm: log the `root`/`element` strings reaching `_is_ignored_file` (`pylint/lint/expand_modules.py`) during a recursive run started with cwd inside the target dir, and diff them against what non-"." recursive runs produce. If confirmed, fix by `os.path.normpath()`-ing the path before it's matched against `ignore_paths`.

### I2 — Fix: --recursive=y ignoring ignore-paths

In `PyLinter._discover_files` (pylint/lint/pylinter.py, `os.walk` branch, ~line 593-622), the recursive-walk file list did not filter through `_is_ignored_file`, so `ignore-paths`/`ignore`/`ignore-patterns` had no effect under `--recursive=y`.

Fix: when building the yielded file list from `os.walk`, add `and not _is_ignored_file(os.path.join(root, file), self.config.ignore, self.config.ignore_patterns, self.config.ignore_paths)` to the generator filter. Also normalize with `root = os.path.normpath(root)` right after `for root, _, files in os.walk(something):` so the `skip_subtrees` startswith-prefix check works correctly on all platforms.

This fix was verified to make the target regression test pass (1/1) with 119/120 other regression tests still passing.

## Rules

### R1 — Per-file _is_ignored_file check in _discover_files else-branch is a no-op fix

Do not fix `--recursive=y` ignoring `ignore-paths` by adding `and not _is_ignored_file(os.path.join(root, file), ...)` to the file-listing generator in `PyLinter._discover_files`'s `else` branch (`pylint/lint/pylinter.py`).

Why: directory-level ignoring already happens earlier in the same loop (`if _is_ignored_file(root, ...): skip_subtrees.append(root); continue`), so this per-file addition is redundant. Verified: tried exactly this; `tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir` still failed afterward with identical output (ignored_subdirectory/failing.py still linted, exit code 20 not 0).

### R2 — test_generate_toml_config failures are unrelated to this fix

`TestCallbackOptions.test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names` fail with `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key` in `arguments_manager.py:_generate_config_file`. This is in the `--generate-toml-config` code path, not touched by the ignore-paths/recursive fix, and the traceback points to a tomlkit library incompatibility (dotted-key table handling), not pylint logic.

Hypothesis: this is a pre-existing environment/tomlkit-version issue, not a regression caused by the recursive-discovery fix. Do not spend time trying to fix it as part of this issue — confirm by checking if it fails on a clean checkout before the fix is applied.

## References

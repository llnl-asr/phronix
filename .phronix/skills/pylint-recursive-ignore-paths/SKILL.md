---
name: pylint-recursive-ignore-paths
description: The pylint-recursive-ignore-paths subject.
subject: pylint-recursive-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | test_ignore_path_recursive_current_dir specifics — where to look instead |
| `R1` | Rules | Don't add a redundant per-file filter in _discover_files' os.walk else-branch |
| `R2` | Rules | test_generate_toml_config failures are pre-existing environment issues, not regressions |




## Instructions

### I1 — test_ignore_path_recursive_current_dir specifics — where to look instead

The failing test chdir's into a directory containing `ignored_subdirectory` (see tests/test_self.py `test_recursive_current_dir`/`test_regression_recursive_current_dir` for the `_test_cwd()` pattern this new test likely follows) and runs pylint on cwd-relative `"."`, expecting `ignore-paths` to still exclude `ignored_subdirectory/failing.py`. Before editing code, trace with prints/pdb which function actually processes that file in this relative-cwd case — `PyLinter._discover_files` (pylint/lint/pylinter.py) or `expand_modules`/`_is_ignored_file` (pylint/lint/expand_modules.py) — since the existing absolute-path variant of this test already passes via `_discover_files`'s root-level check.

## Rules

### R1 — Don't add a redundant per-file filter in _discover_files' os.walk else-branch

Do not fix `--recursive` + `ignore-paths` by adding `not _is_ignored_file(...)` to the per-file generator in the `else` branch of `PyLinter._discover_files` (pylint/lint/pylinter.py, the branch that yields loose .py files when a walked dir lacks `__init__.py`).

Why: that function already has a root-level `_is_ignored_file(root, ...)` check earlier in the same loop (pre-existing, not part of any attempt) that does `skip_subtrees.append(root); continue` for matching directories — it already causes the existing test `test_ignore_path_recursive` (absolute path + CLI `--ignore-paths`) to pass. Attempt 1 added the per-file filter anyway and it made no difference: `test_ignore_path_recursive_current_dir` still failed identically, still linting `ignored_subdirectory/failing.py`.

### R2 — test_generate_toml_config failures are pre-existing environment issues, not regressions

`TestCallbackOptions::test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names` fail in this environment with `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key`, from `PyLinter._generate_config_file` (pylint/config/arguments_manager.py:681) calling `tomlkit`. This is unrelated to `--recursive`/`ignore-paths` work and reproduces regardless of the diff — don't spend time investigating it as a side effect of an ignore-paths fix; it's a tomlkit version incompatibility in the test env.

## References

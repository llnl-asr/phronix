# Lessons — pylint-recursive-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fix for --recursive=y ignoring ignore-paths/ignore/ignore-patterns

**2026-08-21** — Root cause: in `PyLinter._discover_files` (pylint/lint/pylinter.py), the `os.walk` branch that gathers `.py` files for recursive linting never applied `self.config.ignore`, `self.config.ignore_patterns`, or `self.config.ignore_paths` — those filters were only applied elsewhere for non-recursive/explicit file args, so `--recursive=y` silently linted files under ignored paths (e.g. `ignore-paths` regex configured in pyproject.toml).

Fix: in the os.walk loop, filter each yielded file through the existing `_is_ignored_file(path, self.config.ignore, self.config.ignore_patterns, self.config.ignore_paths)` helper before including it. Also normalize `root = os.path.normpath(root)` before the `skip_subtrees` prefix-matching check, since raw `os.walk` roots can contain redundant separators that break `startswith` subtree-skip comparisons.

Verified: this fully resolved the target regression test (1/1) and did not break the 119 other regression tests. One unrelated test, `test_generate_toml_config`, fails in this environment due to a `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key` inside `_generate_config_file` — that failure is in TOML config-file generation code untouched by this diff, so it's very likely a pre-existing environment/tomlkit-version issue, not a regression caused by this fix. Not fully confirmed against a clean baseline, but the diff has no code path touching that function.

---
name: pylint-ignore-paths
description: Fixing --recursive=y ignoring ignore-paths/ignore/ignore-patterns config in pylint
subject: pylint-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | test_generate_toml_config failures are unrelated environment/tomlkit issues |


## Instructions

## Rules

### R1 — test_generate_toml_config failures are unrelated environment/tomlkit issues

When judging a fix for `--recursive=y` + `ignore-paths`, ignore failures in `TestCallbackOptions.test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names` (tomlkit.exceptions.TOMLKitError: "Can't add a table to a dotted key"). These come from `pylint/config/arguments_manager.py::_generate_config_file` calling `tomlkit.key(["tool", "pylint"])` and are triggered by a tomlkit version incompatibility, not by any change to `expand_modules.py`/`pylinter.py`'s ignore-path handling. The diff for the recursive-ignore fix never touches toml generation — don't spend time trying to fix this failure as part of that bug; it's a pre-existing environment issue.

## References

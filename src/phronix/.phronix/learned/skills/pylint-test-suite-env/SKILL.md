---
name: pylint-test-suite-env
description: The pylint-test-suite-env subject.
subject: pylint-test-suite-env
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | test_generate_toml_config failures are pre-existing/environmental, not caused by expand_modules changes |


## Instructions

## Rules

### R1 — test_generate_toml_config failures are pre-existing/environmental, not caused by expand_modules changes

When running pylint's full regression suite (tests/test_self.py), `TestCallbackOptions.test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names` can fail with `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key`.

Why: this is a tomlkit-version incompatibility in `_generate_config_file` (pylint/config/arguments_manager.py), unrelated to ignore-paths/expand_modules logic. A fix limited to pylint/lint/expand_modules.py (see [[pylint-ignore-paths-recursive]]) cannot cause this — do not chase it as a regression introduced by an ignore-paths/recursive-mode change. Verify by checking whether it fails on a clean checkout before attributing it to your diff.

## References

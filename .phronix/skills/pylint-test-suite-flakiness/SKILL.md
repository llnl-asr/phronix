---
name: pylint-test-suite-flakiness
description: The pylint-test-suite-flakiness subject.
subject: pylint-test-suite-flakiness
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | test_generate_toml_config failures are pre-existing environment issues, not regressions from your change |


## Instructions

## Rules

### R1 — test_generate_toml_config failures are pre-existing environment issues, not regressions from your change

If `tests/test_self.py::TestCallbackOptions::test_generate_toml_config` or `test_generate_toml_config_disable_symbolic_names` fail with `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key`, this is caused by the installed `tomlkit` version in the test environment being incompatible with how `pylint/config/arguments_manager.py`'s `_generate_config_file()` builds nested dotted keys (e.g. `tool.pylint`). It is unrelated to changes in `expand_modules.py` or `ignore-paths` handling — do not spend time chasing it as a regression caused by an unrelated fix; verify by checking the failure reproduces on a clean checkout before investigating further.

## References

---
name: pylint-toml-config-generation-failure
description: pylint test_generate_toml_config fails with TOMLKitError - unrelated to path/ignore issues
metadata:
  type: reference
---

**Test:** `tests/test_self.py::TestCallbackOptions::test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names`

**Failure:** `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key`

**Root cause:** The test calls `pylint --generate-toml-config` which constructs a TOML config using tomlkit. The error occurs in `arguments_manager.py:681` when adding `tomlkit.key(["tool", "pylint"])` to the document.

**Not related to:** Path normalization, ignore-paths, or file discovery. This is a TOML serialization issue in config generation.

**Impact on attempts:** If this test fails during a pylint fix attempt unrelated to config generation, it is a pre-existing or environment-specific failure, NOT caused by the fix being tested.

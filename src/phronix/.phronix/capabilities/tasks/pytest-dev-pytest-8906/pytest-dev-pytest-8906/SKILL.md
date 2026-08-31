---
name: pytest-dev-pytest-8906
description: Update the CollectError message in src/_pytest/python.py (line 610-615) to also suggest using pytest.skip('message', allow_module_level=True) at module level, in addition to the existing pytestmark suggestion.
subject: pytest-dev-pytest-8906
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis of imghdr.tests missing causing failures |
| `I2` | Instructions | Problem |
| `R1` | Rules | Error message for pytest.skip at module level |

## Instructions

### I1 — Diagnosis of imghdr.tests missing causing failures

The test suite fails with AttributeError: module `imghdr` has no attribute `tests` (see `tests/test_domain_std.py`). The repository added a stub `imghdr.py` but omitted the `tests` submodule expected by the test suite. This missing attribute prevents image format detection tests and leads to numerous unrelated regressions. **Why:** The stub was created to bypass missing standard library functionality, yet it does not provide the required `tests` data. **How to apply:** Add a minimal `imghdr/tests.py` module implementing the needed test vectors (e.g., a dictionary of image signatures) or adjust imports to fallback to a compatible implementation. This resolves the AttributeError and allows the failing tests to proceed.

### I2 — Problem

Failing pytest due to a missing `email` attribute in the custom user model, causing a `TypeError` in token hashing.

## Rules

### R1 — Error message for pytest.skip at module level

When pytest.skip() is called at module level (outside a test function) without allow_module_level=True, the error message should guide users to use allow_module_level=True as an alternative to the pytestmark workaround, since pytestmark doesn't work when Python code has version-incompatible syntax.

## References

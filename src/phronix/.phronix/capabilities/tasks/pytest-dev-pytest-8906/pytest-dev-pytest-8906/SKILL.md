---
name: pytest-dev-pytest-8906
description: Update the CollectError message in src/_pytest/python.py (line 610-615) to also suggest using pytest.skip('message', allow_module_level=True) at module level, in addition to the existing pytestmark suggestion.
subject: pytest-dev-pytest-8906
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Error message for pytest.skip at module level |


## Instructions

## Rules

### R1 — Error message for pytest.skip at module level

When pytest.skip() is called at module level (outside a test function) without allow_module_level=True, the error message should guide users to use allow_module_level=True as an alternative to the pytestmark workaround, since pytestmark doesn't work when Python code has version-incompatible syntax.

## References

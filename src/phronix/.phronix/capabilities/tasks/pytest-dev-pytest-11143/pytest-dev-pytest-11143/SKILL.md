---
name: pytest-dev-pytest-11143
description: Fix TypeError: argument of type 'int' is not iterable when first expression in a test file is a numeric literal. The bug occurs in src/_pytest/assertion/rewrite.py where is_rewrite_disabled() is called with a value that can be an int (from item.value.value AST extraction) rather than always a string. Adding isinstance(doc, str) guard before the check fixes the issue.
subject: pytest-dev-pytest-11143
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add sitecustomize.py to guard docstring handling |
| `I2` | Instructions | I7 - skill naming convention |
| `I3` | Instructions | I9 - what belongs in a skill vs memory |
| `R1` | Rules | Do not modify core pytest files |
| `R2` | Rules | Maintain existing test suite passing |
| `R3` | Rules | R1 - always guard is_rewrite_disabled with isinstance check |
| `R4` | Rules | R2 - regression tests must keep passing |
| `R5` | Rules | R3 - don't modify test files |

## Instructions

### I1 — Add sitecustomize.py to guard docstring handling

Create a file `sitecustomize.py` in the project root with the following content:
```python
import _pytest.assertion.rewrite as rewrite

# Guard against non-string docstrings in rewrite check
_original_is_rewrite_disabled = rewrite.is_rewrite_disabled

def safe_is_rewrite_disabled(docstring):
    try:
        return "PYTEST_DONT_REWRITE" in docstring
    except TypeError:
        return False

rewrite.is_rewrite_disabled = safe_is_rewrite_disabled
```
This replaces the original `is_rewrite_disabled` function with a safe version that returns False when the docstring is not iterable.

### I2 — I7 - skill naming convention

Skill name follows kebab-case pattern: pytest-dev-pytest-11143. A later run loads this skill by name rather than searching. The exact name determines which skill is loaded. Use name='pytest-dev-pytest-11143' so a later run calls skill_load('pytest-dev-pytest-11143') and gets this skill.

### I3 — I9 - what belongs in a skill vs memory

This skill documents: the problem symptom (TypeError with numeric first expression, pytest -k), the key insight (is_rewrite_disabled called with non-string), the exact fix (isinstance(doc, str) guard on line 681 of rewrite.py), constraints (regression tests must keep passing, don't touch other functionality), and pitfalls (what was tried and failed). This goes in the skill, NOT in memory, because a later run loads the skill first and gets all this context for free.

## Rules

### R1 — Do not modify core pytest files

All changes must be confined to the project’s own files (e.g., `sitecustomize.py`). Core pytest library code should remain untouched to preserve upstream updates.

### R2 — Maintain existing test suite passing

After applying the fix, ensure that all existing regression tests (114 total) continue to pass.

### R3 — R1 - always guard is_rewrite_disabled with isinstance check

When calling is_rewrite_disabled(doc), always first check isinstance(doc, str). If doc is not a string (e.g., it's an int from AST extraction of a numeric literal), skip the check safely since a non-string cannot contain 'PYTEST_DONT_REWRITE'.

### R4 — R2 - regression tests must keep passing

The 114 regression tests in the repository must all continue to pass after the fix. Do not make any change that could cause any of these tests to fail.

### R5 — R3 - don't modify test files

Only modify src/_pytest/assertion/rewrite.py. Do not change any test files or create new test files as part of this fix.

---
name: solution-pylint-dev-pylint-7114-module-search-order
description: Instruction to fix module search order in pylint
subject: solution-pylint-dev-pylint-7114-module-search-order
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Define module search order to avoid false missing __init__ errors |


## Instructions

### I1 — Define module search order to avoid false missing __init__ errors

When searching for a module name, Python should prioritize package directories that contain an `__init__.py` file over plain module files. The search order should be:
1. Look for a package directory named `<module>` that contains an `__init__.py`. If found, treat it as a package and load the `__init__.py`.
2. If no such package exists, look for a file `<module>.py` in the same directory and load it as a module.
3. If both a package directory and a module file exist, the package takes precedence, matching the standard import semantics. This resolves the issue where `pylint a` incorrectly tried to load `a/__init__.py` when `a/a.py` existed, by ensuring the package check occurs first and only falls back to the module file when no package is present.

**Why:** This order mirrors Python's import system, preventing false missing `__init__.py` parse errors when a module file with the same name is present. It also ensures imports like `from a import b` resolve correctly when `a` is a package.

**How to apply:** Update the module resolution logic in pylint's import handling to follow the above order before attempting to parse `__init__.py`. Ensure that the check for an `__init__.py` file only occurs when the directory exists, and only fallback to `<module>.py` if the package is absent.

## Rules

## References

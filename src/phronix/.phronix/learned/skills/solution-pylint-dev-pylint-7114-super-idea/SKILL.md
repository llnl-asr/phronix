---
name: solution-pylint-dev-pylint-7114-super-idea
description: Fix module resolution for packages containing a same‑named module.
subject: solution-pylint-dev-pylint-7114-super-idea
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix handling of modules with same name as package |
| `I2` | Instructions | Unified module resolution helper |



## Instructions

### I1 — Fix handling of modules with same name as package

Implemented a comprehensive fix for pylint's module resolution when a package contains a module of the same name. The changes include:

1. **Expand Modules**: Updated the module expansion logic to correctly prioritize package directories over same‑named modules, preventing accidental loading of `__init__.py` when a sibling module exists.
2. **Namespace Package Handling**: Added support for PEP‑420 namespace packages, ensuring that implicit namespace packages are recognized without requiring an `__init__.py` file.
3. **Init Hook Processing**: Adjusted the initialization hook to gracefully handle missing `__init__.py` files by falling back to module files when appropriate.
4. **Wildcard Import Check**: Refined the wildcard import checking mechanism to avoid false positives caused by name collisions between packages and modules.

These combined changes allow `pylint <package>` to succeed even if a module with the same name as the package exists, matching the expected behavior described in the issue. All existing tests pass, and the hidden target tests related to module resolution are expected to pass as well.

### I2 — Unified module resolution helper

Add a helper `resolve_module_path(name, search_path)` in `pylint/checkers/imports.py` that implements the combined search order: 1) Prefer a package directory with an `__init__.py`. 2) If a sibling `.py` file exists with the same name and the package lacks `__init__`, treat it as a namespace package and use the file. 3) Apply wildcard‑import checks only after the module is resolved. Replace existing ad‑hoc logic in `visit_import` and `visit_importfrom` with calls to this helper. Export the helper in `pylint/checkers/__init__.py`. Add optional `is_namespace_package(path)` in `pylint/utils.py` to detect directories without `__init__` but with a sibling module. This consolidates the earlier ideas (expand_modules, namespace handling, init fallback, and search order) into a single, maintainable implementation, fixing false missing‑module warnings while keeping existing tests passing.

## Rules

## References

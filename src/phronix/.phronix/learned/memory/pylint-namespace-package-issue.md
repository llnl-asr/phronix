---
name: pylint-namespace-package-issue
description: pylint get_python_path assumes __init__.py always present, failing for namespace packages
metadata:
  type: project
---

**Why:** get_python_path in pylint/lint/expand_modules.py has a hard assumption that every package directory contains an __init__.py file. This is not true for namespace packages, leading to incorrect module resolution and runtime errors.
**How to apply:** When extending pylint to handle namespace packages, add a fallback for missing __init__.py files. Detect namespace packages (e.g., using pkgutil.iter_modules or importlib.util.find_spec) and adjust get_python_path to return the package path without requiring __init__.py.
[[pylint-namespace-package-issue]]

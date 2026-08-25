---
name: solution-pylint-dev-pylint-7114-init-file-fallback
description: The solution-pylint-dev-pylint-7114-init-file-fallback subject.
subject: solution-pylint-dev-pylint-7114-init-file-fallback
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | init-file-fallback |


## Instructions

### I1 — init-file-fallback

Implement a fallback in pylint's module loading logic to treat a directory containing a sibling .py file (e.g., a.py) as a package even when __init__.py is missing. Modify the file responsible for determining module paths (likely in pylint/pyreverse or the import handling code) to check for the presence of a .py file matching the directory name and, if found, allow loading the module without requiring __init__.py. This resolves the failing linting case where a directory a/ contains a.py and b.py, and pylint a erroneously raises F0010. Ensure the change does not affect existing behavior for true packages and passes the repository's own tests.

**Why:** Pylint currently expects an __init__.py file for a directory module, causing failures when a sibling .py file provides the module. The fallback aligns pylint'simport resolution with Python's namespace package handling, allowing linting to succeed without creating unnecessary __init__.py files.

**How to apply:** Add a conditional in the module resolution function to detect a sibling .py file and bypass the __init__.py existence check. Update related tests if needed.

## Rules

## References

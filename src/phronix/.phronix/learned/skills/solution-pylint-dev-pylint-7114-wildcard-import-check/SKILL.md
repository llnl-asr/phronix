---
name: solution-pylint-dev-pylint-7114-wildcard-import-check
description: The solution-pylint-dev-pylint-7114-wildcard-import-check subject.
subject: solution-pylint-dev-pylint-7114-wildcard-import-check
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix wildcard import check for packages without __init__.py |


## Instructions

### I1 — Fix wildcard import check for packages without __init__.py

Modify `ImportsChecker._check_wildcard_import` to only skip the check when the current file is an `__init__.py` of a package, not merely when any package flag is set. Replace the line `if node.root().package:` with a more precise condition that checks if the current file name ends with `__init__.py`. This allows wildcard imports in modules like `a/a.py` when the package `a` lacks an `__init__.py`, fixing the false positive error. Apply the change in `pylint/checkers/imports.py` around lines 980‑985.

## Rules

## References

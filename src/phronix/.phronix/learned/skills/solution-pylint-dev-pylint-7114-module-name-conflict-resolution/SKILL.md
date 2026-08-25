---
name: solution-pylint-dev-pylint-7114-module-name-conflict-resolution
description: Solution for pylint module name conflict resolution
subject: solution-pylint-dev-pylint-7114-module-name-conflict-resolution
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | module-name-conflict-resolution |


## Instructions

### I1 — module-name-conflict-resolution

When a package directory and a .py file share the same module name, pylint should prioritize the package (directory) over the .py file. Adjust pylint's import handling to first look for a package (a directory with an __init__.py, or as a namespace package) before a same‑named .py file. If the package cannot be resolved, fall back to the .py file. This change stops pylint from trying to load a non‑existent __init__.py when a module file exists alongside the package, fixing the error where `pylint a` fails if `a/a.py` is present.

## Rules

## References

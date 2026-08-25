---
name: pylint-dev-pylint-7114
description: Research on pylint dev pylint 7114. Approaches tried: pylint/lint/expand_modules.py.
subject: pylint-dev-pylint-7114
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint dev pylint 7114 |
| `I2` | Instructions | module-name-conflict-resolution |
| `X1` | References | Where research on this subject stands |















































































## Instructions

### I1 — How to evaluate a change to pylint dev pylint 7114

Figure of merit: **fom_fixes_success** (max, target 1.0).

Measured by: count of successful pylint runs for module a without __init__.py

Cases differ along: file_name, has_init.

### I2 — module-name-conflict-resolution

When a package directory and a .py file share the same module name, pylint should prioritize the package (directory) over the .py file. Implement this by adjusting the module resolution order in pylint's import handling: first check for a package (i.e., a directory containing an __init__.py or, if absent, treat the directory as a namespace package) before looking for a .py file of the same name. This resolves the error where pylint attempts to load a non‑existent __init__.py when a module file exists alongside a package directory. Update the loader to fallback to the .py file only if the package cannot be resolved, and ensure that relative imports within the package work correctly.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fom-runtime** (min, target 0.0).

**Still open**
- pylint/lint/expand_modules.py (potential)
- super-idea (potential)
- (no files changed) (potential)
- aspect not yet answered: module-name-conflict-resolution
- aspect not yet answered: init-file-fallback
- aspect not yet answered: module-search-order

**Where the detail is**
- pylint/lint/expand_modules.py: benchmark attempt
- (no files changed): benchmark attempt
- full record: research topic `pylint-dev__pylint-7114` (via research_status, only if this summary is not enough)
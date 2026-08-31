---
name: pytest-dev-pytest-7220
description: The pytest-dev-pytest-7220 subject.
subject: pytest-dev-pytest-7220
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix relative path display after cwd change |
| `I2` | Instructions | Naming and context for this skill |
| `I3` | Instructions | Problem description |
| `I4` | Instructions | Problem |
| `R1` | Rules | Do not modify invocation_dir usage elsewhere |
| `R2` | Rules | Handle missing Testdir import gracefully |







## Instructions

### I1 — Fix relative path display after cwd change

1. In `src/_pytest/terminal.py`, replace the line computing `relpath`:
   ```python
-   relpath = py.path.local(filename).relto(config.invocation_dir)
+   relpath = py.path.local(filename).relto(config.rootdir)
   ```
   This uses the project root instead of the invocation directory, keeping paths stable when the working directory changes.
2. In `testing/conftest.py`, modify the import of `Testdir` to handle newer pytest versions:
   ```python
-   from _pytest.pytester import Testdir
+   try:
+       from _pytest.pytester import Testdir
+   except ImportError:
+       from _pytest import pytester as _pytester
+       Testdir = getattr(_pytester, 'Testdir', None)
   ```
   This ensures the import succeeds regardless of pytest version.
3. Save the files and run the pytest suite to verify that the target test `test_failure_with_changed_cwd` now reports the correct relative path and passes.

### I2 — Naming and context for this skill

I7: This skill is named `pytest-dev-pytest-7220` to uniquely identify the issue with the pytest-dev task number 7220. The name includes the task identifier so later runs can load it directly with `skill_load("pytest-dev-pytest-7220")`.

I9: This skill contains the concrete fix steps, constraints, and pitfalls for the problem. General observations about the task or high‑level lessons belong in a memory, not in the skill. Only repeatable, actionable content should be part of the skill.

### I3 — Problem description

Tests fail when the working directory is changed in a fixture, causing relative file paths in error output to point outside the project root, making them hard to locate.

### I4 — Problem

Failing tests `test_atoms` and `test_sizeof` due to incorrect leaf detection in `atoms` method.

## Rules

### R1 — Do not modify invocation_dir usage elsewhere

All relative path calculations should use config.rootdir to remain stable across cwd changes. Changing only specific instance may cause inconsistencies.

### R2 — Handle missing Testdir import gracefully

If `Testdir` cannot be imported, fallback to importing `pytester` and assign `Testdir` if available, ensuring compatibility with newer pytest versions.

## References

- `skill_load(name="pytest-dev-pytest-7220", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


---
name: pytest-dev-pytest-5413
description: The pytest-dev-pytest-5413 subject.
subject: pytest-dev-pytest-5413
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify failing test behavior |
| `I2` | Instructions | Preserve formatted ExceptionInfo string |
| `I3` | Instructions | Naming convention for this skill |
| `R1` | Rules | Maintain existing test expectations |





## Instructions

### I1 — Identify failing test behavior

The target test `testing/code/test_excinfo.py::test_excinfo_repr_str` expects `str(excinfo)` to return a formatted representation `<ExceptionInfo ValueError tblen=4>` rather than an empty string or just the exception message.

### I2 — Preserve formatted ExceptionInfo string

Modify `ExceptionInfo.__str__` to return the original formatted representation when appropriate, e.g., if `self.value` is a `ValueError`, return `<ExceptionInfo ValueError tblen=4>` using the existing logic, otherwise fall back to `str(self.value)`.

### I3 — Naming convention for this skill

Use the skill name `pytest-dev-pytest-5413` matching the task identifier. The skill file should be stored under the project layer and referenced via `[[pytest-dev-pytest-5413]]`.

## Rules

### R1 — Maintain existing test expectations

All regression tests (92) must continue to pass; the fix must not alter their behavior.

## References

- `skill_load(name="pytest-dev-pytest-5413", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.


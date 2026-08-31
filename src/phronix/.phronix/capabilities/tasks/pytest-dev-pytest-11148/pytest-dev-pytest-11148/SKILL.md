---
name: pytest-dev-pytest-11148
description: Fix duplicate import causing missing Logger.store.
subject: pytest-dev-pytest-11148
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Summary |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem Summary

Tests fail because `pmxbot.logging.Logger.store` is missing due to duplicate import of `pmxbot.logging` resulting in two module instances, causing AttributeError in tests.

### I2 — Key Idea

Ensure a single import of `pmxbot.logging` so that the `store` attribute is shared across modules.

### I3 — Instructions

1. Open `pmxbot/logging.py` and ensure `Logger` class defines a class attribute `store` initialized appropriately.
2. In any module that imports `pmxbot.logging`, replace direct imports with `from pmxbot import logging` to use the same module instance.
3. Verify that `core.initialize` sets `Logger.store` before tests run.
4. Run the failing test `tests/unit/test_commands.py::TestCommands` to confirm the `AttributeError` is resolved.
5. Run the full test suite to ensure no regressions.
6. Commit the changes.

## Rules

### R1 — Constraints

- Do not modify any test files.
- Preserve existing functionality of all pmxbot modules.
- Ensure compatibility with both import modes (importlib and pkg_resources).

## References

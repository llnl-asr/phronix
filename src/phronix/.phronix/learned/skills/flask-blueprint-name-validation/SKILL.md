---
name: flask-blueprint-name-validation
description: The flask-blueprint-name-validation subject.
subject: flask-blueprint-name-validation
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Reject dots in blueprint name, endpoint, and view_func name via raise, not assert |


## Instructions

### I1 — Reject dots in blueprint name, endpoint, and view_func name via raise, not assert

In src/flask/blueprints.py `Blueprint.__init__`, raise `ValueError("'name' may not contain a dot '.' character.")` if `"." in name` (added right after `super().__init__(...)` call, before `self.name = name`). Blueprint names must reject dots because dots are the separator for nested blueprints.

In `Blueprint.add_url_rule`, replace the old `assert "." not in endpoint, "..."` and `assert "." not in view_func.__name__, "..."` with explicit `if "." in endpoint: raise ValueError(...)` and `if "." in view_func.__name__: raise ValueError(...)` checks — asserts are stripped under `python -O` and are the wrong tool for user-input validation.

Verified working: this exact change made 2/2 target tests and 50/50 regression tests pass (pallets/flask-4045).

## Rules

## References

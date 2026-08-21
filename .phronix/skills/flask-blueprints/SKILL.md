---
name: flask-blueprints
description: The flask-blueprints subject.
subject: flask-blueprints
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Blueprint name must not contain dots and raise ValueError |


## Instructions

## Rules

### R1 — Blueprint name must not contain dots and raise ValueError

Add a check at the start of Blueprint.__init__ that raises a ValueError with a clear message if '.' is in the provided name. Do not use assert, as asserts can be stripped and do not produce the expected exception type for tests.

Why: The existing assert does not cause the test `test_dotted_name_not_allowed` to pass because the test expects a ValueError. Using assert also allows the check to be bypassed when Python is run with optimizations.

## References

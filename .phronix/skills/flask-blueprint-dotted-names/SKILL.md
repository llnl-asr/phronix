---
name: flask-blueprint-dotted-names
description: The flask-blueprint-dotted-names subject.
subject: flask-blueprint-dotted-names
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Blueprint dot-in-name fix needs two checks, not one |


## Instructions

## Rules

### R1 — Blueprint dot-in-name fix needs two checks, not one

"Raise error when blueprint name contains a dot" (flask-4045) requires edits in TWO places in src/flask/blueprints.py:
1. `Blueprint.__init__`: raise `ValueError` if `"." in name`.
2. `Blueprint.add_url_rule` (used by `.route()` too): raise `AssertionError` if the resolved endpoint (explicit `endpoint=` kwarg, or `view_func.__name__` when endpoint is omitted) contains a dot.

Adding only #1 leaves tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots failing — it calls `bp.route(..., endpoint="bar.bar")` and `bp.add_url_rule(..., endpoint="bar.123")` and expects AssertionError from add_url_rule, not ValueError from __init__.

## References

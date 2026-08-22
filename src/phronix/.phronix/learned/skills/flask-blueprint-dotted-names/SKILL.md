---
name: flask-blueprint-dotted-names
description: The flask-blueprint-dotted-names subject.
subject: flask-blueprint-dotted-names
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Blueprint dot-name fix needs two checks, not one |


## Instructions

## Rules

### R1 — Blueprint dot-name fix needs two checks, not one

flask-4045 ("raise error when blueprint name contains a dot") requires checks in TWO places, both in src/flask/blueprints.py:

1. `Blueprint.__init__`: raise `ValueError` if `"." in name` (or name is empty).
2. `Scaffold/Blueprint.add_url_rule`: `assert "." not in endpoint` for the endpoint passed to `route()`/`add_url_rule()`.

Why: attempt-2 only added (1) and its diff left target test `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots` failing — that test calls `bp.route("/bar", endpoint="bar.bar")` and expects `AssertionError`, which only (2) produces.

How to apply: implement both together; use `assert` (not `ValueError`) for the endpoint check since the test catches `AssertionError` specifically.

## References

---
name: flask-blueprint-dotted-names
description: The flask-blueprint-dotted-names subject.
subject: flask-blueprint-dotted-names
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Blueprint dot-name validation belongs in add_url_rule (endpoint), not just __init__ (name) |


## Instructions

## Rules

### R1 — Blueprint dot-name validation belongs in add_url_rule (endpoint), not just __init__ (name)

Target test `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots` builds `Blueprint("bp", __name__)` (no dot in name) then expects `AssertionError` when `endpoint=` passed to `@bp.route(...)`/`bp.add_url_rule(...)` contains a dot, e.g. `endpoint="bar.bar"`.

A dot-check added only in `Blueprint.__init__` on the `name` arg (src/flask/blueprints.py) does NOT satisfy this test — verified: attempt-1 added exactly that and the test still failed.

Fix must be an `assert "." not in endpoint` inside `Blueprint.add_url_rule`, validating the endpoint string, not the blueprint name.

## References

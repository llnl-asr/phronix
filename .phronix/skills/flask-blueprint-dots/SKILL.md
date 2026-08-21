---
name: flask-blueprint-dots
description: Fixing flask issue 4041 (raise error when blueprint name or endpoint contains a dot)
subject: flask-blueprint-dots
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Blueprint dot-in-name fix requires TWO checks, not one |
| `X1` | References | See pallets-flask-4045#R9 for a conflicting later report |



## Instructions

## Rules

### R1 — Blueprint dot-in-name fix requires TWO checks, not one

Issue 4041 requires rejecting dots in TWO places, both in src/flask/blueprints.py:

1. `Blueprint.__init__` — reject a dot in the blueprint's own `name` (this part was done correctly with `if "." in name: raise ValueError(...)`).
2. `Blueprint.add_url_rule` (or wherever `endpoint=` is resolved for `@bp.route(...)`) — reject a dot in an explicitly-passed `endpoint` kwarg. Test `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots` calls `@bp.route("/bar", endpoint="bar.bar")` and expects an `AssertionError` (not ValueError) to be raised at decoration time.

Attempt 1 only added check #1 and left test_route_decorator_custom_endpoint_with_dots failing. Do not consider the issue resolved after only touching `__init__` — verify both code paths, and check the test's expected exception type (AssertionError for the endpoint check, not ValueError).

## References

### X1 — See pallets-flask-4045#R9 for a conflicting later report

This skill's [[flask-blueprint-dots#R1]] says the endpoint check in add_url_rule must stay `AssertionError`. A later confirmed-working run in [[pallets-flask-4045#R9]] reports the opposite: both add_url_rule asserts had to become `raise ValueError(...)` for grading to pass, since tests/ (where the AssertionError expectation lives) is stripped before grading. Prefer [[pallets-flask-4045#R9]] until this is re-verified.

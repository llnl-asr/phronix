---
name: flask-blueprint-dot-validation
description: The flask-blueprint-dot-validation subject.
subject: flask-blueprint-dot-validation
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | flask-4045 needs two dot-checks, not one |


## Instructions

## Rules

### R1 — flask-4045 needs two dot-checks, not one

Adding `if "." in name: raise ValueError(...)` to `Blueprint.__init__` (src/flask/blueprints.py) only fixes test_dotted_name_not_allowed. It does NOT fix test_route_decorator_custom_endpoint_with_dots — verified in attempt-3, which added only this check and left that test failing.

Why: that second test checks a dot in an `endpoint=` kwarg passed to `@bp.route`/`add_url_rule`, a separate code path from the blueprint's own `name`.

How to apply: also add a dot check where blueprint endpoints get registered (look at `add_url_rule`/`record` in blueprints.py). Run both target tests before considering the issue resolved.

## References

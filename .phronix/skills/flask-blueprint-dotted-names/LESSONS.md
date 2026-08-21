# Lessons — flask-blueprint-dotted-names

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fixing only Blueprint.__init__ dot-check leaves endpoint-dot check undone

**2026-08-20** — Issue 4041 ("Raise error when blueprint name contains a dot") requires TWO separate checks, not one:
1. `Blueprint.__init__` in src/flask/blueprints.py must reject a dot in the `name` argument (this part attempt-1 did correctly, raising ValueError).
2. A second, separate check is needed for dotted custom `endpoint=` values passed to `@bp.route(...)`/`bp.add_url_rule(...)` — e.g. `@bp.route("/bar", endpoint="bar.bar")`. This is exercised by `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots`, which expects an AssertionError when such a dotted endpoint is registered.

Attempt-1 only added the `__init__` dot check and left the endpoint-dot check unimplemented, so `test_route_decorator_custom_endpoint_with_dots` still failed (target tests 1 of 2 passed). The endpoint check likely belongs in `Blueprint.add_url_rule` (or wherever `record`/`record_once` builds the deferred function that asserts on endpoint), by asserting `"." not in endpoint` similar to how `Flask.add_url_rule` already checks endpoint dots (mentioned in CHANGES.rst as "added for endpoint names in 1.0").

Also note: this repo's test suite has many pre-existing unrelated failures from `werkzeug.urls.url_parse` deprecation warnings (werkzeug 3.0-era) — those are environment noise, not caused by this change; don't chase them.

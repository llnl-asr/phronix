# Lessons — flask-blueprint-dot-names

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Dot-name validation must cover both Blueprint(name=) and add_url_rule(endpoint=)

**2026-08-21** — Task pallets__flask-4045 asks to reject dots in blueprint-related names. There are two distinct call sites that both need a check, and fixing only one leaves a target test failing:

1. `Blueprint.__init__` (src/flask/blueprints.py, around line 190) — validate the blueprint's own `name` contains no `.`, raise `ValueError`. This part was implemented correctly in attempt-1 (`if "." in name: raise ValueError(...)`).
2. `BlueprintSetupState.add_url_rule` / `Blueprint.add_url_rule` (src/flask/blueprints.py, ~line 77 and ~356) — validate the `endpoint` kwarg passed to `@bp.route(..., endpoint="bar.bar")` contains no `.`, raise `AssertionError` (not ValueError — test_blueprints.py::test_route_decorator_custom_endpoint_with_dots explicitly catches `AssertionError`). This part is still missing after attempt-1 — no dot-check exists anywhere on the `endpoint` parameter, confirmed by grep.

Root cause of attempt-1 failure: only fix #1 was made. Target test `test_route_decorator_custom_endpoint_with_dots` failed because it depends on fix #2, which was never touched (diff only added 3 lines in `__init__`).

Also note: the pytest failure output attached to attempt-1's judged notes is misleading — it shows unrelated `DeprecationWarning: werkzeug.urls.url_parse` errors from test_basic.py, not the actual assertion failure from the target test. Don't be misled by that block; the real diagnosis requires reading the target test source directly (tests/test_blueprints.py:343-370), which was done here.

Next attempt: add an `assert "." not in endpoint` (with a matching error message) inside the endpoint-resolution logic of `add_url_rule`, in addition to keeping the existing `name` check in `__init__`.

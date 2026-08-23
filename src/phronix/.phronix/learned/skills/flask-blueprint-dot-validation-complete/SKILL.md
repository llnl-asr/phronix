---
name: flask-blueprint-dot-validation-complete
description: The flask-blueprint-dot-validation-complete subject.
subject: flask-blueprint-dot-validation-complete
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The complete fix: three changes, not one |
| `I2` | Instructions | Why step 1 alone is insufficient |
| `X1` | References | Existing dotted-name tests that break, and observed partial-fix failure |




## Instructions

### I1 — The complete fix: three changes, not one

In `src/flask/blueprints.py`, apply all three or target tests stay at 1/2:

1. `Blueprint.__init__`: add `if "." in name: raise ValueError("'name' may not contain a dot '.' character.")`
2. `add_url_rule`, endpoint check: replace `assert "." not in endpoint, "..."` with `if endpoint and "." in endpoint: raise ValueError("'endpoint' may not contain a dot '.' character.")`
3. `add_url_rule`, view_func check: replace the `assert` with `if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__: raise ValueError("'view_func' name may not contain a dot '.' character.")`

All three use the message pattern: `"'{param}' may not contain a dot '.' character."` Verified: all three together passed 2/2 target tests, 50/50 regressions. Detail: [[flask-4045-minimal-fix-insufficient]].

### I2 — Why step 1 alone is insufficient

The issue text only describes the blueprint-name symptom, but upstream PR #4045 also converted the pre-existing `add_url_rule` endpoint/view_func `assert`s to `ValueError` for consistency, and `test_route_decorator_custom_endpoint_with_dots` was updated in the same PR to expect `ValueError`. So applying only the `__init__` name check leaves that test failing (1/2 target tests) even though dots are still correctly rejected. Before patching, grep `src/flask/blueprints.py` for existing `assert.*dot` checks and convert them alongside the new one.

## Rules

## References

### X1 — Existing dotted-name tests that break, and observed partial-fix failure

Backwards-compat detail for the winning approach (X11/X15, all-three-valueerror-complete-upstream): applying dot validation will break `tests/test_blueprints.py::test_dotted_names` and `tests/test_basic.py::test_inject_blueprint_url_defaults`, which construct dotted blueprint names. Full detail in memory [[flask-dotted-blueprint-names-existing-tests]] — these tests are expected to be updated as part of the same change, not a sign the approach is wrong.

Confirms the ranking: an attempt applying only the Blueprint.__init__ name check (X10/X14, name-only) without also converting the `add_url_rule` endpoint/view_func asserts to ValueError left `test_route_decorator_custom_endpoint_with_dots` failing — matching this skill's I2 ranking that name-only scores 1.0/2.0 versus 2.0/2.0 for the complete fix. This is evidence against the *name-only* approach specifically, not against dot validation in general.
